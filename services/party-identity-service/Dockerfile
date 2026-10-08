FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY libs/sio-auth /app/libs/sio-auth
COPY libs/sio-audit /app/libs/sio-audit
COPY services/party-identity-service /app/services/party-identity-service

WORKDIR /app/services/party-identity-service

RUN python -m pip install --upgrade pip \
    && python -m pip install .

EXPOSE 8000

CMD ["python", "-m", "uvicorn", "party_identity_service.main:app", "--host", "0.0.0.0", "--port", "8000"]
