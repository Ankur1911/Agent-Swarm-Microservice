
FROM python:3.9-slim as shared-base
WORKDIR /app
COPY ../../shared/ ./shared/

# Service-specific Dockerfile
FROM shared-base
COPY services/knowledge_agent/requirements.txt .
RUN pip install -r requirements.txt
COPY services/knowledge_agent/ ./services/knowledge_agent/
ENV PYTHONPATH=/app
CMD ["python", "/app/services/knowledge_agent/main.py"]
