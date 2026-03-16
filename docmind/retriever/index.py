"""
FAISS index management for vector similarity search.
"""

from pathlib import Path
from typing import Optional

import faiss
import numpy as np


class FAISSIndex:
    """
    FAISS index wrapper for vector storage and retrieval.
    """

    def __init__(self, dimension: int, index_type: str = "flat"):
        """
        Initialize FAISS index.

        Args:
            dimension: Dimension of the vectors.
            index_type: Type of FAISS index ("flat", "ivf", "hnsw").
        """
        self.dimension = dimension
        self.index_type = index_type
        self.index: Optional[faiss.Index] = None
        self._create_index()

    def _create_index(self) -> None:
        """Create the FAISS index based on type."""
        if self.index_type == "flat":
            self.index = faiss.IndexFlatIP(self.dimension)
        elif self.index_type == "ivf":
            # IVF index with 100 clusters
            quantizer = faiss.IndexFlatIP(self.dimension)
            self.index = faiss.IndexIVFFlat(quantizer, self.dimension, 100)
        elif self.index_type == "hnsw":
            self.index = faiss.IndexHNSWFlat(self.dimension, 32)
        else:
            self.index = faiss.IndexFlatIP(self.dimension)

    def add(self, vectors: np.ndarray) -> None:
        """
        Add vectors to the index.

        Args:
            vectors: Numpy array of shape (num_vectors, dimension).
        """
        if self.index is None:
            raise ValueError("Index not initialized")

        # Ensure vectors are float32
        vectors = vectors.astype(np.float32)

        # Train index if needed (for IVF)
        if self.index_type == "ivf" and not self.index.is_trained:
            self.index.train(vectors)

        self.index.add(vectors)

    def search(
        self, query_vectors: np.ndarray, top_k: int = 10
    ) -> tuple[np.ndarray, np.ndarray]:
        """
        Search for similar vectors.

        Args:
            query_vectors: Query vectors of shape (num_queries, dimension).
            top_k: Number of results to return.

        Returns:
            Tuple of (distances, indices) arrays.
        """
        if self.index is None:
            raise ValueError("Index not initialized")

        query_vectors = query_vectors.astype(np.float32)
        distances, indices = self.index.search(query_vectors, top_k)
        return distances, indices

    def save(self, path: Path) -> None:
        """
        Save the index to disk.

        Args:
            path: Path to save the index file.
        """
        if self.index is None:
            raise ValueError("Index not initialized")

        path.parent.mkdir(parents=True, exist_ok=True)
        faiss.write_index(self.index, str(path))

    def load(self, path: Path) -> None:
        """
        Load the index from disk.

        Args:
            path: Path to the index file.
        """
        if not path.exists():
            raise FileNotFoundError(f"Index file not found: {path}")

        self.index = faiss.read_index(str(path))
        self.dimension = self.index.d

    def __len__(self) -> int:
        """Return the number of vectors in the index."""
        return self.index.ntotal if self.index else 0

    def is_trained(self) -> bool:
        """Check if the index is trained."""
        return self.index.is_trained if self.index else False