FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    libpq-dev \
    gcc \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libgdk-pixbuf2.0-0 \
    libglib2.0-0 \
    libffi-dev \
    shared-mime-info \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

COPY . .

# Make entrypoint script executable
RUN chmod +x entrypoint.sh

ENV PORT=5000
# Set Flask environment to development by default for local development
# Override with FLASK_ENV=production in production deployments
ENV FLASK_ENV=development
# Set default ALLOWED_ORIGINS for local development/testing
# Override this in production with actual domain(s)
ENV ALLOWED_ORIGINS=http://localhost:5000,http://127.0.0.1:5000,https://localhost:5000,https://127.0.0.1:5000
EXPOSE ${PORT}

# Use entrypoint script to run migrations before starting server
ENTRYPOINT ["./entrypoint.sh"]
