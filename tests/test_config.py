"""
Tests for the config module.
"""

import pytest
from pathlib import Path
from pydantic import ValidationError

from docmind.config import (
    Config,
    LLMConfig,
    OutputConfig,
    load_config,
    merge_cli_args,
)


class TestConfigModels:
    """Tests for configuration models."""

    def test_default_config(self):
        """Test default configuration values."""
        config = Config()

        assert config.output.language == "zh-CN"
        assert config.llm.base_url == "http://localhost:8000/v1"
        assert config.embedder.model == "BAAI/bge-m3"
        assert config.retriever.top_k == 15

    def test_llm_config(self):
        """Test LLM configuration."""
        llm = LLMConfig(
            base_url="http://localhost:8080/v1",
            model="custom-model",
            temperature=0.5,
        )

        assert llm.base_url == "http://localhost:8080/v1"
        assert llm.model == "custom-model"
        assert llm.temperature == 0.5

    def test_output_config(self):
        """Test output configuration."""
        output = OutputConfig(
            user_guide="docs/user.md",
            dev_guide="docs/dev.md",
            language="en-US",
        )

        assert output.user_guide == "docs/user.md"
        assert output.dev_guide == "docs/dev.md"
        assert output.language == "en-US"


class TestLoadConfig:
    """Tests for configuration loading."""

    def test_load_config_no_file(self, tmp_path: Path):
        """Test loading config when no file exists."""
        config = load_config(None)
        assert isinstance(config, Config)

    def test_load_config_from_file(self, tmp_path: Path):
        """Test loading config from YAML file."""
        config_file = tmp_path / "docmind.yaml"
        config_file.write_text('''
output:
  language: "en-US"
  user_guide: "user.md"

llm:
  model: "test-model"
  temperature: 0.8
''')

        config = load_config(str(config_file))

        assert config.output.language == "en-US"
        assert config.output.user_guide == "user.md"
        assert config.llm.model == "test-model"
        assert config.llm.temperature == 0.8


class TestMergeCliArgs:
    """Tests for CLI argument merging."""

    def test_merge_simple_args(self):
        """Test merging simple CLI arguments."""
        config = Config()
        cli_args = {
            "output.language": "en-US",
        }

        merged = merge_cli_args(config, cli_args)
        assert merged.output.language == "en-US"

    def test_merge_nested_args(self):
        """Test merging nested CLI arguments."""
        config = Config()
        cli_args = {
            "llm.base_url": "http://custom:8000/v1",
            "llm.temperature": 0.9,
        }

        merged = merge_cli_args(config, cli_args)
        assert merged.llm.base_url == "http://custom:8000/v1"
        assert merged.llm.temperature == 0.9

    def test_merge_none_values_ignored(self):
        """Test that None values are ignored."""
        config = Config()
        original_language = config.output.language
        cli_args = {
            "output.language": None,
        }

        merged = merge_cli_args(config, cli_args)
        assert merged.output.language == original_language