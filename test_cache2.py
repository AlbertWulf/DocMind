#!/usr/bin/env python3
"""测试缓存验证"""

import sys
sys.path.insert(0, '/home/richardlin/projects/tools/DocMind')

from pathlib import Path
from docmind.retriever.cache import EmbeddingCache
from docmind.config import load_config

project_path = Path("/home/richardlin/projects/sycamore")
config_path = Path("/home/richardlin/projects/sycamore/docmind.yaml")

cache = EmbeddingCache(project_path)
config = load_config(config_path)

# 获取 Python 文件
from docmind.analyzer.parser import find_python_files
python_files = find_python_files(
    project_path,
    exclude_patterns=config.analyzer.exclude,
)

print(f"Found {len(python_files)} Python files")
print(f"\nCache exists: {cache.exists()}")

print("\nChecking cache validity...")
try:
    is_valid = cache.is_valid(
        files=python_files,
        embedder_model=config.embedder.model,
        embedder_provider=config.embedder.provider,
        chunk_size=config.splitter.chunk_size,
        chunk_overlap=config.splitter.chunk_overlap,
    )
    print(f"Cache is valid: {is_valid}")
except Exception as e:
    print(f"✗ Error: {e}")
    import traceback
    traceback.print_exc()
