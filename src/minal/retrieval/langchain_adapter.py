"""Optional LangChain wrapper (TECH_STACK 3.5). Import this module only where
langchain_core is installed; nothing else in the package depends on it."""
from __future__ import annotations

from typing import Any

from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever
from pydantic import ConfigDict, Field

from .models import RetrievalRequest
from .retriever import Retriever


class MinalLangChainRetriever(BaseRetriever):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    retriever: Retriever
    top_k: int = 5
    filters: dict[str, Any] = Field(default_factory=dict)

    def _get_relevant_documents(self, query: str, *, run_manager: Any = None) -> list[Document]:
        result = self.retriever.retrieve(
            RetrievalRequest(question=query, top_k=self.top_k, filters=self.filters)
        )
        return [
            Document(
                page_content=p.text,
                metadata={
                    "ref": p.ref, "kind": p.kind.value, "key": p.key,
                    "version": p.version, "score": p.score, "match": p.match,
                },
            )
            for p in result.passages
        ]
