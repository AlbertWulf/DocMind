"""
Configuration management module for DocMind.
"""

from pathlib import Path
from typing import Any, Optional

import yaml
from pydantic import BaseModel, Field


class ProjectConfig(BaseModel):
    """Project information configuration."""

    name: str = ""
    version: str = ""
    description: str = ""
    author: str = ""


class CustomRequirementsConfig(BaseModel):
    """Custom requirements file configuration."""

    file: str = ""
    apply_to: dict[str, bool] = Field(default_factory=lambda: {"user_guide": True, "dev_guide": True})


class OutputConfig(BaseModel):
    """Output configuration."""

    user_guide: str = "user-guide.md"
    dev_guide: str = "dev-guide.md"
    language: str = "zh-CN"


class AnalyzerConfig(BaseModel):
    """Code analyzer configuration."""

    source_dir: str = "."
    exclude: list[str] = Field(
        default_factory=lambda: [
            "tests/",
            "examples/",
            "docs/",
            "**/migrations/",
            "**/__pycache__/",
            "**/*.egg-info/",
            "**/venv/",
            "**/.venv/",
            "**/node_modules/",
        ]
    )
    include_private: bool = False


class LLMConfig(BaseModel):
    """LLM configuration."""

    base_url: str = "http://localhost:8000/v1"
    model: str = "Qwen/Qwen2.5-72B-Instruct"
    api_key: str = "EMPTY"
    temperature: float = 0.7
    max_tokens: int = 4096
    timeout: int = 300


class EmbedderConfig(BaseModel):
    """Embedding model configuration."""

    provider: str = "local"  # "local" or "openai"
    model: str = "BAAI/bge-m3"
    device: str = "cuda"  # Only for local: cuda, cpu, auto
    batch_size: int = 32
    max_length: int = 512  # Only for local
    api_key: str = ""  # Required for openai provider
    base_url: Optional[str] = None  # Optional for openai-compatible APIs
    dimensions: Optional[int] = None  # Output dimensions (for text-embedding-3-*)
    timeout: int = 60  # API timeout in seconds


class RetrieverConfig(BaseModel):
    """Retrieval configuration."""

    top_k: int = 15


class SplitterConfig(BaseModel):
    """Text splitting configuration."""

    chunk_size: int = 500
    chunk_overlap: int = 100


class UserGuideGeneratorConfig(BaseModel):
    """User guide generator configuration."""

    include_installation: bool = True
    include_quickstart: bool = True
    include_examples: bool = True


class DevGuideGeneratorConfig(BaseModel):
    """Developer guide generator configuration."""

    include_architecture: bool = True
    include_api: bool = True
    include_contributing: bool = True


class MermaidConfig(BaseModel):
    """Mermaid diagram configuration."""

    enabled: bool = True
    max_diagrams: int = 5


class GeneratorConfig(BaseModel):
    """Document generator configuration."""

    user_guide: UserGuideGeneratorConfig = Field(default_factory=UserGuideGeneratorConfig)
    dev_guide: DevGuideGeneratorConfig = Field(default_factory=DevGuideGeneratorConfig)
    mermaid: MermaidConfig = Field(default_factory=MermaidConfig)


class Config(BaseModel):
    """Main configuration for DocMind."""

    project: ProjectConfig = Field(default_factory=ProjectConfig)
    custom_requirements: CustomRequirementsConfig = Field(default_factory=CustomRequirementsConfig)
    output: OutputConfig = Field(default_factory=OutputConfig)
    analyzer: AnalyzerConfig = Field(default_factory=AnalyzerConfig)
    llm: LLMConfig = Field(default_factory=LLMConfig)
    embedder: EmbedderConfig = Field(default_factory=EmbedderConfig)
    retriever: RetrieverConfig = Field(default_factory=RetrieverConfig)
    splitter: SplitterConfig = Field(default_factory=SplitterConfig)
    generator: GeneratorConfig = Field(default_factory=GeneratorConfig)


def load_config(config_path: Optional[str] = None) -> Config:
    """
    Load configuration from YAML file.

    Args:
        config_path: Path to configuration file. If None, searches for default locations.

    Returns:
        Config object with loaded or default values.
    """
    config = Config()

    if config_path is None:
        # Search for config file in common locations
        search_paths = [
            Path.cwd() / "docmind.yaml",
            Path.cwd() / "docmind.yml",
            Path.cwd() / ".docmind" / "config.yaml",
        ]
        for path in search_paths:
            if path.exists():
                config_path = str(path)
                break

    if config_path and Path(config_path).exists():
        with open(config_path, encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        config = Config(**data)

    return config


def merge_cli_args(config: Config, cli_args: dict[str, Any]) -> Config:
    """
    Merge CLI arguments into configuration.

    CLI arguments take precedence over config file values.

    Args:
        config: Base configuration.
        cli_args: Dictionary of CLI arguments (using dot notation for nested keys).

    Returns:
        Updated configuration.
    """
    config_dict = config.model_dump()

    for key, value in cli_args.items():
        if value is None:
            continue

        # Handle dot notation for nested keys (e.g., "llm.base_url")
        keys = key.split(".")
        current = config_dict

        for k in keys[:-1]:
            if k not in current:
                current[k] = {}
            current = current[k]

        current[keys[-1]] = value

    return Config(**config_dict)


def create_default_config(output_path: str) -> None:
    """
    Create a default configuration file.

    Args:
        output_path: Path where the configuration file will be created.
    """
    default_config = """# DocMind Configuration File
# Generated by 'docmind init'

# Project information (optional - will be extracted from code if not provided)
project:
  name: ""
  version: ""
  description: ""
  author: ""

# Custom requirements file
custom_requirements:
  file: "docmind-requirements.md"
  apply_to:
    user_guide: true
    dev_guide: true

# Output configuration
output:
  user_guide: "user-guide.md"
  dev_guide: "dev-guide.md"
  language: "zh-CN"

# Code analysis configuration
analyzer:
  source_dir: "."
  exclude:
    - "tests/"
    - "examples/"
    - "docs/"
    - "**/migrations/"
    - "**/__pycache__/"
    - "**/*.egg-info/"
    - "**/venv/"
    - "**/.venv/"
    - "**/node_modules/"
  include_private: false

# LLM configuration (vLLM OpenAI-compatible mode)
llm:
  base_url: "http://localhost:8000/v1"
  model: "Qwen/Qwen2.5-72B-Instruct"
  api_key: "EMPTY"
  temperature: 0.7
  max_tokens: 4096
  timeout: 300

# Embedding model configuration
# Provider options: "local" (sentence-transformers) or "openai" (API)
embedder:
  provider: "local"                    # "local" or "openai"
  model: "BAAI/bge-m3"                 # Model name
  device: "cuda"                       # For local: cuda, cpu, or auto
  batch_size: 32
  max_length: 512                      # For local: max sequence length
  # api_key: ""                        # For openai: API key (required for openai)
  # base_url: ""                       # For openai: custom API endpoint
  # dimensions: null                   # For openai: output dimensions
  # timeout: 60                        # For openai: API timeout in seconds

# Retrieval configuration
retriever:
  top_k: 15

# Text splitting configuration
splitter:
  chunk_size: 500
  chunk_overlap: 100

# Document generation configuration
generator:
  user_guide:
    include_installation: true
    include_quickstart: true
    include_examples: true
  dev_guide:
    include_architecture: true
    include_api: true
    include_contributing: true
  mermaid:
    enabled: true
    max_diagrams: 5
"""
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(default_config)