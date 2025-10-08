"""
RAG (Retrieval-Augmented Generation) Indexer
Handles codebase indexing, embedding generation, and semantic search
"""

import os
import logging
import hashlib
from pathlib import Path
from typing import List, Dict, Any, Optional
import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer


class RAGIndexer:
    def __init__(self, config):
        """Initialize RAG indexer with configuration"""
        self.config = config
        self.workspace = Path(config['agent']['workspace'])

        # Initialize embedding model
        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        logging.info("Loaded embedding model: all-MiniLM-L6-v2")

        # Initialize ChromaDB
        chroma_path = self.workspace.parent / "chroma_db"
        chroma_path.mkdir(exist_ok=True)

        self.client = chromadb.PersistentClient(
            path=str(chroma_path),
            settings=Settings(anonymized_telemetry=False)
        )

        # Get or create collection
        self.collection = self.client.get_or_create_collection(
            name="codebase",
            metadata={"description": "Indexed codebase for RAG"}
        )

        logging.info(f"ChromaDB initialized at {chroma_path}")

        # File extensions to index
        self.indexable_extensions = {
            '.py', '.js', '.ts', '.jsx', '.tsx', '.java', '.cpp', '.c', '.h',
            '.css', '.html', '.json', '.yaml', '.yml', '.md', '.txt', '.sh',
            '.go', '.rs', '.rb', '.php', '.swift', '.kt'
        }

        # Chunking parameters
        self.chunk_size = 512  # tokens per chunk
        self.chunk_overlap = 50  # overlap between chunks

    def _get_file_hash(self, file_path: Path) -> str:
        """Generate hash of file content for change detection"""
        try:
            content = file_path.read_text(encoding='utf-8', errors='ignore')
            return hashlib.md5(content.encode()).hexdigest()
        except Exception:
            return ""

    def _should_index_file(self, file_path: Path) -> bool:
        """Check if file should be indexed"""
        # Check extension
        if file_path.suffix not in self.indexable_extensions:
            return False

        # Skip hidden files
        if file_path.name.startswith('.'):
            return False

        # Skip __pycache__ and node_modules
        if '__pycache__' in file_path.parts or 'node_modules' in file_path.parts:
            return False

        # Skip venv/virtualenv
        if 'venv' in file_path.parts or '.venv' in file_path.parts:
            return False

        # Skip chroma_db directory
        if 'chroma_db' in file_path.parts:
            return False

        return True

    def _chunk_text(self, text: str, file_path: str) -> List[Dict[str, Any]]:
        """Split text into semantic chunks"""
        # Simple line-based chunking for now
        # TODO: Implement smarter chunking based on code structure
        lines = text.split('\n')
        chunks = []
        current_chunk = []
        current_size = 0

        for i, line in enumerate(lines):
            line_tokens = len(line.split())

            if current_size + line_tokens > self.chunk_size and current_chunk:
                # Save current chunk
                chunk_text = '\n'.join(current_chunk)
                chunks.append({
                    'text': chunk_text,
                    'file_path': file_path,
                    'start_line': i - len(current_chunk) + 1,
                    'end_line': i
                })

                # Start new chunk with overlap
                overlap_lines = current_chunk[-self.chunk_overlap:] if len(current_chunk) > self.chunk_overlap else current_chunk
                current_chunk = overlap_lines + [line]
                current_size = sum(len(l.split()) for l in current_chunk)
            else:
                current_chunk.append(line)
                current_size += line_tokens

        # Add final chunk
        if current_chunk:
            chunk_text = '\n'.join(current_chunk)
            chunks.append({
                'text': chunk_text,
                'file_path': file_path,
                'start_line': len(lines) - len(current_chunk) + 1,
                'end_line': len(lines)
            })

        return chunks

    def scan_workspace(self) -> List[Path]:
        """Scan workspace and return all indexable files"""
        indexable_files = []

        try:
            for file_path in self.workspace.rglob('*'):
                if file_path.is_file() and self._should_index_file(file_path):
                    indexable_files.append(file_path)

            logging.info(f"Found {len(indexable_files)} indexable files")
        except Exception as e:
            logging.error(f"Error scanning workspace: {e}")

        return indexable_files

    def index_file(self, file_path: Path) -> int:
        """Index a single file and return number of chunks created"""
        try:
            # Read file content
            content = file_path.read_text(encoding='utf-8', errors='ignore')
            rel_path = str(file_path.relative_to(self.workspace))

            # Generate file hash
            file_hash = self._get_file_hash(file_path)

            # Chunk the content
            chunks = self._chunk_text(content, rel_path)

            if not chunks:
                return 0

            # Generate embeddings
            texts = [chunk['text'] for chunk in chunks]
            embeddings = self.embedding_model.encode(texts, show_progress_bar=False)

            # Prepare data for ChromaDB
            ids = [f"{rel_path}::{i}" for i in range(len(chunks))]
            metadatas = [
                {
                    'file_path': chunk['file_path'],
                    'start_line': chunk['start_line'],
                    'end_line': chunk['end_line'],
                    'file_hash': file_hash,
                    'extension': file_path.suffix
                }
                for chunk in chunks
            ]

            # Add to collection (upsert to handle updates)
            self.collection.upsert(
                ids=ids,
                embeddings=embeddings.tolist(),
                documents=texts,
                metadatas=metadatas
            )

            logging.info(f"Indexed {rel_path}: {len(chunks)} chunks")
            return len(chunks)

        except Exception as e:
            logging.error(f"Error indexing {file_path}: {e}")
            return 0

    def index_codebase(self) -> Dict[str, Any]:
        """Index entire codebase"""
        logging.info("Starting codebase indexing...")

        files = self.scan_workspace()
        total_chunks = 0
        indexed_files = 0

        for file_path in files:
            chunks = self.index_file(file_path)
            if chunks > 0:
                total_chunks += chunks
                indexed_files += 1

        result = {
            'success': True,
            'files_indexed': indexed_files,
            'total_files': len(files),
            'total_chunks': total_chunks
        }

        logging.info(f"Indexing complete: {indexed_files} files, {total_chunks} chunks")
        return result

    def search(self, query: str, n_results: int = 5) -> Dict[str, Any]:
        """Semantic search across indexed codebase"""
        try:
            # Generate query embedding
            query_embedding = self.embedding_model.encode([query])[0]

            # Search in ChromaDB
            results = self.collection.query(
                query_embeddings=[query_embedding.tolist()],
                n_results=n_results
            )

            # Format results
            formatted_results = []
            if results['documents'] and results['documents'][0]:
                for i, doc in enumerate(results['documents'][0]):
                    metadata = results['metadatas'][0][i]
                    formatted_results.append({
                        'file_path': metadata['file_path'],
                        'start_line': metadata['start_line'],
                        'end_line': metadata['end_line'],
                        'content': doc,
                        'distance': results['distances'][0][i] if results['distances'] else None
                    })

            return {
                'success': True,
                'query': query,
                'results': formatted_results,
                'count': len(formatted_results)
            }

        except Exception as e:
            logging.error(f"Error searching: {e}")
            return {
                'success': False,
                'error': str(e),
                'results': [],
                'count': 0
            }

    def delete_file_chunks(self, file_path: str) -> Dict[str, Any]:
        """Delete all chunks for a specific file from the index"""
        try:
            # Normalize file path
            if not os.path.isabs(file_path):
                full_path = self.workspace / file_path
            else:
                full_path = Path(file_path)

            file_path_str = str(full_path.relative_to(self.workspace.parent))

            # Get all chunks for this file
            results = self.collection.get(
                where={"file_path": file_path_str}
            )

            if results['ids']:
                # Delete all chunks with these IDs
                self.collection.delete(ids=results['ids'])
                logging.info(f"Deleted {len(results['ids'])} chunks for {file_path_str}")
                return {
                    'success': True,
                    'deleted_chunks': len(results['ids']),
                    'file_path': file_path_str
                }
            else:
                return {
                    'success': True,
                    'deleted_chunks': 0,
                    'file_path': file_path_str
                }

        except Exception as e:
            logging.error(f"Error deleting chunks for {file_path}: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    def clear_index(self) -> Dict[str, Any]:
        """Clear all indexed data"""
        try:
            # Delete the collection and recreate it
            self.client.delete_collection(name="codebase")
            self.collection = self.client.get_or_create_collection(
                name="codebase",
                metadata={"description": "Indexed codebase for RAG"}
            )
            logging.info("Cleared RAG index")
            return {
                'success': True,
                'message': 'Index cleared successfully'
            }
        except Exception as e:
            logging.error(f"Error clearing index: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    def get_stats(self) -> Dict[str, Any]:
        """Get indexing statistics"""
        try:
            count = self.collection.count()
            return {
                'success': True,
                'total_chunks': count,
                'collection_name': self.collection.name
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
