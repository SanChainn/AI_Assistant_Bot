"""
RAG (Retrieval-Augmented Generation) service.

Enriches LLM responses with relevant context from stored documents.
Pipeline:
1. User sends a message
2. Message is embedded into a vector
3. Similar documents are retrieved from Qdrant
4. Retrieved context is injected into the LLM prompt
5. LLM generates a response with the context
"""

import hashlib
import uuid
from typing import Optional

from app.core.logging import logger
from app.services.embedding import embedding_service
from app.vector.client import vector_client


class RAGService:
    """
    Service for Retrieval-Augmented Generation.

    Manages document ingestion, semantic search, and context
    injection for LLM conversations.
    """

    async def index_document(
        self,
        content: str,
        metadata: Optional[dict] = None,
        doc_id: Optional[str] = None,
    ) -> str:
        """
        Index a document for semantic search.

        Args:
            content: The document text content.
            metadata: Optional metadata (user_id, source, etc.).
            doc_id: Optional document ID (auto-generated if not provided).

        Returns:
            The document ID.
        """
        if doc_id is None:
            doc_id = str(uuid.uuid4())

        # Generate embedding
        vector = await embedding_service.embed_text(content)
        logger.debug("Generated embedding for doc %s (dim=%d)", doc_id, len(vector))

        # Store in Qdrant
        payload = {
            "content": content,
            "doc_id": doc_id,
            **(metadata or {}),
        }
        await vector_client.upsert_document(
            doc_id=doc_id,
            vector=vector,
            payload=payload,
        )
        logger.info("Indexed document %s (%d chars)", doc_id, len(content))
        return doc_id

    async def search_context(
        self,
        query: str,
        user_id: Optional[str] = None,
        limit: int = 3,
    ) -> list[dict]:
        """
        Search for relevant document context for a query.

        Args:
            query: The search query (user message).
            user_id: Optional user ID to filter by.
            limit: Maximum number of results.

        Returns:
            List of relevant document chunks with scores.
        """
        # Embed the query
        query_vector = await embedding_service.embed_text(query)

        # Search Qdrant
        results = await vector_client.search_similar(
            vector=query_vector,
            limit=limit,
            score_threshold=0.6,
        )

        # Filter by user_id if provided
        if user_id:
            results = [r for r in results if r.get("payload", {}).get("user_id") == user_id]

        return results

    def format_context(self, results: list[dict]) -> str:
        """
        Format search results into a context string for the LLM prompt.

        Args:
            results: List of search results from Qdrant.

        Returns:
            A formatted context string to inject into the system prompt.
        """
        if not results:
            return ""

        context_parts = []
        for i, result in enumerate(results, 1):
            content = result.get("payload", {}).get("content", "")
            score = result.get("score", 0)
            context_parts.append(f"[Document {i}] (relevance: {score:.2f})\n{content}")

        return "\n\n".join(context_parts)

    async def delete_document(self, doc_id: str) -> None:
        """Delete a document from the vector store."""
        await vector_client.delete_document(doc_id)
        logger.info("Deleted document %s", doc_id)


# Singleton instance
rag_service = RAGService()