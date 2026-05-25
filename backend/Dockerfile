# backend/Dockerfile
FROM python:3.11-slim
WORKDIR /app
# Install dependensi sistem untuk psycopg2 (PostgreSQL)
RUN apt-get update && apt-get install -y libpq-dev gcc
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8000