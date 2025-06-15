
FROM python:3.9-slim as shared-base
WORKDIR /app
COPY ../../shared/ ./shared/

# Service-specific Dockerfile
FROM shared-base
COPY services/personality_layer/requirements.txt .
RUN pip install -r requirements.txt
COPY services/personality_layer/ ./services/personality_layer/
ENV PYTHONPATH=/app
CMD ["python", "/app/services/personality_layer/main.py"]
