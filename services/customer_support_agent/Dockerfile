
FROM python:3.9-slim as shared-base
WORKDIR /app
COPY ../../shared/ ./shared/

# Service-specific Dockerfile
FROM shared-base
COPY services/customer_support_agent/requirements.txt .
RUN pip install -r requirements.txt
COPY services/customer_support_agent/ ./services/customer_support_agent/
ENV PYTHONPATH=/app
CMD ["python", "/app/services/customer_support_agent/main.py"]
