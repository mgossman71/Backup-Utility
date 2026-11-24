# Optional deployment example — direct host deployment is the recommended path.
# See docker-compose.example.yml for required bind mounts.
FROM python:3.12-slim

# rsync is required by the backup engine; ca-certificates for optional proxies.
RUN apt-get update \
    && apt-get install -y --no-install-recommends rsync ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /srv/backup-ui

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY templates ./templates
COPY static ./static

# Application state and logs live on named volumes declared in the compose file.
ENV BACKUP_UI_HOST=0.0.0.0 \
    BACKUP_UI_PORT=8000 \
    BACKUP_UI_STATE_DIR=/var/lib/backup-ui \
    BACKUP_UI_LOG_DIR=/var/log/backup-ui

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
