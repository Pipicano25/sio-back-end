FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1

WORKDIR /app

# El contexto de construcción es la raíz del monorepo (depende de libs/sio-auth).
COPY libs/sio-auth /app/libs/sio-auth
COPY services/business-reporting-service /app/services/business-reporting-service

WORKDIR /app/services/business-reporting-service

# Sin base de datos ni migraciones (spec 023).
RUN python -m pip install --upgrade pip \
    && python -m pip install . \
    && useradd --create-home --uid 10001 appuser

USER appuser

EXPOSE 8000

HEALTHCHECK --interval=60s --timeout=5s --start-period=30s --start-interval=2s --retries=5 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health/live')"

CMD ["python", "-m", "uvicorn", "business_reporting_service.main:app", "--host", "0.0.0.0", "--port", "8000"]
