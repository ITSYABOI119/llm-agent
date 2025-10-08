#!/usr/bin/env python3
"""Test RAG system functionality"""

import sys
import yaml
from pathlib import Path
from tools.rag_indexer import RAGIndexer

# Set UTF-8 encoding for Windows console
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# Load config
with open('config.yaml', 'r') as f:
    config = yaml.safe_load(f)

# Override workspace to index the agent code
config['agent']['workspace'] = str(Path.cwd())

# Initialize RAG
print("Initializing RAG indexer...")
rag = RAGIndexer(config)

# Index codebase
print("\n=== INDEXING CODEBASE ===")
result = rag.index_codebase()
print(f"Files indexed: {result['files_indexed']}/{result['total_files']}")
print(f"Total chunks: {result['total_chunks']}")

# Get stats
stats = rag.get_stats()
print(f"Database contains: {stats['total_chunks']} chunks")

# Test 1: Find authentication code
print("\n=== TEST 1: Find authentication code ===")
results = rag.search('authentication login user verification', n_results=3)
print(f"Query: 'authentication login user verification'")
print(f"Results found: {results['count']}")
for i, r in enumerate(results['results'], 1):
    print(f"\n{i}. {r['file_path']}:{r['start_line']}-{r['end_line']}")
    print(f"   Distance: {r['distance']:.4f}")
    print(f"   Content preview:")
    preview = r['content'][:200].replace('\n', ' ')
    print(f"   {preview}...")

# Test 2: Find logging implementations
print("\n\n=== TEST 2: Find logging implementations ===")
results = rag.search('logging system log file structured json', n_results=3)
print(f"Query: 'logging system log file structured json'")
print(f"Results found: {results['count']}")
for i, r in enumerate(results['results'], 1):
    print(f"\n{i}. {r['file_path']}:{r['start_line']}-{r['end_line']}")
    print(f"   Distance: {r['distance']:.4f}")
    print(f"   Content preview:")
    preview = r['content'][:200].replace('\n', ' ')
    print(f"   {preview}...")

# Test 3: Find file operations
print("\n\n=== TEST 3: Find file operations ===")
results = rag.search('read write edit file filesystem operations', n_results=3)
print(f"Query: 'read write edit file filesystem operations'")
print(f"Results found: {results['count']}")
for i, r in enumerate(results['results'], 1):
    print(f"\n{i}. {r['file_path']}:{r['start_line']}-{r['end_line']}")
    print(f"   Distance: {r['distance']:.4f}")
    print(f"   Content preview:")
    preview = r['content'][:200].replace('\n', ' ')
    print(f"   {preview}...")

print("\n\n=== RAG TESTS COMPLETE ===")
