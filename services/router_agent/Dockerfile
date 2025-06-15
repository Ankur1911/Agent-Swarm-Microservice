
FROM python:3.9-slim as shared-base
WORKDIR /app
COPY ../../shared/ ./shared/

# Service-specific Dockerfile
FROM shared-base
COPY services/router_agent/requirements.txt .
RUN pip install -r requirements.txt
COPY services/router_agent/ ./services/router_agent/
ENV PYTHONPATH=/app
CMD ["python", "/app/services/router_agent/main.py"]
