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

ENV PORT=5000
EXPOSE ${PORT}

CMD gunicorn app:app --bind 0.0.0.0:${PORT} --workers 4 --threads 2 --timeout 120 --access-logfile - --error-logfile -
