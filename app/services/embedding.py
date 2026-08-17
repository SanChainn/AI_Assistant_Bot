"""
Embedding service.

Generates vector embeddings for text using OpenRouter's embedding API.
Used by the RAG pipeline to convert documents and queries into vectors.
"""

import httpx

from app.core.config import settings
from app.core.logging import logger


class EmbeddingService:
    """
    Service for generating text embeddings.

    Uses OpenRouter's embedding endpoint to convert text
    into vector representations for semantic search.
    """

    EMBEDDING_URL = "https://openrouter.ai/api/v1/embeddings"
    DEFAULT_MODEL = "text-embedding-ada-002"

    def __init__(self) -> None:
        self._api_key = settings.OPENROUTER_API_KEY

    async def embed_text(self, text: str, model: str = DEFAULT_MODEL) -> list[float]:
        """
        Generate an embedding vector for a text string.

        Args:
            text: The text to embed.
            model: The embedding model to use.

        Returns:
            A list of floats representing the embedding vector.
        """
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.EMBEDDING_URL,
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": model,
                    "input": text,
                },
                timeout=30.0,
            )
            response.raise_for_status()
            result = response.json()
            return result["data"][0]["embedding"]

    async def embed_chunks(self, chunks: list[str]) -> list[list[float]]:
        """
        Generate embeddings for multiple text chunks.

        Args:
            chunks: List of text strings to embed.

        Returns:
            List of embedding vectors.
        """
        embeddings = []
        for chunk in chunks:
            vector = await self.embed_text(chunk)
            embeddings.append(vector)
        return embeddings


# Singleton instance
embedding_service = EmbeddingService()