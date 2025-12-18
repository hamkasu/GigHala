FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

COPY . .

# Make entrypoint script executable
RUN chmod +x entrypoint.sh

ENV PORT=5000
EXPOSE ${PORT}

# Use entrypoint script to run migrations before starting server
ENTRYPOINT ["./entrypoint.sh"]
