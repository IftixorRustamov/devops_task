import http.client
import json
from pathlib import Path
import tempfile
import threading
import unittest

from crystal.api.server import create_server


class ApiTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.folder = tempfile.TemporaryDirectory()
        cls.server = create_server("127.0.0.1", 0, str(Path(cls.folder.name) / "api.sqlite3"))
        cls.port = cls.server.server_address[1]
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.folder.cleanup()

    def request(self, method, path, body=None, raw=None):
        connection = http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)
        self.addCleanup(connection.close)
        data = raw if raw is not None else (json.dumps(body).encode() if body is not None else None)
        headers = {"Content-Type": "application/json"} if data is not None else {}
        connection.request(method, path, body=data, headers=headers)
        response = connection.getresponse()
        payload = json.loads(response.read().decode("utf-8"))
        self.assertTrue(response.getheader("Content-Type").startswith("application/json"))
        return response.status, payload

    def create(self):
        status, payload = self.request("POST", "/api/v1/orders", {"address": "Demo manzil"})
        self.assertEqual(status, 201)
        return payload["code"]

    def test_health(self):
        status, payload = self.request("GET", "/health")
        self.assertEqual((status, payload["status"]), (200, "ok"))

    def test_full_lifecycle_over_http(self):
        code = self.create()
        self.assertEqual(self.request("POST", f"/api/v1/orders/{code}/receive")[0], 200)
        status, _ = self.request("POST", f"/api/v1/orders/{code}/assign", {"courier": "Demo kuryer"})
        self.assertEqual(status, 200)
        self.assertEqual(self.request("POST", f"/api/v1/orders/{code}/dispatch")[0], 200)
        self.assertEqual(self.request("POST", f"/api/v1/orders/{code}/deliver")[0], 200)
        status, tracking = self.request("GET", f"/api/v1/orders/{code.lower()}")
        self.assertEqual(status, 200)
        self.assertEqual(
            [event["status"] for event in tracking["history"]],
            ["Yangi", "Omborda", "Yo‘lda", "Yetkazildi"],
        )
        self.assertNotIn("Demo manzil", json.dumps(tracking, ensure_ascii=False))
        self.assertNotIn("Demo kuryer", json.dumps(tracking, ensure_ascii=False))

    def test_wrong_state_is_conflict(self):
        code = self.create()
        status, payload = self.request("POST", f"/api/v1/orders/{code}/deliver")
        self.assertEqual(status, 409)
        self.assertIn("error", payload)

    def test_validation_errors(self):
        self.assertEqual(self.request("POST", "/api/v1/orders", {"address": " "})[0], 400)
        self.assertEqual(
            self.request("POST", "/api/v1/orders", {"address": "X", "warehouse_id": 999})[0], 400
        )
        self.assertEqual(self.request("POST", "/api/v1/orders", raw=b"{not json")[0], 400)
        self.assertEqual(self.request("POST", "/api/v1/orders", raw=b"[1, 2]")[0], 400)

    def test_not_found_and_method_not_allowed(self):
        self.assertEqual(self.request("GET", "/api/v1/orders/CRY-UNKNOWN")[0], 404)
        self.assertEqual(self.request("GET", "/nowhere")[0], 404)
        self.assertEqual(self.request("DELETE", "/api/v1/orders")[0], 405)

    def test_warehouses(self):
        status, payload = self.request("GET", "/api/v1/warehouses")
        self.assertEqual(status, 200)
        self.assertEqual(payload["items"][0]["name"], "Markaziy ombor")

    def test_parallel_creates(self):
        codes, errors = [], []

        def worker():
            try:
                connection = http.client.HTTPConnection("127.0.0.1", self.port, timeout=10)
                connection.request("POST", "/api/v1/orders", body=b'{"address":"P"}',
                                   headers={"Content-Type": "application/json"})
                response = connection.getresponse()
                codes.append((response.status, json.loads(response.read())["code"]))
                connection.close()
            except Exception as error:  # pragma: no cover
                errors.append(error)

        threads = [threading.Thread(target=worker) for _ in range(20)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        self.assertEqual(errors, [])
        self.assertEqual({status for status, _ in codes}, {201})
        self.assertEqual(len({code for _, code in codes}), 20)


if __name__ == "__main__":
    unittest.main()
