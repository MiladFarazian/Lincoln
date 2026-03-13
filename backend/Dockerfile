FROM python:3.11-slim

# Install system deps for psycopg2
RUN apt-get update && apt-get install -y \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ ./app/

# Create models directory for ML artifacts
RUN mkdir -p models

EXPOSE 8000

CMD ["python", "-c", "import os; port = os.environ.get('PORT', '8000'); os.execvp('uvicorn', ['uvicorn', 'app.main:app', '--host', '0.0.0.0', '--port', port])"]
