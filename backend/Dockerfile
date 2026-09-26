FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

COPY --from=ghcr.io/astral-sh/uv:0.8 /uv /usr/local/bin/uv

WORKDIR /srv

COPY pyproject.toml uv.lock README.md ./
RUN uv sync --frozen --no-dev --no-install-project

COPY app ./app
COPY config ./config
# PYTHONDONTWRITEBYTECODE means the app's own .pyc would be recompiled on every cold start.
RUN python -m compileall -q app

RUN adduser --system --no-create-home --group elderguard \
    && chown -R elderguard:elderguard /srv
USER elderguard

ENV PORT=8080 \
    PATH="/srv/.venv/bin:$PATH"
EXPOSE 8080

# --proxy-headers so Twilio signature validation sees the public scheme/host behind Cloud Run.
CMD ["sh", "-c", "uvicorn app.main:create_app --factory --host 0.0.0.0 --port ${PORT} --proxy-headers --forwarded-allow-ips='*'"]
