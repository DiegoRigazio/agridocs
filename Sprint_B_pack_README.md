# Sprint_B_pack

## Archivos
- AgriDocs_OpenAPI_0_1_0.json — OpenAPI 3.0 para importar como Custom Connector en Power Platform.
- postman_collection_AgriDocs_SprintB.json — Coleccion Postman.
- payload_sample_ingest.json — Ejemplo de body para POST /ingest.

## Importar conector en Power Platform
1. Power Automate → Data → Custom connectors → New custom connector → Import an OpenAPI file.
2. Elegí AgriDocs_OpenAPI_0_1_0.json.
3. Base URL: http://localhost:8002.
4. Guardar y probar postIngest y getRecords.

## Flujo minimo (manual)
- Trigger: Manual o When a file is created (SharePoint/OneDrive).
- Accion HTTP (si no usas el conector):
  - Method: POST
  - URI: http://localhost:8002/ingest
  - Headers: Content-Type: application/json
  - Body: contenido de payload_sample_ingest.json (ajusta campos).

## Notas
- Dedupe: se aplica por hash_sha256 (indice unico parcial).
  - 200: {"ok": true, "doc_id": N}
  - 409: {"detail": "Documento duplicado (hash)"}
- Auditoria: GET /audit/ingest muestra los ultimos 50 intentos.
