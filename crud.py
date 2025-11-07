import json
import hashlib
from typing import Optional, Tuple
from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from fastapi import HTTPException
from models import Doc, AuditIngest
from schemas import DocIngest

def _canonical_payload_hash(payload: dict) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()

def create_doc(db: Session, data: DocIngest, raw_payload: dict) -> Tuple[str, Doc]:
    hash_val = data.hash_sha256 or _canonical_payload_hash(raw_payload)

    doc = Doc(
        contrato_nro=data.contrato_nro,
        tipo=data.tipo,
        productor_cuit=data.productor_cuit,
        hash_sha256=hash_val,
        meta=data.metadata,              # <- antes: metadata=data.metadata
        referencias=data.referencias,
        content_text=data.content_text,
    )
    db.add(doc)
    try:
        db.commit()
        db.refresh(doc)
        audit = AuditIngest(
            doc_id=doc.id,
            status="OK",
            hash_sha256=hash_val,
            detail="Documento insertado",
            raw_payload=raw_payload,
        )
        db.add(audit)
        db.commit()
        return ("OK", doc)
    except IntegrityError:
        db.rollback()
        existing = db.scalar(select(Doc).where(Doc.hash_sha256 == hash_val))
        audit = AuditIngest(
            doc_id=existing.id if existing else None,
            status="DUP",
            hash_sha256=hash_val,
            detail="Documento duplicado (hash)",
            raw_payload=raw_payload,
        )
        db.add(audit)
        db.commit()
        raise HTTPException(status_code=409, detail="Documento duplicado (hash)")

def list_docs(
    db: Session,
    contrato_nro: Optional[str],
    tipo: Optional[str],
    productor_cuit: Optional[str],
    limit: int,
    offset: int,
):
    q = select(Doc)
    if contrato_nro:
        q = q.where(Doc.contrato_nro == contrato_nro)
    if tipo:
        q = q.where(Doc.tipo == tipo)
    if productor_cuit:
        q = q.where(Doc.productor_cuit == productor_cuit)

    count_q = select(func.count()).select_from(q.subquery())
    total = db.scalar(count_q)

    q = q.order_by(Doc.created_at.desc()).limit(limit).offset(offset)
    items = list(db.scalars(q))
    return total, items

def last_audit(db: Session, limit: Optional[int] = None):
    q = select(AuditIngest).order_by(AuditIngest.created_at.desc())
    if limit and limit > 0:
        q = q.limit(limit)
    return list(db.scalars(q))

def docs_count(db: Session) -> int:
    return db.scalar(select(func.count()).select_from(Doc))