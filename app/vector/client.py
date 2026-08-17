"""
Qdrant vector database client.

Provides async access to Qdrant for storing and searching
document embeddings. Used for RAG (Retrieval-Augmented Generation)
and semantic memory.

Gracefully degrades when Qdrant is not available (dev mode).
"""

from typing import Optional
from uuid import UUID

from app.core.config import settings
from app.core.logging import logger


class VectorClient:
    """
    Async-compatible Qdrant client wrapper.

    Manages collections and provides search/upsert operations
    for document embeddings. Gracefully handles missing Qdrant.
    """

    def __init__(self) -> None:
        self._client = None
        self._collection_name = settings.QDRANT_COLLECTION
        self._vector_size = 1536
        self._available = False

    def _init_client(self) -> None:
        """Lazy-init the Qdrant client."""
        if self._client is not None:
            return
        if not settings.QDRANT_HOST:
            logger.info("Qdrant not configured — skipping vector operations")
            return
        try:
            from qdrant_client import QdrantClient
            from qdrant_client.http import models
            from qdrant_client.http.models import Distance, VectorParams

            self._client = QdrantClient(
                host=settings.QDRANT_HOST,
                port=settings.QDRANT_PORT,
                timeout=5.0,
            )
            # Test connection
            self._client.get_collections()
            self._available = True
            self._ensure_collection()
            logger.info("Qdrant connected: %s:%s", settings.QDRANT_HOST, settings.QDRANT_PORT)
        except Exception as e:
            logger.warning("Qdrant not available: %s — RAG disabled", e)
            self._available = False

    def _ensure_collection(self) -> None:
        """Create the collection if it doesn't exist."""
        if not self._available:
            return
        from qdrant_client.http.models import Distance, VectorParams
        collections = self._client.get_collections().collections
        exists = any(c.name == self._collection_name for c in collections)
        if not exists:
            self._client.create_collection(
                collection_name=self._collection_name,
                vectors_config=VectorParams(
                    size=self._vector_size,
                    distance=Distance.COSINE,
                ),
            )
            logger.info("Created Qdrant collection: %s", self._collection_name)

    async def upsert_document(
        self,
        doc_id: str,
        vector: list[float],
        payload: dict,
    ) -> None:
        """Insert or update a document embedding."""
        self._init_client()
        if not self._available:
            logger.warning("Qdrant not available — skipping upsert")
            return
        from qdrant_client.http import models
        self._client.upsert(
            collection_name=self._collection_name,
            points=[models.PointStruct(
                id=doc_id,
                vector=vector,
                payload=payload,
            )],
        )

    async def search_similar(
        self,
        vector: list[float],
        limit: int = 5,
        score_threshold: float = 0.7,
    ) -> list[dict]:
        """Search for similar documents by vector."""
        self._init_client()
        if not self._available:
            return []
        results = self._client.search(
            collection_name=self._collection_name,
            query_vector=vector,
            limit=limit,
            score_threshold=score_threshold,
        )
        return [
            {"id": hit.id, "score": hit.score, "payload": hit.payload}
            for hit in results
        ]

    async def delete_document(self, doc_id: str) -> None:
        """Delete a document by ID."""
        self._init_client()
        if not self._available:
            return
        from qdrant_client.http import models
        self._client.delete(
            collection_name=self._collection_name,
            points_selector=models.PointIdsList(points=[doc_id]),
        )

    async def close(self) -> None:
        """Close the Qdrant client."""
        if self._client:
            self._client.close()


# Singleton instance
vector_client = VectorClient()