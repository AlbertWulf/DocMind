"""
Vector encoder for generating embeddings.

Supports both:
- Local models via sentence-transformers
- Cloud API services via OpenAI-compatible API (OpenAI, vLLM, etc.)
"""

from abc import ABC, abstractmethod
from enum import Enum
from typing import Optional

import numpy as np


class EmbedderProvider(Enum):
    """Supported embedding providers."""

    LOCAL = "local"  # sentence-transformers local model
    OPENAI = "openai"  # OpenAI or OpenAI-compatible API


class BaseEncoder(ABC):
    """Abstract base class for encoders."""

    @abstractmethod
    def encode(self, texts: list[str]) -> np.ndarray:
        """Encode a list of texts into vectors."""
        pass

    @abstractmethod
    def encode_single(self, text: str) -> np.ndarray:
        """Encode a single text string."""
        pass

    @abstractmethod
    def get_embedding_dim(self) -> int:
        """Get the dimension of the embeddings."""
        pass

    @abstractmethod
    def is_loaded(self) -> bool:
        """Check if the model is loaded/ready."""
        pass


class LocalEncoder(BaseEncoder):
    """
    Encode text into vectors using sentence-transformers (local model).
    """

    def __init__(
        self,
        model_name: str = "BAAI/bge-m3",
        device: str = "cuda",
        batch_size: int = 32,
        max_length: int = 512,
    ):
        """
        Initialize the local encoder.

        Args:
            model_name: Name of the sentence-transformers model.
            device: Device to use for inference (cuda, cpu, or auto).
            batch_size: Batch size for encoding.
            max_length: Maximum sequence length for the model.
        """
        self.model_name = model_name
        self.device = self._resolve_device(device)
        self.batch_size = batch_size
        self.max_length = max_length
        self.model = None

    def _resolve_device(self, device: str) -> str:
        """Resolve the device to use."""
        if device == "auto":
            try:
                import torch

                if torch.cuda.is_available():
                    return "cuda"
                elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
                    return "mps"
                else:
                    return "cpu"
            except ImportError:
                return "cpu"
        return device

    def load_model(self) -> None:
        """Load the embedding model."""
        if self.model is None:
            from sentence_transformers import SentenceTransformer

            self.model = SentenceTransformer(
                self.model_name,
                device=self.device,
                trust_remote_code=True,
            )
            self.model.max_seq_length = self.max_length

    def encode(self, texts: list[str]) -> np.ndarray:
        """
        Encode a list of texts into vectors.

        Args:
            texts: List of text strings to encode.

        Returns:
            Numpy array of shape (num_texts, embedding_dim).
        """
        self.load_model()

        embeddings = self.model.encode(
            texts,
            batch_size=self.batch_size,
            show_progress_bar=False,
            convert_to_numpy=True,
            normalize_embeddings=True,
        )

        return embeddings

    def encode_single(self, text: str) -> np.ndarray:
        """
        Encode a single text string.

        Args:
            text: Text string to encode.

        Returns:
            Numpy array of shape (embedding_dim,).
        """
        embeddings = self.encode([text])
        return embeddings[0]

    def get_embedding_dim(self) -> int:
        """Get the dimension of the embeddings."""
        self.load_model()
        return self.model.get_sentence_embedding_dimension()

    def is_loaded(self) -> bool:
        """Check if the model is loaded."""
        return self.model is not None

    def unload_model(self) -> None:
        """Unload the model from memory."""
        if self.model is not None:
            del self.model
            self.model = None

            # Clear GPU memory if using CUDA
            try:
                import torch

                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
            except ImportError:
                pass


