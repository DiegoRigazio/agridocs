# AgriDocs Cloud API - Dockerfile (Render Free)
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Crear usuario no-root
RUN useradd -m appuser

WORKDIR /app

# Dependencias del sistema (mínimas)
# (psycopg2-binary no requiere build deps)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
  && rm -rf /var/lib/apt/lists/*

# Instalar Python deps
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código
COPY . .

# Usar usuario no-root
USER appuser

# Render asigna $PORT; uvicorn debe bindear 0.0.0.0:$PORT
CMD ["bash", "-lc", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]