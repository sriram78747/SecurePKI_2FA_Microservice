#!/bin/sh
# start.sh — install cron job at container start, then run cron + uvicorn

set -e

# Ensure required dirs exist
mkdir -p /data /cron
touch /var/log/cron.log

# Ensure cron file exists and set permissions
if [ -f /etc/cron.d/2fa-cron ]; then
  chmod 0644 /etc/cron.d/2fa-cron
  # Install the cron file (crontab requires a regular file)
  crontab /etc/cron.d/2fa-cron || true
fi

# Start cron in background
cron

# Start FastAPI (replace with your command if different)
exec uvicorn main:app --host 0.0.0.0 --port 8080
