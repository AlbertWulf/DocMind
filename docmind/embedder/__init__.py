"""
Embedding module for text splitting and vector encoding.

Supports both local models (sentence-transformers) and cloud API services (OpenAI-compatible).
"""

from .splitter import TextSplitter, CodeChunk
from .encoder import (
    Encoder,
    BaseEncoder,
    LocalEncoder,
    OpenAIEncoder,
    EmbedderProvider,
)

__all__ = [
    "TextSplitter",
    "CodeChunk",
    "Encoder",
    "BaseEncoder",
    "LocalEncoder",
    "OpenAIEncoder",
    "EmbedderProvider",
]