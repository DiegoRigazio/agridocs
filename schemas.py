from typing import Optional, Any, Dict, List
from uuid import UUID as UUID_T
from pydantic import BaseModel, Field, ConfigDict

class DocIngest(BaseModel):
    contrato_nro: str
    tipo: str
    productor_cuit: Optional[str] = None
    hash_sha256: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None   # <- el cliente sigue enviando "metadata"
    referencias: Optional[Dict[str, Any]] = None
    content_text: Optional[str] = None

class DocOut(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)
    id: UUID_T
    contrato_nro: str
    tipo: str
    productor_cuit: Optional[str]
    hash_sha256: Optional[str]
    # Mapear atributo ORM "meta" a clave JSON "metadata"
    metadata: Optional[dict] = Field(default=None, alias="meta", serialization_alias="metadata")
    referencias: Optional[dict]
    content_text: Optional[str]
    created_at: Any

class RecordsResponse(BaseModel):
    items: List[DocOut]
    limit: int
    offset: int
    count: int

class AuditOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    doc_id: Optional[UUID_T]
    status: str
    hash_sha256: Optional[str]
    detail: Optional[str]
    raw_payload: Optional[dict]
    created_at: Any

class HealthSimple(BaseModel):
    status: str = "ok"

class HealthFull(BaseModel):
    status: str = "ok"
    docs_count: int
    last_audit: List[AuditOut]