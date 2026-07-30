from app.vector_db import ensure_qdrant_collection, qdrant_client

ensure_qdrant_collection()

collections = qdrant_client.get_collections()
print(collections)