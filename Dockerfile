############################
# Stage 1: Builder
############################
FROM python:3.11-slim AS builder

WORKDIR /app

# Install pip dependencies (cryptography needs build tools)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --upgrade pip
RUN pip install --prefix=/install -r requirements.txt


############################
# Stage 2: Runtime
############################
FROM python:3.11-slim AS runtime

# Set timezone to UTC
ENV TZ=UTC \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install cron + timezone tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    cron \
    tzdata \
    && rm -rf /var/lib/apt/lists/*

# Configure timezone
RUN ln -snf /usr/share/zoneinfo/UTC /etc/localtime && echo "UTC" > /etc/timezone

# Copy installed dependencies from builder
COPY --from=builder /install /usr/local

# Copy your application code
COPY . /app

# Create required volume folders
RUN mkdir -p /data /cron && chmod 755 /data /cron

# Copy cron job file (you will create this in next step)
COPY cron/2fa-cron /etc/cron.d/2fa-cron

# Set permissions & register cron job
RUN chmod 0644 /etc/cron.d/2fa-cron && crontab /etc/cron.d/2fa-cron

# Expose FastAPI port
EXPOSE 8080

# Start cron AND FastAPI
CMD /usr/sbin/cron && uvicorn main:app --host 0.0.0.0 --port 8080
