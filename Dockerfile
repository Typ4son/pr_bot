FROM python:3.9-slim

# Install Chrome and dependencies in a single layer
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget \
    gnupg \
    unzip \
    chromium \
    chromium-driver \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Set working directory
WORKDIR /app

# Copy only requirements first
COPY requirements.txt .

# Install Python packages
RUN pip install --no-cache-dir -r requirements.txt

# Copy only necessary files
COPY pr.py .
COPY telegram_bot.py .
COPY .env .

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV DISPLAY=:99

CMD ["python", "telegram_bot.py"]