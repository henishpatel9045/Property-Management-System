# Use a Debian-based Python image (Playwright does not support Alpine)
FROM python:3.11-slim

# Set timezone for Adelaide
ENV TZ=Australia/Adelaide
RUN echo "--- Build Started ---"
WORKDIR /app

# Install system dependencies for Playwright AND Cron/Timezone
RUN apt-get update && apt-get install -y \
    cron \
    tzdata \
    libgbm-dev \
    libnss3 \
    libasound2 \
    libxshmfence1 \
    libglu1-mesa \
    && rm -rf /var/lib/apt/lists/*

# Configure Timezone
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# Copy the requirements file into the container
COPY requirements.txt .

# Install Python packages
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright browsers and their system dependencies
RUN playwright install chromium
RUN playwright install-deps chromium

# Copy the application code
COPY . .

# Setup Crontab
COPY crontab /etc/cron.d/whatsapp-cron
RUN chmod 0644 /etc/cron.d/whatsapp-cron && \
    crontab /etc/cron.d/whatsapp-cron && \
    touch /var/log/cron.log

# Setup Entrypoint
RUN chmod +x entrypoint.sh
ENTRYPOINT ["/app/entrypoint.sh"]
