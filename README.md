# AgriDocs Cloud API (FastAPI + Postgres Neon + Render Free)

API mínima para ingesta de documentos con dedupe por hash y auditoría. **No usa Azure** y no afecta tu proyecto AI Inbox Zero.

## Endpoints

- `GET /health` → `{"status":"ok"}`
- `GET /health/full` → `{"status":"ok","docs_count":X,"last_audit":[...5]}`
- `POST /ingest` → inserta doc, dedupe por `hash_sha256` (índice único parcial)
- `GET /records` → filtros por `contrato_nro`, `tipo`, `productor_cuit`, paginación `limit`/`offset`
- `GET /records/export.csv` → exporta CSV con `;`
- `GET /audit/ingest` → últimos N (param `limit`), timestamps ISO8601

## Compatibilidad de `/ingest` (Formato Plano + ERP)

`/ingest` acepta **dos variantes**:

- **Plano (original)**:
  ```json
  {
    "contrato_nro": "CON-2025-0345",
    "tipo": "LIQUIDACION",
    "productor_cuit": "20-12345678-9",
    "hash_sha256": "…",
    "metadata": { "origen": {...}, "datos": {...} },
    "referencias": { "ctg": "..." },
    "content_text": "..."
  }

**Seguridad opcional**: Header `X-API-Key`.  
- Si la env `API_KEY` está **vacía** → **no se exige**.
- Si `API_KEY` tiene valor → se exige header `X-API-Key: <valor>` (401 si falta/incorrecta).

CORS abierto.

---

## Setup local rápido

Requisitos:
- Python 3.12
- Una DB Postgres (recomendado usar directamente Neon también en local)

```bash
git clone <tu-repo>
cd <tu-repo>

python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

pip install -r requirements.txt

# Copiar .env.sample -> .env y completar DATABASE_URL de Neon con sslmode=require
cp .env.sample .env
# Edita .env y pega: DATABASE_URL=postgresql+psycopg2://USER:PASS@HOST/DB?sslmode=require

uvicorn main:app --host 0.0.0.0 --port 8000