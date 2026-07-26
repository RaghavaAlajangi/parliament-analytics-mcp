# --- build stage ---
FROM python:3.11-slim AS builder

WORKDIR /app

RUN pip install --no-cache-dir uv

COPY pyproject.toml uv.lock ./
COPY mcp_server/ ./mcp_server/

# Install the package and all runtime deps into the system Python
RUN uv pip install --system --no-cache .

# --- runtime stage ---
FROM python:3.11-slim AS runtime

WORKDIR /app

COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin
COPY mcp_server/ ./mcp_server/
COPY pyproject.toml ./

# DIP response cache — override to mount a host volume for persistence
ENV DIP_CACHE_DIR=/app/.dip_cache

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

CMD ["parliament-mcp-http"]
