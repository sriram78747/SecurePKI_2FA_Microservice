############################
# Stage 1: Builder
############################
FROM python:3.11-slim AS builder
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends build-essential && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --upgrade pip && pip install --prefix=/install -r requirements.txt

############################
# Stage 2: Runtime
############################
FROM python:3.11-slim AS runtime
ENV TZ=UTC PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app

# system deps
RUN apt-get update && apt-get install -y --no-install-recommends cron tzdata && rm -rf /var/lib/apt/lists/*

# timezone
RUN ln -snf /usr/share/zoneinfo/UTC /etc/localtime && echo "UTC" > /etc/timezone

# copy installed python packages
COPY --from=builder /install /usr/local

# copy app code
COPY . /app

# create mount points
RUN mkdir -p /data /cron && chmod 755 /data /cron

# copy cron file (do not run crontab at build-time)
COPY cron/2fa-cron /etc/cron.d/2fa-cron
RUN chmod 0644 /etc/cron.d/2fa-cron && touch /var/log/cron.log

# copy start script and mark executable
COPY start.sh /app/start.sh
RUN chmod +x /app/start.sh

VOLUME ["/data", "/cron"]
EXPOSE 8080

# start cron and the API via start script
CMD ["sh", "-c", "/app/start.sh"]
COPY scripts /app/scripts
