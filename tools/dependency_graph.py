"""
Dependency Graph Builder - Build and query codebase dependency graph (Phase 3)

Uses AST parsing to build a networkx graph of:
- File-to-file import relationships
- Function/class definitions per file
- Dependency traversal (N-hops)

Enables understanding code relationships for better context gathering.
"""

import ast
import logging
import pickle
from pathlib import Path
from typing import List, Dict, Set, Optional, Any
import networkx as nx


class DependencyGraph:
    """
    Build and query codebase dependency graph using AST parsing
    """

    def __init__(self, workspace_path: Path):
        """
        Initialize dependency graph builder

        Args:
            workspace_path: Path to workspace directory
        """
        self.workspace = workspace_path
        self.graph = nx.DiGraph()
        self.file_metadata = {}  # file_path -> {functions, classes, imports}

        # Configuration
        self.max_depth = 2  # Maximum hops in dependency graph
        self.indexable_extensions = {'.py'}  # Start with Python only

    def build_graph(self) -> nx.DiGraph:
        """
        Parse all files and build import/dependency graph

        Returns:
            NetworkX directed graph
        """
        logging.info(f"[DEPGRAPH] Building dependency graph for {self.workspace}")

        # Clear existing graph
        self.graph.clear()
        self.file_metadata.clear()

        # Find all Python files
        python_files = list(self.workspace.rglob("*.py"))

        # Filter out venv, __pycache__, etc.
        python_files = [
            f for f in python_files
            if not any(part in f.parts for part in ['venv', '.venv', '__pycache__', 'node_modules', '.git'])
        ]

        logging.info(f"[DEPGRAPH] Found {len(python_files)} Python files to analyze")

        # Parse each file
        for file_path in python_files:
            self._parse_python_file(file_path)

        logging.info(f"[DEPGRAPH] Graph built: {self.graph.number_of_nodes()} nodes, {self.graph.number_of_edges()} edges")

        return self.graph

    def _parse_python_file(self, file_path: Path):
        """
        Parse a Python file and extract imports, functions, classes

        Args:
            file_path: Path to Python file
        """
        try:
            content = file_path.read_text(encoding='utf-8', errors='ignore')
            tree = ast.parse(content, filename=str(file_path))

            # Convert to relative path
            rel_path = str(file_path.relative_to(self.workspace))

            # Extract metadata
            imports = self._extract_imports(tree, file_path)
            functions = self._extract_functions(tree)
            classes = self._extract_classes(tree)

            # Store metadata
            self.file_metadata[rel_path] = {
                'imports': imports,
                'functions': functions,
                'classes': classes,
                'path': str(file_path)
            }

            # Add node to graph
            self.graph.add_node(
                rel_path,
                type='file',
                functions=functions,
                classes=classes,
                imports=imports
            )

            # Add edges for imports
            for imported_file in imports:
                self.graph.add_edge(rel_path, imported_file, type='import')

        except Exception as e:
            logging.warning(f"[DEPGRAPH] Error parsing {file_path}: {e}")

    def _extract_imports(self, tree: ast.AST, file_path: Path) -> List[str]:
        """
        Extract import statements from AST

        Args:
            tree: AST tree
            file_path: Path to file (for resolving relative imports)

        Returns:
            List of imported file paths (relative to workspace)
        """
        imports = []

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    # Convert module name to file path
                    imported_file = self._module_to_file(alias.name, file_path)
                    if imported_file:
                        imports.append(imported_file)

            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    # From X import Y
                    imported_file = self._module_to_file(node.module, file_path)
                    if imported_file:
                        imports.append(imported_file)

        return list(set(imports))  # Remove duplicates

    def _module_to_file(self, module_name: str, current_file: Path) -> Optional[str]:
        """
        Convert module name to file path

        Args:
            module_name: Module name (e.g., 'tools.rag_indexer')
            current_file: Current file path (for relative imports)

        Returns:
            Relative file path if it exists, None otherwise
        """
        # Convert module name to file path
        # E.g., 'tools.rag_indexer' -> 'tools/rag_indexer.py'
        module_path = module_name.replace('.', '/')

        # Try as file
        file_path = self.workspace / f"{module_path}.py"
        if file_path.exists():
            return str(file_path.relative_to(self.workspace))

        # Try as package (__init__.py)
        package_path = self.workspace / module_path / "__init__.py"
        if package_path.exists():
            return str(package_path.relative_to(self.workspace))

        # Not found in workspace (likely external library)
        return None

    def _extract_functions(self, tree: ast.AST) -> List[str]:
        """
        Extract function names from AST

        Args:
            tree: AST tree

        Returns:
            List of function names
        """
        functions = []

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                functions.append(node.name)

        return functions

    def _extract_classes(self, tree: ast.AST) -> List[str]:
        """
        Extract class names from AST

        Args:
            tree: AST tree

        Returns:
            List of class names
        """
        classes = []

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                classes.append(node.name)

        return classes

    def find_related_files(
        self,
        file_path: str,
        depth: int = 2,
        direction: str = 'both'
    ) -> List[str]:
        """
        Find files within N hops in dependency graph

        Args:
            file_path: File path (relative to workspace)
            depth: Maximum hops (default: 2)
            direction: 'both', 'dependencies', or 'dependents'

        Returns:
            List of related file paths
        """
        if file_path not in self.graph:
            logging.warning(f"[DEPGRAPH] File not in graph: {file_path}")
            return []

        related = set()

        if direction in ['both', 'dependencies']:
            # Files this file depends on (outgoing edges)
            try:
                paths = nx.single_source_shortest_path_length(
                    self.graph,
                    file_path,
                    cutoff=depth
                )
                related.update(paths.keys())
            except Exception as e:
                logging.warning(f"[DEPGRAPH] Error finding dependencies: {e}")

        if direction in ['both', 'dependents']:
            # Files that depend on this file (incoming edges)
            try:
                # Reverse the graph
                reversed_graph = self.graph.reverse()
                paths = nx.single_source_shortest_path_length(
                    reversed_graph,
                    file_path,
                    cutoff=depth
                )
                related.update(paths.keys())
            except Exception as e:
                logging.warning(f"[DEPGRAPH] Error finding dependents: {e}")

        # Remove the original file
        related.discard(file_path)

        return list(related)

    def get_file_dependencies(self, file_path: str) -> List[str]:
        """
        Get direct dependencies (files this file imports)

        Args:
            file_path: File path (relative to workspace)

        Returns:
            List of file paths this file directly depends on
        """
        if file_path not in self.graph:
            return []

        # Get outgoing edges (dependencies)
        return list(self.graph.successors(file_path))

    def get_file_dependents(self, file_path: str) -> List[str]:
        """
        Get files that depend on this file (files that import this)

        Args:
            file_path: File path (relative to workspace)

        Returns:
            List of file paths that depend on this file
        """
        if file_path not in self.graph:
            return []

        # Get incoming edges (dependents)
        return list(self.graph.predecessors(file_path))

    def get_file_metadata(self, file_path: str) -> Optional[Dict[str, Any]]:
        """
        Get metadata for a file (functions, classes, imports)

        Args:
            file_path: File path (relative to workspace)

        Returns:
            Metadata dict or None if file not found
        """
        return self.file_metadata.get(file_path)

    def save_graph(self, cache_path: str):
        """
        Serialize graph to pickle for caching

        Args:
            cache_path: Path to save graph
        """
        try:
            cache_file = Path(cache_path)
            cache_file.parent.mkdir(parents=True, exist_ok=True)

            with open(cache_file, 'wb') as f:
                pickle.dump({
                    'graph': self.graph,
                    'metadata': self.file_metadata
                }, f)

            logging.info(f"[DEPGRAPH] Graph saved to {cache_path}")

        except Exception as e:
            logging.error(f"[DEPGRAPH] Error saving graph: {e}")

    def load_graph(self, cache_path: str) -> bool:
        """
        Load graph from cache

        Args:
            cache_path: Path to cached graph

        Returns:
            True if loaded successfully, False otherwise
        """
        try:
            cache_file = Path(cache_path)
            if not cache_file.exists():
                return False

            with open(cache_file, 'rb') as f:
                data = pickle.load(f)

            self.graph = data['graph']
            self.file_metadata = data['metadata']

            logging.info(f"[DEPGRAPH] Graph loaded from {cache_path}")
            logging.info(f"[DEPGRAPH] {self.graph.number_of_nodes()} nodes, {self.graph.number_of_edges()} edges")

            return True

        except Exception as e:
            logging.error(f"[DEPGRAPH] Error loading graph: {e}")
            return False

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get graph statistics

        Returns:
            Statistics dict
        """
        return {
            'num_files': self.graph.number_of_nodes(),
            'num_dependencies': self.graph.number_of_edges(),
            'avg_dependencies': self.graph.number_of_edges() / max(self.graph.number_of_nodes(), 1),
            'isolated_files': len([n for n in self.graph.nodes() if self.graph.degree(n) == 0]),
            'most_depended_on': self._get_most_depended_on(top_n=5)
        }

    def _get_most_depended_on(self, top_n: int = 5) -> List[Tuple[str, int]]:
        """
        Get files with most dependents

        Args:
            top_n: Number of top files to return

        Returns:
            List of (file_path, num_dependents) tuples
        """
        dependents_count = [
            (node, self.graph.in_degree(node))
            for node in self.graph.nodes()
        ]

        # Sort by in-degree (descending)
        dependents_count.sort(key=lambda x: x[1], reverse=True)

        return dependents_count[:top_n]

    def visualize_subgraph(self, file_path: str, depth: int = 1) -> str:
        """
        Create ASCII visualization of file's dependency subgraph

        Args:
            file_path: File to visualize
            depth: Depth of visualization

        Returns:
            ASCII art representation
        """
        if file_path not in self.graph:
            return f"File not found: {file_path}"

        # Get related files
        related = self.find_related_files(file_path, depth=depth)

        # Build ASCII representation
        lines = [f"Dependency graph for: {file_path}", ""]

        # Show dependencies (files this imports)
        deps = self.get_file_dependencies(file_path)
        if deps:
            lines.append("Dependencies (imports):")
            for dep in deps:
                lines.append(f"  → {dep}")
            lines.append("")

        # Show dependents (files that import this)
        dependents = self.get_file_dependents(file_path)
        if dependents:
            lines.append("Dependents (imported by):")
            for dep in dependents:
                lines.append(f"  ← {dep}")

        return "\n".join(lines)
