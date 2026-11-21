ARG PYTHON_VERSION=3.13

# ---------- 1-bosqich: testlar ----------
# `docker build --target test .` testlarni obraz ichida ishlatadi.
# Testlar o‘tmasa build to‘xtaydi.
FROM python:${PYTHON_VERSION}-slim AS test
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY crystal/ crystal/
COPY app.py .
COPY tests/ tests/
RUN python -m unittest discover -s tests -v

# ---------- 2-bosqich: ishchi obraz ----------
FROM python:${PYTHON_VERSION}-slim AS runtime

LABEL org.opencontainers.image.title="crystal-logistics" \
      org.opencontainers.image.description="Crystal Logistics REST API" \
      org.opencontainers.image.source="https://github.com/IftixorRustamov/devops_task"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    CRYSTAL_HOST=0.0.0.0 \
    CRYSTAL_PORT=8000 \
    CRYSTAL_DB_PATH=/data/crystal.sqlite3 \
    CRYSTAL_LOG_LEVEL=INFO

# root bo‘lmagan foydalanuvchi va ma’lumotlar papkasi
RUN groupadd --system --gid 10001 crystal \
 && useradd --system --uid 10001 --gid crystal --no-create-home --shell /usr/sbin/nologin crystal \
 && mkdir -p /data && chown crystal:crystal /data

WORKDIR /app
COPY --chown=root:root crystal/ crystal/
COPY --chown=root:root app.py .

USER crystal:crystal
VOLUME ["/data"]
EXPOSE 8000

HEALTHCHECK --interval=15s --timeout=3s --start-period=5s --retries=3 \
  CMD ["python", "-c", "import os,sys,urllib.request; u='http://127.0.0.1:'+os.environ.get('CRYSTAL_PORT','8000')+'/health'; sys.exit(0 if urllib.request.urlopen(u, timeout=2).status == 200 else 1)"]

ENTRYPOINT ["python", "-m", "crystal"]
CMD ["serve"]
