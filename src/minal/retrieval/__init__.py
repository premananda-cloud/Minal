"""Minal retrieval: read-only access to college data for the AI."""
from .models import Passage, RetrievalConfig, RetrievalRequest, RetrievalResult
from .retriever import Retriever

__all__ = ["Passage", "RetrievalConfig", "RetrievalRequest", "RetrievalResult", "Retriever"]
