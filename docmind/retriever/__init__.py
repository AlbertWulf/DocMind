"""
Retrieval module for FAISS index management and similarity search.
"""

from .index import FAISSIndex
from .search import Retriever, SearchResult
from .cache import EmbeddingCache, CacheMetadata

__all__ = [
    "FAISSIndex",
    "Retriever",
    "SearchResult",
    "EmbeddingCache",
    "CacheMetadata",
]