FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY libs/sio-auth /app/libs/sio-auth
COPY services/product-catalog-service /app/services/product-catalog-service

WORKDIR /app/services/product-catalog-service

RUN python -m pip install --upgrade pip \
    && python -m pip install .

EXPOSE 8000

CMD ["python", "-m", "uvicorn", "product_catalog_service.main:app", "--host", "0.0.0.0", "--port", "8000"]
