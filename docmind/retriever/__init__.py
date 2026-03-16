"""
Retrieval module for FAISS index management and similarity search.
"""

from .index import FAISSIndex
from .search import Retriever

__all__ = [
    "FAISSIndex",
    "Retriever",
]