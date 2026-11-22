"""Xabar shinasi: production’da RabbitMQ (topic exchange), testlarda xotirada.

Topologiya:
    crystal.events      (topic, durable)  — barcha hodisalar, routing key = hodisa turi
    crystal.events.dlx  (direct, durable) — qayta ishlab bo‘lmagan xabarlar
    <servis>.events     navbat — servis tinglaydigan hodisalar
    <servis>.events.dlq navbat — ikki marta muvaffaqiyatsiz bo‘lgan xabarlar (qo‘lda tekshiriladi)
"""

import json
import logging
import threading
import time

log = logging.getLogger("crystal.bus")

EXCHANGE = "crystal.events"
DEAD_LETTER_EXCHANGE = "crystal.events.dlx"


def topic_matches(pattern, key):
    """AMQP topic qoidasi: `*` bitta so‘z, `#` nol yoki ko‘p so‘z."""

    def match(p, k):
        if not p:
            return not k
        if p[0] == "#":
            return any(match(p[1:], k[i:]) for i in range(len(k) + 1))
        if not k:
            return False
        return (p[0] == "*" or p[0] == k[0]) and match(p[1:], k[1:])

    return match(pattern.split("."), key.split("."))


class InMemoryBus:
    """Bitta jarayon ichidagi shina: lokal ishga tushirish va testlar uchun."""

    def __init__(self):
        self.subscriptions = []
        self.published = []

    def subscribe(self, queue, bindings, handler):
        self.subscriptions.append((queue, tuple(bindings), handler))

    def publish(self, event):
        self.published.append(event)
        for _queue, bindings, handler in self.subscriptions:
            if any(topic_matches(binding, event["type"]) for binding in bindings):
                handler(event)

    def start(self):
        pass

    def stop(self):
        pass

    def healthy(self):
        return True


class RabbitBus:
    def __init__(self, url, service):
        import pika  # faqat konteynerda o‘rnatilgan

        self.pika = pika
        self.parameters = pika.URLParameters(url)
        self.parameters.client_properties = {"connection_name": service}
        # Broker ishlamasa tez xato qaytsin (health va so‘rovlar osilib qolmasin).
        self.parameters.socket_timeout = 2
        self.parameters.connection_attempts = 1
        self.parameters.heartbeat = 30
        self.service = service
        self._lock = threading.Lock()
        self._connection = None
        self._channel = None
        self._consumers = []
        self._stop = threading.Event()

    # --- yuborish -------------------------------------------------------------
    def _declare_topology(self, channel):
        channel.exchange_declare(EXCHANGE, exchange_type="topic", durable=True)
        channel.exchange_declare(DEAD_LETTER_EXCHANGE, exchange_type="direct", durable=True)

    def _ensure_publisher(self):
        if self._connection is None or not self._connection.is_open:
            self._connection = self.pika.BlockingConnection(self.parameters)
            self._channel = self._connection.channel()
            self._channel.confirm_delivery()  # broker qabul qilganini tasdiqlaydi
            self._declare_topology(self._channel)
        return self._channel

    def _reset_publisher(self):
        try:
            if self._connection is not None and self._connection.is_open:
                self._connection.close()
        except Exception:
            pass
        self._connection = self._channel = None

    def publish(self, event):
        body = json.dumps(event, ensure_ascii=False).encode("utf-8")
        properties = self.pika.BasicProperties(
            content_type="application/json",
            delivery_mode=2,  # persistent: broker qayta ishga tushsa ham saqlanadi
            message_id=event["id"],
            type=event["type"],
            app_id=self.service,
        )
        with self._lock:
            for attempt in (1, 2):
                try:
                    channel = self._ensure_publisher()
                    channel.basic_publish(EXCHANGE, event["type"], body, properties, mandatory=False)
                    return
                except Exception:
                    # Bo‘sh turgan ulanishni broker yopgan bo‘lishi mumkin — bir marta qayta ulanamiz.
                    self._reset_publisher()
                    if attempt == 2:
                        raise

    def healthy(self):
        with self._lock:
            try:
                self._ensure_publisher()
                self._connection.process_data_events(time_limit=0)
            except Exception as error:
                log.warning("RabbitMQ bilan aloqa yo‘q: %s", error)
                self._reset_publisher()
                return False
        return all(thread.is_alive() for thread in self._consumers)

    # --- tinglash -------------------------------------------------------------
    def subscribe(self, queue, bindings, handler):
        thread = threading.Thread(
            target=self._consume_forever,
            args=(queue, tuple(bindings), handler),
            name=f"consumer-{queue}",
            daemon=True,
        )
        self._consumers.append(thread)

    def _consume_forever(self, queue, bindings, handler):
        delay = 1
        while not self._stop.is_set():
            try:
                self._consume(queue, bindings, handler)
                delay = 1
            except Exception as error:
                if self._stop.is_set():
                    break
                log.warning("Consumer %s uzildi, %d s dan keyin qayta ulanadi: %s", queue, delay, error)
                self._stop.wait(delay)
                delay = min(delay * 2, 15)

    def _consume(self, queue, bindings, handler):
        connection = self.pika.BlockingConnection(self.parameters)
        try:
            channel = connection.channel()
            self._declare_topology(channel)
            dead_letter_queue = queue + ".dlq"
            channel.queue_declare(dead_letter_queue, durable=True)
            channel.queue_bind(dead_letter_queue, DEAD_LETTER_EXCHANGE, routing_key=queue)
            channel.queue_declare(
                queue,
                durable=True,
                arguments={
                    "x-dead-letter-exchange": DEAD_LETTER_EXCHANGE,
                    "x-dead-letter-routing-key": queue,
                },
            )
            for binding in bindings:
                channel.queue_bind(queue, EXCHANGE, routing_key=binding)
            channel.basic_qos(prefetch_count=20)
            log.info("Consumer %s tayyor (%s)", queue, ", ".join(bindings))
            for method, _properties, body in channel.consume(queue, inactivity_timeout=1):
                if self._stop.is_set():
                    break
                if method is None:
                    continue
                try:
                    handler(json.loads(body))
                    channel.basic_ack(method.delivery_tag)
                except Exception:
                    if method.redelivered:
                        log.exception("Hodisa ikkinchi marta ham xato berdi, DLQ’ga: %s", queue)
                        channel.basic_nack(method.delivery_tag, requeue=False)
                    else:
                        log.exception("Hodisani qayta ishlashda xato, navbatga qaytariladi: %s", queue)
                        time.sleep(0.5)
                        channel.basic_nack(method.delivery_tag, requeue=True)
            channel.cancel()
        finally:
            if connection.is_open:
                connection.close()

    # --- hayot sikli ----------------------------------------------------------
    def start(self):
        for thread in self._consumers:
            thread.start()

    def stop(self):
        self._stop.set()
        for thread in self._consumers:
            thread.join(timeout=5)
        with self._lock:
            self._reset_publisher()


def create_bus(url, service):
    if url:
        return RabbitBus(url, service)
    log.warning("CRYSTAL_BROKER_URL berilmagan — xotiradagi shina ishlatiladi (faqat lokal).")
    return InMemoryBus()
