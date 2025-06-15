
FROM python:3.9-slim as shared-base
WORKDIR /app
COPY ../../shared/ ./shared/

# Service-specific Dockerfile
FROM shared-base
COPY services/general_agent/requirements.txt .
RUN pip install -r requirements.txt
COPY services/general_agent/ ./services/general_agent/
ENV PYTHONPATH=/app
CMD ["python", "/app/services/general_agent/main.py"]
