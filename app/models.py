"""Pydantic models for request and response schemas."""

from typing import List, Optional

from pydantic import BaseModel


class ChatRequest(BaseModel):
    """Request model for the chat endpoint."""

    question: str


class Citation(BaseModel):
    """Model for a citation in the chat response."""

    title: str
    link: str
    ticker: Optional[str] = None


class FactCheckResult(BaseModel):
    verdict: str  # "PASS" | "WARN" | "FAIL"
    unsupported_claims: List[str] = []
    confidence: float = 0.0
    notes: Optional[str] = None


class ChatResponse(BaseModel):
    """Response model for the chat endpoint."""

    answer: str
    citations: List[Citation]
    fact_check: Optional[FactCheckResult] = None


class Healthz(BaseModel):
    """Health check response model."""

    ok: bool
    docs: int
