import os
import csv
import io
from typing import Optional, Dict, Any
from fastapi import FastAPI, Depends, Header, Query, Body, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from dotenv import load_dotenv

from db import Base, engine, get_db
from schemas import DocIngest, RecordsResponse, AuditOut, HealthSimple, HealthFull
from crud import create_doc, list_docs, last_audit, docs_count

load_dotenv()

API_KEY_ENV = os.getenv("API_KEY", "").strip()

def api_key_dependency(x_api_key: Optional[str] = Header(default=None, alias="X-API-Key")):
    """
    Seguridad opcional:
    - Si API_KEY está vacío -> NO se exige header.
    - Si API_KEY tiene valor -> exigir X-API-Key idéntico, si no => 401.
    """
    if not API_KEY_ENV:
        return
    if not x_api_key or x_api_key != API_KEY_ENV:
        raise HTTPException(status_code=401, detail="Unauthorized: invalid or missing X-API-Key")

app = FastAPI(title="AgriDocs Cloud API", version="1.0.1")

# CORS abierto para consumo desde Power Apps u orígenes web
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=False,
)

# Crear/validar tablas al iniciar
@app.on_event("startup")
def on_startup():
    if engine is None:
        raise RuntimeError("DATABASE_URL no configurada. Configure Neon/Local antes de iniciar la app.")
    Base.metadata.create_all(bind=engine)
    print("[startup] Tablas verificadas/creadas.")

# --- Health ---
@app.get("/health", response_model=HealthSimple, summary="Health simple", tags=["health"])
def health():
    return {"status": "ok"}

@app.get("/health/full", response_model=HealthFull, summary="Health extendido", tags=["health"])
def health_full(db: Session = Depends(get_db)):
    count = docs_count(db)
    audits = last_audit(db, limit=5)
    return {"status": "ok", "docs_count": count, "last_audit": audits}

# --- Normalizador de payload ---
def _normalize_ingest_payload(p: Dict[str, Any]) -> Dict[str, Any]:
    """
    Acepta dos variantes de entrada:
    A) 'Plana' (original de la API):
       {
         contrato_nro, tipo, productor_cuit?, hash_sha256?,
         metadata?, referencias?, content_text?
       }

    B) 'ERP-like' (tu JSON):
       {
         tipo,
         origen{ hash_sha256? ... },
         referencias{ contrato_nro, productor_cuit? ... },
         datos?, content_text?
       }

    Devuelve un dict listo para DocIngest(**...).
    """
    if not isinstance(p, dict):
        raise HTTPException(status_code=422, detail="Payload inválido (no es objeto JSON)")

    contrato = p.get("contrato_nro") or (p.get("referencias") or {}).get("contrato_nro")
    tipo = p.get("tipo")
    if not contrato or not tipo:
        raise HTTPException(status_code=422, detail="Faltan campos requeridos: contrato_nro y/o tipo")

    productor_cuit = p.get("productor_cuit") or (p.get("referencias") or {}).get("productor_cuit")
    hash_val = p.get("hash_sha256") or (p.get("origen") or {}).get("hash_sha256")
    referencias = p.get("referencias")

    # Si ya viene metadata, usarla; si no, construir con origen+datos si existen
    metadata = p.get("metadata")
    if metadata is None:
        comp = {}
        if p.get("origen") is not None:
            comp["origen"] = p.get("origen")
        if p.get("datos") is not None:
            comp["datos"] = p.get("datos")
        metadata = comp if comp else None

    return {
        "contrato_nro": contrato,
        "tipo": tipo,
        "productor_cuit": productor_cuit,
        "hash_sha256": hash_val,
        "metadata": metadata,
        "referencias": referencias,
        "content_text": p.get("content_text"),
    }

# --- Ingest ---
@app.post("/ingest", summary="Ingesta de documentos (admite formato plano o ERP)", tags=["ingest"])
def ingest(payload: Dict[str, Any] = Body(...),
          db: Session = Depends(get_db),
          auth=Depends(api_key_dependency)):
    # Compat layer: normalizamos a la estructura DocIngest
    norm = _normalize_ingest_payload(payload)
    data = DocIngest(**norm)

    print(f"[ingest] contrato_nro={data.contrato_nro} tipo={data.tipo}")
    status, doc = create_doc(db, data, raw_payload=payload)
    return {"ok": True, "doc_id": str(doc.id), "status": status}

# --- Records ---
@app.get("/records", response_model=RecordsResponse, summary="Consulta de documentos", tags=["records"])
def records(
    contrato_nro: Optional[str] = Query(default=None),
    tipo: Optional[str] = Query(default=None),
    productor_cuit: Optional[str] = Query(default=None),
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    auth=Depends(api_key_dependency),
):
    total, items = list_docs(db, contrato_nro, tipo, productor_cuit, limit, offset)
    return {"items": items, "limit": limit, "offset": offset, "count": total}

# --- Export CSV ---
@app.get("/records/export.csv", summary="Export CSV (delimitador ';')", tags=["records"])
def records_export_csv(
    contrato_nro: Optional[str] = Query(default=None),
    tipo: Optional[str] = Query(default=None),
    productor_cuit: Optional[str] = Query(default=None),
    limit: int = Query(default=5000, ge=1, le=100000),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    auth=Depends(api_key_dependency),
):
    _, items = list_docs(db, contrato_nro, tipo, productor_cuit, limit, offset)

    output = io.StringIO()
    writer = csv.writer(output, delimiter=';')
    writer.writerow(["id", "contrato_nro", "tipo", "productor_cuit", "hash_sha256", "created_at"])
    for d in items:
        writer.writerow([
            str(d.id),
            d.contrato_nro,
            d.tipo,
            d.productor_cuit or "",
            d.hash_sha256 or "",
            d.created_at.isoformat() if d.created_at else ""
        ])

    output.seek(0)
    headers = {"Content-Disposition": "attachment; filename=records_export.csv"}
    return StreamingResponse(iter([output.read()]), media_type="text/csv", headers=headers)

# --- Auditoría ---
@app.get("/audit/ingest", summary="Auditoría de ingestas", tags=["audit"], response_model=list[AuditOut])
def audit_ingest(limit: Optional[int] = Query(default=100, ge=1),
                 db: Session = Depends(get_db),
                 auth=Depends(api_key_dependency)):
    return last_audit(db, limit=limit)