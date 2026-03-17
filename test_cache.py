#!/usr/bin/env python3
"""测试缓存加载"""

import sys
sys.path.insert(0, '/home/richardlin/projects/tools/DocMind')

from pathlib import Path
from docmind.retriever.cache import EmbeddingCache

project_path = Path("/home/richardlin/projects/sycamore")
cache = EmbeddingCache(project_path)

print(f"Cache dir: {cache.cache_dir}")
print(f"Index path: {cache.index_path}")
print(f"Chunks path: {cache.chunks_path}")
print(f"Metadata path: {cache.metadata_path}")

print(f"\nCache exists: {cache.exists()}")

if cache.exists():
    print("\nLoading cache...")
    try:
        index, chunks = cache.load()
        print(f"✓ Loaded index with {len(index)} vectors")
        print(f"✓ Loaded {len(chunks)} chunks")
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
