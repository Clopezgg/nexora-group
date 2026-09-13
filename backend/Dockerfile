FROM python:3.12-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends libpq-dev gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./

RUN pip install --no-cache-dir -r requirements.txt

# NEXORA containers MUST NOT execute application/runtime code as root.
# Fixed UID/GID keeps ownership deterministic across environments.
RUN groupadd --gid 10001 nexora \
    && useradd \
        --uid 10001 \
        --gid 10001 \
        --home-dir /home/nexora \
        --create-home \
        --shell /usr/sbin/nologin \
        nexora

COPY --chown=10001:10001 . .

RUN chown 10001:10001 /app

USER 10001:10001

EXPOSE 8000

CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
