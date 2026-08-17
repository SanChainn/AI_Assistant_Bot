"""
Document API endpoints for RAG operations.

Provides endpoints for indexing and searching documents
via the vector database (Qdrant).
"""

from fastapi import APIRouter, Depends, HTTPException

from app.core.logging import logger
from app.schemas.document import (
    DocumentIndexRequest,
    DocumentIndexResponse,
    DocumentSearchRequest,
    DocumentSearchResponse,
    DocumentSearchResult,
)
from app.services.rag import rag_service

router = APIRouter(prefix="/documents", tags=["documents"])


@router.post("/index", response_model=DocumentIndexResponse)
async def index_document(request: DocumentIndexRequest) -> DocumentIndexResponse:
    """
    Index a document for semantic search.

    The document content is embedded and stored in Qdrant
    for later retrieval during conversations.
    """
    metadata = {}
    if request.user_id:
        metadata["user_id"] = str(request.user_id)
    if request.source:
        metadata["source"] = request.source

    doc_id = await rag_service.index_document(
        content=request.content,
        metadata=metadata,
    )

    logger.info("Document indexed: %s (%d chars)", doc_id, len(request.content))
    return DocumentIndexResponse(
        doc_id=doc_id,
        content_length=len(request.content),
    )


@router.post("/search", response_model=DocumentSearchResponse)
async def search_documents(request: DocumentSearchRequest) -> DocumentSearchResponse:
    """
    Search indexed documents by semantic similarity.

    Returns the most relevant document chunks for a given query.
    """
    user_id = str(request.user_id) if request.user_id else None
    results = await rag_service.search_context(
        query=request.query,
        user_id=user_id,
        limit=request.limit,
    )

    search_results = [
        DocumentSearchResult(
            id=r.get("id", ""),
            score=r.get("score", 0.0),
            content=r.get("payload", {}).get("content", ""),
            source=r.get("payload", {}).get("source"),
        )
        for r in results
    ]

    return DocumentSearchResponse(results=search_results)


@router.delete("/{doc_id}")
async def delete_document(doc_id: str) -> dict:
    """Delete an indexed document by its ID."""
    await rag_service.delete_document(doc_id)
    return {"ok": True, "doc_id": doc_id}