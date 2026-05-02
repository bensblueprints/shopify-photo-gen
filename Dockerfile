FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for Pillow
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libjpeg-dev \
    zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

# Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app
COPY . .

# Create upload/generated dirs
RUN mkdir -p uploads generated

# Expose port
EXPOSE 5000

# Run with gunicorn
CMD ["gunicorn", "-w", "2", "-b", "0.0.0.0:5000", "-t", "300", "app:app"]
