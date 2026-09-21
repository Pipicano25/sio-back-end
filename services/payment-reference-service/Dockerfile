FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY libs/sio-auth /app/libs/sio-auth
COPY services/payment-reference-service /app/services/payment-reference-service

WORKDIR /app/services/payment-reference-service

RUN python -m pip install --upgrade pip \
    && python -m pip install .

EXPOSE 8000

CMD ["python", "-m", "uvicorn", "payment_reference_service.main:app_factory", "--factory", "--host", "0.0.0.0", "--port", "8000"]