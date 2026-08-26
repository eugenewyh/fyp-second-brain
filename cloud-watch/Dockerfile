FROM python:3.12-slim

WORKDIR /app

# Repo context: build from repository root:
#   docker build -f cloud-watch/Dockerfile .
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY src /app/src
COPY cloud-watch /app/cloud-watch

ENV PYTHONPATH=/app/src:/app/cloud-watch
ENV CLOUD_WATCH_DATA=/data

WORKDIR /app/cloud-watch
EXPOSE 8787

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8787"]
