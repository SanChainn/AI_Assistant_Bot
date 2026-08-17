"""
Document schemas for RAG API request/response validation.
"""

from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class DocumentIndexRequest(BaseModel):
    """Schema for indexing a document."""
    content: str = Field(..., min_length=1, max_length=100000)
    user_id: Optional[UUID] = None
    source: Optional[str] = None


class DocumentIndexResponse(BaseModel):
    """Schema for document indexing response."""
    doc_id: str
    content_length: int


class DocumentSearchRequest(BaseModel):
    """Schema for searching documents."""
    query: str = Field(..., min_length=1, max_length=4096)
    user_id: Optional[UUID] = None
    limit: int = Field(3, ge=1, le=20)


class DocumentSearchResult(BaseModel):
    """Schema for a single search result."""
    id: str
    score: float
    content: str
    source: Optional[str] = None


class DocumentSearchResponse(BaseModel):
    """Schema for document search response."""
    results: list[DocumentSearchResult]