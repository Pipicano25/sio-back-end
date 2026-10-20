# Despliegue unificado de SIO (modalidad adicional): los 12 microservicios (un proceso ASGI)
# y sus 11 workers (un proceso) en un solo contenedor. No reemplaza los Dockerfiles de cada servicio.
#
# Construir desde la raíz del repositorio (usa su .dockerignore):
#   docker build -f infrastructure/unified-deployment/Dockerfile -t sio-unified .

FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY libs/sio-auth /app/libs/sio-auth
COPY libs/sio-audit /app/libs/sio-audit
COPY services/geography-service /app/services/geography-service
COPY services/party-identity-service /app/services/party-identity-service
COPY services/product-catalog-service /app/services/product-catalog-service
COPY services/operational-context-service /app/services/operational-context-service
COPY services/payment-reference-service /app/services/payment-reference-service
COPY services/commercial-relationship-service /app/services/commercial-relationship-service
COPY services/purchase-service /app/services/purchase-service
COPY services/sales-service /app/services/sales-service
COPY services/inventory-service /app/services/inventory-service
COPY services/audit-service /app/services/audit-service
COPY services/product-inventory-query-service /app/services/product-inventory-query-service
COPY services/business-reporting-service /app/services/business-reporting-service
COPY infrastructure/unified-deployment/requirements.txt /app/infrastructure/unified-deployment/requirements.txt

RUN python -m pip install --upgrade pip \
    && for package in $(grep -vE '^\s*(#|$)' infrastructure/unified-deployment/requirements.txt); do \
         (cd "/app/$package" && python -m pip install .) || exit 1; \
       done \
    && python -m pip check

# Después de instalar: un cambio en estos archivos no repite la instalación.
COPY infrastructure/unified-deployment /app/infrastructure/unified-deployment
WORKDIR /app/infrastructure/unified-deployment

# Render inyecta PORT; en local vale 8000. Las 12 aplicaciones comparten un proceso y se
# llaman entre sí por 127.0.0.1:$PORT; los workers van en otro proceso (workers.py).
ENV PORT=8000
EXPOSE 8000

# supervisor.py es PID 1: arranca la API, luego los workers, los rearranca si caen y
# reparte el SIGTERM de Render. SIO_UNIFIED_WORKERS=none deja solo la API.
CMD ["python", "supervisor.py"]