class OpenAIEncoder(BaseEncoder):
    """
    Encode text into vectors using OpenAI-compatible embedding API.

    Supports OpenAI, vLLM embedding endpoint, and other compatible services.
    """

    # Known embedding dimensions for common models
    MODEL_DIMENSIONS = {
        # OpenAI models
        "text-embedding-3-small": 1536,
        "text-embedding-3-large": 3072,
        "text-embedding-ada-002": 1536,
        # Common dimensions that can be specified
        "small": 512,
        "medium": 1024,
        "large": 1536,
    }

    def __init__(
        self,
        model: str = "text-embedding-3-small",
        api_key: str = "",
        base_url: Optional[str] = None,
        batch_size: int = 100,
        dimensions: Optional[int] = None,
        timeout: int = 60,
    ):
        """
        Initialize the OpenAI encoder.

        Args:
            model: Model name to use.
            api_key: API key for the service.
            base_url: Base URL for the API (optional, defaults to OpenAI).
            batch_size: Batch size for encoding (API limit).
            dimensions: Output dimensions (for models that support it).
            timeout: Request timeout in seconds.
        """
        self.model = model
        self.api_key = api_key
        self.base_url = base_url
        self.batch_size = batch_size
        self.dimensions = dimensions
        self.timeout = timeout
        self._client = None
        self._embedding_dim = self._resolve_embedding_dim()

    def _resolve_embedding_dim(self) -> int:
        """Resolve the embedding dimension."""
        if self.dimensions:
            return self.dimensions
        return self.MODEL_DIMENSIONS.get(self.model, 1536)

    def _get_client(self):
        """Get or create the OpenAI client."""
        if self._client is None:
            from openai import OpenAI

            kwargs = {"api_key": self.api_key, "timeout": self.timeout}
            if self.base_url:
                kwargs["base_url"] = self.base_url

            self._client = OpenAI(**kwargs)
        return self._client

    def encode(self, texts: list[str]) -> np.ndarray:
        """
        Encode a list of texts into vectors.

        Args:
            texts: List of text strings to encode.

        Returns:
            Numpy array of shape (num_texts, embedding_dim).
        """
        client = self._get_client()
        all_embeddings = []

        # Process in batches
        for i in range(0, len(texts), self.batch_size):
            batch = texts[i : i + self.batch_size]

            # Build API kwargs
            api_kwargs = {
                "model": self.model,
                "input": batch,
                "encoding_format": "float",
            }

            # Add dimensions if supported
            if self.dimensions and "text-embedding-3" in self.model:
                api_kwargs["dimensions"] = self.dimensions

            response = client.embeddings.create(**api_kwargs)

            # Extract embeddings in order
            batch_embeddings = [item.embedding for item in response.data]
            all_embeddings.extend(batch_embeddings)

        return np.array(all_embeddings, dtype=np.float32)

    def encode_single(self, text: str) -> np.ndarray:
        """
        Encode a single text string.

        Args:
            text: Text string to encode.

        Returns:
            Numpy array of shape (embedding_dim,).
        """
        embeddings = self.encode([text])
        return embeddings[0]

    def get_embedding_dim(self) -> int:
        """Get the dimension of the embeddings."""
        return self._embedding_dim

    def is_loaded(self) -> bool:
        """Check if the encoder is ready."""
        return bool(self.api_key)

    def test_connection(self) -> bool:
        """Test the connection to the embedding API."""
        try:
            self.encode(["test"])
            return True
        except Exception:
            return False


class Encoder:
    """
    Unified encoder that supports both local and API-based embedding.

    This is the main encoder class used by DocMind. It automatically
    selects the appropriate backend based on configuration.
    """

    def __init__(
        self,
        provider: str = "local",
        model: str = "BAAI/bge-m3",
        device: str = "cuda",
        batch_size: int = 32,
        max_length: int = 512,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        dimensions: Optional[int] = None,
        timeout: int = 60,
    ):
        """
        Initialize the encoder.

        Args:
            provider: Embedding provider - "local" or "openai".
            model: Model name.
            device: Device for local model (cuda, cpu, auto).
            batch_size: Batch size for encoding.
            max_length: Max sequence length for local model.
            api_key: API key for cloud services.
            base_url: Base URL for API (optional).
            dimensions: Output dimensions (for supported models).
            timeout: API timeout in seconds.
        """
        self.provider = EmbedderProvider(provider)
        self._encoder: BaseEncoder

        if self.provider == EmbedderProvider.LOCAL:
            self._encoder = LocalEncoder(
                model_name=model,
                device=device,
                batch_size=batch_size,
                max_length=max_length,
            )
        elif self.provider == EmbedderProvider.OPENAI:
            if not api_key:
                raise ValueError("api_key is required for OpenAI/embedding API provider")
            self._encoder = OpenAIEncoder(
                model=model,
                api_key=api_key,
                base_url=base_url,
                batch_size=batch_size,
                dimensions=dimensions,
                timeout=timeout,
            )
        else:
            raise ValueError(f"Unknown provider: {provider}")

    def encode(self, texts: list[str]) -> np.ndarray:
        """Encode a list of texts into vectors."""
        return self._encoder.encode(texts)

    def encode_chunks(self, chunks) -> np.ndarray:
        """Encode a list of CodeChunk objects."""
        texts = [chunk.content for chunk in chunks]
        return self.encode(texts)

    def encode_single(self, text: str) -> np.ndarray:
        """Encode a single text string."""
        return self._encoder.encode_single(text)

    def get_embedding_dim(self) -> int:
        """Get the dimension of the embeddings."""
        return self._encoder.get_embedding_dim()

    def is_loaded(self) -> bool:
        """Check if the encoder is ready."""
        return self._encoder.is_loaded()

    def unload_model(self) -> None:
        """Unload the model from memory (local only)."""
        if hasattr(self._encoder, "unload_model"):
            self._encoder.unload_model()

    def test_connection(self) -> bool:
        """Test the encoder connection."""
        if hasattr(self._encoder, "test_connection"):
            return self._encoder.test_connection()
        return self.is_loaded()