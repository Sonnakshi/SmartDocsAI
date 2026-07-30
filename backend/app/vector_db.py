import os
import uuid

from dotenv import load_dotenv
from qdrant_client import QdrantClient
from qdrant_client.http.models import (
    Distance,
    PointStruct,
    VectorParams,
    Filter,
    FieldCondition,
    MatchValue,
)
from sentence_transformers import SentenceTransformer

load_dotenv()

QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")
QDRANT_COLLECTION_NAME = os.getenv("QDRANT_COLLECTION_NAME", "smartdocs_chunks")

EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"
EMBEDDING_DIMENSION = 384

qdrant_client = QdrantClient(
    url=QDRANT_URL,
    api_key=QDRANT_API_KEY if QDRANT_API_KEY else None,
)

embedding_model = SentenceTransformer(EMBEDDING_MODEL_NAME)


def ensure_qdrant_collection() -> None:
    collections = qdrant_client.get_collections().collections
    existing_names = [collection.name for collection in collections]

    if QDRANT_COLLECTION_NAME not in existing_names:
        qdrant_client.create_collection(
            collection_name=QDRANT_COLLECTION_NAME,
            vectors_config=VectorParams(
                size=EMBEDDING_DIMENSION,
                distance=Distance.COSINE,
            ),
        )


def generate_embeddings(texts: list[str]) -> list[list[float]]:
    return embedding_model.encode(texts).tolist()


def generate_query_embedding(query: str) -> list[float]:
    return embedding_model.encode(query.strip()).tolist()


def store_document_chunks(
    document_id: str,
    owner_id: str,
    filename: str,
    file_type: str,
    chunks: list[str],
) -> None:
    chunks = [chunk.strip() for chunk in chunks if chunk.strip()]
    if not chunks:
        return

    ensure_qdrant_collection()
    embeddings = generate_embeddings(chunks)

    points = []
    for index, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
        points.append(
            PointStruct(
                id=str(uuid.uuid4()),
                vector=embedding,
                payload={
                    "document_id": document_id,
                    "owner_id": owner_id,
                    "filename": filename,
                    "file_type": file_type,
                    "chunk_index": index,
                    "text": chunk,
                },
            )
        )

    qdrant_client.upsert(
        collection_name=QDRANT_COLLECTION_NAME,
        points=points,
    )


def search_document_chunks(
    query: str,
    owner_id: str,
    limit: int = 5,
) -> list[dict]:
    ensure_qdrant_collection()
    query_vector = generate_query_embedding(query)

    search_result = qdrant_client.query_points(
        collection_name=QDRANT_COLLECTION_NAME,
        query=query_vector,
        limit=limit,
        with_payload=True,
        query_filter=Filter(
            must=[
                FieldCondition(
                    key="owner_id",
                    match=MatchValue(value=owner_id),
                )
            ]
        ),
    )

    results = search_result.points if hasattr(search_result, "points") else search_result

    formatted_results = []
    for result in results:
        payload = result.payload or {}
        formatted_results.append(
            {
                "score": result.score,
                "document_id": payload.get("document_id", ""),
                "filename": payload.get("filename", ""),
                "file_type": payload.get("file_type", ""),
                "chunk_index": payload.get("chunk_index", 0),
                "text": payload.get("text", ""),
            }
        )

    return formatted_results


def delete_document_chunks(document_id: str, owner_id: str) -> None:
    ensure_qdrant_collection()

    qdrant_client.delete(
        collection_name=QDRANT_COLLECTION_NAME,
        points_selector=Filter(
            must=[
                FieldCondition(
                    key="document_id",
                    match=MatchValue(value=document_id),
                ),
                FieldCondition(
                    key="owner_id",
                    match=MatchValue(value=owner_id),
                ),
            ]
        ),
    )