FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1

WORKDIR /app

# El contexto de construcción es la raíz del monorepo (depende de libs/sio-auth).
COPY libs/sio-auth /app/libs/sio-auth
COPY services/operational-context-service /app/services/operational-context-service

WORKDIR /app/services/operational-context-service

RUN python -m pip install --upgrade pip \
    && python -m pip install . \
    && useradd --create-home --uid 10001 appuser

USER appuser

EXPOSE 8000

HEALTHCHECK --interval=10s --timeout=5s --start-period=15s --retries=10 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health/live')"

CMD ["python", "-m", "uvicorn", "operational_context_service.main:app", "--host", "0.0.0.0", "--port", "8000"]
