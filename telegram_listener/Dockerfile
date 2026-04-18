# Use a Debian-based Python image (Playwright does not support Alpine)
FROM python:3.11-slim

RUN echo "--- Build Started ---"
WORKDIR /app

# Install system dependencies for Playwright
RUN apt-get update && apt-get install -y \
    libgbm-dev \
    libnss3 \
    libasound2 \
    libxshmfence1 \
    libglu1-mesa \
    && rm -rf /var/lib/apt/lists/*

# Copy the requirements file into the container
COPY requirements.txt .

# Install Python packages
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright browsers and their system dependencies
RUN playwright install chromium
RUN playwright install-deps chromium

# Copy the application code
COPY . .

# Run main.py by default (or override with docker-compose)
CMD ["python", "main.py"]
