"""
Embedding cache management for avoiding redundant embedding computation.
"""

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from ..embedder.splitter import CodeChunk
from .index import FAISSIndex


@dataclass
class CacheMetadata:
    """Metadata for cache validation."""
    
    project_path: str
    file_hashes: dict[str, str] = field(default_factory=dict)
    embedder_model: str = ""
    embedder_provider: str = ""
    splitter_chunk_size: int = 500
    splitter_overlap: int = 100
    total_chunks: int = 0


class EmbeddingCache:
    """
    Manage embedding cache to avoid redundant computation.
    
    Cache files are stored in .docmind/cache/ directory:
    - index.faiss: FAISS index
    - chunks.json: Serialized code chunks
    - metadata.json: Cache metadata for validation
    """
    
    CACHE_DIR = ".docmind/cache"
    
    def __init__(self, project_path: Path):
        """
        Initialize cache manager.
        
        Args:
            project_path: Path to the project root.
        """
        self.project_path = project_path.resolve()
        self.cache_dir = self.project_path / self.CACHE_DIR
        self.index_path = self.cache_dir / "index.faiss"
        self.chunks_path = self.cache_dir / "chunks.json"
        self.metadata_path = self.cache_dir / "metadata.json"
    
    def exists(self) -> bool:
        """Check if cache exists."""
        return (
            self.index_path.exists() 
            and self.chunks_path.exists() 
            and self.metadata_path.exists()
        )
    
    def compute_file_hashes(self, files: list[Path]) -> dict[str, str]:
        """
        Compute hashes for a list of files.
        
        Args:
            files: List of file paths.
            
        Returns:
            Dictionary mapping relative file paths to their hashes.
        """
        hashes = {}
        for file_path in files:
            try:
                rel_path = str(file_path.relative_to(self.project_path))
                content = file_path.read_bytes()
                file_hash = hashlib.md5(content).hexdigest()
                hashes[rel_path] = file_hash
            except Exception:
                continue
        return hashes
    
    def is_valid(
        self,
        files: list[Path],
        embedder_model: str,
        embedder_provider: str,
        chunk_size: int,
        chunk_overlap: int,
    ) -> bool:
        """
        Check if the cache is still valid.
        
        Cache is invalid if:
        - Cache files don't exist
        - Any source file has changed (hash mismatch)
        - Embedder model/provider changed
        - Splitter settings changed
        
        Args:
            files: List of source files.
            embedder_model: Current embedder model name.
            embedder_provider: Current embedder provider.
            chunk_size: Current chunk size.
            chunk_overlap: Current chunk overlap.
            
        Returns:
            True if cache is valid and can be reused.
        """
        if not self.exists():
            return False
        
        try:
            metadata = self._load_metadata()
        except Exception:
            return False
        
        # Check embedder settings
        if metadata.embedder_model != embedder_model:
            return False
        if metadata.embedder_provider != embedder_provider:
            return False
        if metadata.splitter_chunk_size != chunk_size:
            return False
        if metadata.splitter_overlap != chunk_overlap:
            return False
        
        # Check if file list matches
        current_hashes = self.compute_file_hashes(files)
        if set(current_hashes.keys()) != set(metadata.file_hashes.keys()):
            return False
        
        # Check if any file content changed
        for file_path, file_hash in current_hashes.items():
            if metadata.file_hashes.get(file_path) != file_hash:
                return False
        
        return True
    
    def save(
        self,
        index: FAISSIndex,
        chunks: list[CodeChunk],
        files: list[Path],
        embedder_model: str,
        embedder_provider: str,
        chunk_size: int,
        chunk_overlap: int,
    ) -> None:
        """
        Save cache to disk.
        
        Args:
            index: FAISS index.
            chunks: List of code chunks.
            files: List of source files.
            embedder_model: Embedder model name.
            embedder_provider: Embedder provider.
            chunk_size: Chunk size.
            chunk_overlap: Chunk overlap.
        """
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Save index
        index.save(self.index_path)
        
        # Save chunks
        chunks_data = [self._chunk_to_dict(chunk) for chunk in chunks]
        with open(self.chunks_path, "w", encoding="utf-8") as f:
            json.dump(chunks_data, f, ensure_ascii=False, indent=2)
        
        # Save metadata
        metadata = CacheMetadata(
            project_path=str(self.project_path),
            file_hashes=self.compute_file_hashes(files),
            embedder_model=embedder_model,
            embedder_provider=embedder_provider,
            splitter_chunk_size=chunk_size,
            splitter_overlap=chunk_overlap,
            total_chunks=len(chunks),
        )
        with open(self.metadata_path, "w", encoding="utf-8") as f:
            json.dump({
                "project_path": metadata.project_path,
                "file_hashes": metadata.file_hashes,
                "embedder_model": metadata.embedder_model,
                "embedder_provider": metadata.embedder_provider,
                "splitter_chunk_size": metadata.splitter_chunk_size,
                "splitter_overlap": metadata.splitter_overlap,
                "total_chunks": metadata.total_chunks,
            }, f, ensure_ascii=False, indent=2)
    
    def load(self) -> tuple[FAISSIndex, list[CodeChunk]]:
        """
        Load cache from disk.
        
        Returns:
            Tuple of (FAISS index, list of code chunks).
            
        Raises:
            FileNotFoundError: If cache files don't exist.
        """
        # Load index
        index = FAISSIndex(dimension=1)  # Dummy dimension
        index.load(self.index_path)
        
        # Load chunks
        with open(self.chunks_path, "r", encoding="utf-8") as f:
            chunks_data = json.load(f)
        chunks = [self._dict_to_chunk(d) for d in chunks_data]
        
        return index, chunks
    
    def _load_metadata(self) -> CacheMetadata:
        """Load cache metadata."""
        with open(self.metadata_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return CacheMetadata(**data)
    
    def _chunk_to_dict(self, chunk: CodeChunk) -> dict:
        """Convert CodeChunk to dictionary for serialization."""
        return {
            "source_file": chunk.source_file,
            "chunk_type": chunk.chunk_type,
            "content": chunk.content,
            "metadata": chunk.metadata,
            "start_line": chunk.start_line,
            "end_line": chunk.end_line,
        }
    
    def _dict_to_chunk(self, data: dict) -> CodeChunk:
        """Convert dictionary to CodeChunk."""
        return CodeChunk(
            source_file=data["source_file"],
            chunk_type=data["chunk_type"],
            content=data["content"],
            metadata=data.get("metadata", {}),
            start_line=data.get("start_line"),
            end_line=data.get("end_line"),
        )
    
    def clear(self) -> None:
        """Clear the cache."""
        for path in [self.index_path, self.chunks_path, self.metadata_path]:
            if path.exists():
                path.unlink()
        # Remove cache directory if empty
        if self.cache_dir.exists() and not any(self.cache_dir.iterdir()):
            self.cache_dir.rmdir()
            # Also remove .docmind if empty
            docmind_dir = self.cache_dir.parent
            if docmind_dir.exists() and not any(docmind_dir.iterdir()):
                docmind_dir.rmdir()
    
    def get_cache_info(self) -> Optional[dict]:
        """
        Get cache information for display.
        
        Returns:
            Dictionary with cache info, or None if cache doesn't exist.
        """
        if not self.exists():
            return None
        
        try:
            metadata = self._load_metadata()
            return {
                "total_chunks": metadata.total_chunks,
                "embedder_model": metadata.embedder_model,
                "cached_files": len(metadata.file_hashes),
            }
        except Exception:
            return None