# Bitta Dockerfile — uchta servis obrazi. Qaysi servis ekanini SERVICE argumenti belgilaydi:
#   docker build --build-arg SERVICE=order --target runtime -t crystal-order .
ARG PYTHON_VERSION=3.13
# Debian bookworm qat’iy belgilangan: trixie’dagi OpenSSL 3.5 kattaroq TLS handshake yuboradi va
# GitHub Codespaces (docker-in-docker) tarmog‘ida pip PyPI’ga ulana olmaydi (read timeout).
ARG DEBIAN_RELEASE=bookworm

# ---------- 1-bosqich: bog‘liqliklar ----------
FROM python:${PYTHON_VERSION}-slim-${DEBIAN_RELEASE} AS deps
ENV PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1
COPY services/requirements.txt /tmp/requirements.txt
RUN pip install --retries 10 --timeout 60 --prefix=/install -r /tmp/requirements.txt

# ---------- 2-bosqich: testlar ----------
# `docker build --target test .` — testlar o‘tmasa build to‘xtaydi.
FROM python:${PYTHON_VERSION}-slim-${DEBIAN_RELEASE} AS test
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
COPY --from=deps /install /usr/local
WORKDIR /app
COPY services/ services/
COPY tests/ tests/
RUN python -m unittest discover -s tests -v

# ---------- 3-bosqich: ishchi obraz ----------
FROM python:${PYTHON_VERSION}-slim-${DEBIAN_RELEASE} AS runtime
ARG SERVICE
RUN test -n "$SERVICE" || (echo "SERVICE build argumenti kerak: order | courier | tracking" && false)

LABEL org.opencontainers.image.title="crystal-${SERVICE}-service" \
      org.opencontainers.image.description="Crystal Logistics ${SERVICE}-service" \
      org.opencontainers.image.source="https://github.com/IftixorRustamov/devops_task"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    CRYSTAL_SERVICE=${SERVICE} \
    CRYSTAL_HOST=0.0.0.0 \
    CRYSTAL_PORT=8000 \
    CRYSTAL_LOG_LEVEL=INFO

RUN groupadd --system --gid 10001 crystal \
 && useradd --system --uid 10001 --gid crystal --no-create-home --shell /usr/sbin/nologin crystal

COPY --from=deps /install /usr/local
WORKDIR /app
# Obrazga faqat umumiy kutubxona va SHU servis kodi kiradi.
COPY --chown=root:root services/common/crystal_common/ crystal_common/
COPY --chown=root:root services/${SERVICE}/${SERVICE}_service/ ${SERVICE}_service/

USER crystal:crystal
EXPOSE 8000

HEALTHCHECK --interval=10s --timeout=3s --start-period=20s --retries=3 \
  CMD ["python", "-c", "import sys,urllib.request; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=2).status == 200 else 1)"]

ENTRYPOINT ["python", "-m", "crystal_common.launch"]
