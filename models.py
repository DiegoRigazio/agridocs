import uuid
from sqlalchemy import Column, String, Text, DateTime, func, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from db import Base

class Doc(Base):
    __tablename__ = "docs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    contrato_nro = Column(String(64), index=True, nullable=False)
    tipo = Column(String(32), index=True, nullable=False)
    productor_cuit = Column(String(32), index=True, nullable=True)

    # Dedupe por hash (único cuando NO es NULL)
    hash_sha256 = Column(String(64), nullable=True, unique=False, index=True)

    # ⚠️ Importante: NO usar 'metadata' como nombre de atributo en modelos
    meta = Column(JSONB, nullable=True)            # <- antes: metadata
    referencias = Column(JSONB, nullable=True)
    content_text = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    audits = relationship("AuditIngest", back_populates="doc", lazy="selectin")

# Índice único parcial (único cuando hash_sha256 no es NULL)
Index(
    "uq_docs_hash_sha256_not_null",
    Doc.hash_sha256,
    unique=True,
    postgresql_where=Doc.hash_sha256.isnot(None)
)

class AuditIngest(Base):
    __tablename__ = "audit_ingest"

    id = Column(String(40), primary_key=True, default=lambda: f"a_{uuid.uuid4().hex[:32]}")
    doc_id = Column(UUID(as_uuid=True), ForeignKey("docs.id"), nullable=True)
    status = Column(String(8), nullable=False)  # "OK" o "DUP"
    hash_sha256 = Column(String(64), nullable=True)
    detail = Column(Text, nullable=True)
    raw_payload = Column(JSONB, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    doc = relationship("Doc", back_populates="audits")