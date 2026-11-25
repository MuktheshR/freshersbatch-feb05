# syntax=docker/dockerfile:1

# ---------- Stage 1: builder - resolve dependencies into an isolated venv ----------
FROM python:3.12-slim AS builder
ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

# ---------- Stage 2: test - adds lint/test tooling; used by CI only ----------
FROM builder AS test
ENV PYTHONDONTWRITEBYTECODE=1
COPY requirements-dev.txt .
RUN pip install -r requirements-dev.txt
COPY . .
CMD ["sh", "-c", "flake8 app tests && python -m pytest -v -p no:cacheprovider"]

# ---------- Stage 3: runtime - minimal, non-root production image ----------
FROM python:3.12-slim AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH"
RUN groupadd --system app && useradd --system --gid app --no-create-home app
WORKDIR /app
COPY --from=builder /opt/venv /opt/venv
COPY --chown=app:app app ./app
USER app
EXPOSE 5000
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD ["python", "-c", "import urllib.request,sys; urllib.request.urlopen('http://127.0.0.1:5000/api/health', timeout=4); sys.exit(0)"]
CMD ["python", "-m", "app.server"]
