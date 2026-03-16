"""
Retriever for searching relevant code chunks using FAISS.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import numpy as np

from ..embedder.encoder import Encoder
from ..embedder.splitter import CodeChunk
from .index import FAISSIndex


@dataclass
class SearchResult:
    """Result of a search query."""

    chunk: CodeChunk
    score: float
    rank: int


class Retriever:
    """
    Retrieve relevant code chunks using vector similarity search.
    """

    def __init__(
        self,
        encoder: Encoder,
        top_k: int = 15,
    ):
        """
        Initialize the retriever.

        Args:
            encoder: Encoder instance for generating embeddings.
            top_k: Number of results to return per query.
        """
        self.encoder = encoder
        self.top_k = top_k
        self.index: Optional[FAISSIndex] = None
        self.chunks: list[CodeChunk] = []

    def build_index(self, chunks: list[CodeChunk]) -> None:
        """
        Build the FAISS index from a list of chunks.

        Args:
            chunks: List of CodeChunk objects to index.
        """
        if not chunks:
            return

        self.chunks = chunks

        # Encode all chunks
        vectors = self.encoder.encode_chunks(chunks)

        # Create and populate index
        self.index = FAISSIndex(dimension=vectors.shape[1], index_type="flat")
        self.index.add(vectors)

    def search(self, query: str) -> list[SearchResult]:
        """
        Search for relevant chunks given a query string.

        Args:
            query: Query string.

        Returns:
            List of SearchResult objects.
        """
        if self.index is None or not self.chunks:
            return []

        # Encode query
        query_vector = self.encoder.encode_single(query)
        query_vectors = query_vector.reshape(1, -1)

        # Search
        distances, indices = self.index.search(query_vectors, self.top_k)

        # Build results
        results = []
        for rank, (score, idx) in enumerate(zip(distances[0], indices[0])):
            if idx < len(self.chunks):
                results.append(SearchResult(
                    chunk=self.chunks[idx],
                    score=float(score),
                    rank=rank + 1,
                ))

        return results

    def search_batch(self, queries: list[str]) -> list[list[SearchResult]]:
        """
        Search for multiple queries at once.

        Args:
            queries: List of query strings.

        Returns:
            List of SearchResult lists, one per query.
        """
        if self.index is None or not self.chunks:
            return [[] for _ in queries]

        if not queries:
            return []

        # Encode all queries
        query_vectors = self.encoder.encode(queries)

        # Search
        distances, indices = self.index.search(query_vectors, self.top_k)

        # Build results for each query
        all_results = []
        for q_idx in range(len(queries)):
            results = []
            for rank, (score, idx) in enumerate(zip(distances[q_idx], indices[q_idx])):
                if idx < len(self.chunks):
                    results.append(SearchResult(
                        chunk=self.chunks[idx],
                        score=float(score),
                        rank=rank + 1,
                    ))
            all_results.append(results)

        return all_results

    def get_context_for_query(
        self,
        query: str,
        max_tokens: int = 4000,
        encoder_name: str = "cl100k_base",
    ) -> str:
        """
        Get concatenated context for a query, limited by token count.

        Args:
            query: Query string.
            max_tokens: Maximum total tokens for the context.
            encoder_name: Tiktoken encoder name for token counting.

        Returns:
            Concatenated context string.
        """
        import tiktoken

        results = self.search(query)
        tokenizer = tiktoken.get_encoding(encoder_name)

        context_parts = []
        total_tokens = 0

        for result in results:
            chunk_text = f"\n--- {result.chunk.source_file} ({result.chunk.chunk_type}: {result.chunk.metadata.get('name', 'unknown')}) ---\n{result.chunk.content}"
            chunk_tokens = len(tokenizer.encode(chunk_text))

            if total_tokens + chunk_tokens <= max_tokens:
                context_parts.append(chunk_text)
                total_tokens += chunk_tokens
            else:
                break

        return "\n".join(context_parts)

    def save_index(self, path: Path) -> None:
        """
        Save the index to disk.

        Args:
            path: Path to save the index.
        """
        if self.index is None:
            raise ValueError("Index not built")

        self.index.save(path)

    def load_index(self, path: Path, chunks: list[CodeChunk]) -> None:
        """
        Load the index from disk.

        Args:
            path: Path to the index file.
            chunks: List of CodeChunk objects (must match the saved index).
        """
        self.index = FAISSIndex(dimension=1)  # Dummy dimension
        self.index.load(path)
        self.chunks = chunks

    def has_index(self) -> bool:
        """Check if an index has been built."""
        return self.index is not None and len(self.index) > 0

    def get_chunk_count(self) -> int:
        """Get the number of chunks in the index."""
        return len(self.chunks)