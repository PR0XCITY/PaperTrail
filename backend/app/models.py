"""
Pydantic request/response models for the PaperTrail API.
"""
from pydantic import BaseModel
from typing import Optional


class QueryRequest(BaseModel):
    """Body for POST /query."""
    question: str
    document_id: Optional[str] = None   # None = search all documents
    session_id: str                      # client-generated UUID per conversation
    search_all: bool = False             # explicit override to search all docs
