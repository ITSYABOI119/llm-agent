#!/usr/bin/env python3
"""
LLM Agent - Main agent logic
Handles communication with Ollama API and tool execution
"""

import json
import logging
import os
import sys
import time
import yaml
import requests
from pathlib import Path

# Import tools
from tools.filesystem import FileSystemTools
from tools.commands import CommandTools
from tools.system import SystemTools
from tools.search import SearchTools
from tools.process import ProcessTools
from tools.network import NetworkTools
from tools.data import DataTools
from tools.memory import MemorySystem
from tools.session_history import SessionHistory
from tools.logging_tools import LogManager, LogAnalyzer, LogQuery
from tools.task_analyzer import TaskAnalyzer
from tools.task_classifier import TaskClassifier  # Phase 2: Smart routing
from tools.model_router import ModelRouter
from tools.two_phase_executor import TwoPhaseExecutor
from safety.sandbox import Sandbox
from safety.validators import Validator

# Import new Cursor-style improvements
from tools.context_gatherer import ContextGatherer
from tools.verifier import ActionVerifier
from tools.model_manager import SmartModelManager
from tools.token_counter import TokenCounter, ContextCompressor
from tools.structured_planner import StructuredPlanner
from tools.progressive_retry import ProgressiveRetrySystem  # Phase 3

# Optional RAG support
try:
    from tools.rag_indexer import RAGIndexer
    RAG_AVAILABLE = True
except ImportError:
    RAG_AVAILABLE = False
    logging.warning("RAG features unavailable: chromadb or tiktoken not installed")


class Agent:
    def __init__(self, config_path="config.yaml"):
        """Initialize the agent with configuration"""
        self.config = self._load_config(config_path)
        self._setup_logging()
        self._setup_workspace()
        
        # Initialize tools
        self.fs_tools = FileSystemTools(self.config)
        self.cmd_tools = CommandTools(self.config)
        self.sys_tools = SystemTools(self.config)
        self.search_tools = SearchTools(self.config)
        self.process_tools = ProcessTools(self.config)
        self.network_tools = NetworkTools(self.config)
        self.data_tools = DataTools(self.config)
        self.memory = MemorySystem(self.config)
        self.history = SessionHistory(self.config)
        
        # Initialize enhanced logging
        self.log_manager = LogManager(self.config)
        self.log_analyzer = LogAnalyzer(self.config)
        self.log_query = LogQuery(self.config)

        # Initialize RAG indexer (optional)
        if RAG_AVAILABLE:
            self.rag = RAGIndexer(self.config)
        else:
            self.rag = None

        # Initialize safety
        self.sandbox = Sandbox(self.config)
        self.validator = Validator(self.config)

        # Initialize multi-model system
        self.task_analyzer = TaskAnalyzer()  # Legacy analyzer
        self.task_classifier = TaskClassifier()  # Phase 2: Smart routing
        self.model_router = ModelRouter(self.config)
        self.two_phase_executor = TwoPhaseExecutor(
            f"http://{self.config['ollama']['host']}:{self.config['ollama']['port']}",
            self.config
        )

        # Ollama API endpoint
        self.api_url = f"http://{self.config['ollama']['host']}:{self.config['ollama']['port']}"

        # Initialize Cursor-style improvements (Phase 1)
        self.token_counter = TokenCounter(max_tokens=8000)  # OpenThinker's 8K context
        self.context_compressor = ContextCompressor()
        self.structured_planner = StructuredPlanner()

        self.context_gatherer = ContextGatherer(
            self.config, self.search_tools, self.fs_tools, self.token_counter
        )
        self.verifier = ActionVerifier(self.config, self.fs_tools)
        self.model_manager = SmartModelManager(self.api_url, self.config)

        # Phase 3: Progressive retry system
        self.retry_system = ProgressiveRetrySystem(self.model_manager, self.model_router)

        # Note: Model swaps take ~2.5s on Windows (disk → VRAM)
        # Phase 2 minimizes swaps, Phase 3 adds smart retries
        logging.info("Agent initialized with Phase 1+2+3 improvements")

        # Track files created/modified in current session
        self.session_files = {
            "created": set(),      # Files created via write_file
            "modified": set(),     # Files modified via edit_file
            "read": set(),         # Files read
            "deleted": set()       # Files deleted
        }

        logging.info(f"Agent initialized: {self.config['agent']['name']}")
        logging.info(f"Workspace: {self.config['agent']['workspace']}")
        logging.info(f"Ollama API: {self.api_url}")
    
    def _load_config(self, config_path):
        """Load configuration from YAML file"""
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
    
    def _setup_logging(self):
        """Configure logging"""
        log_level = getattr(logging, self.config['logging']['level'])
        log_file = self.config['logging']['log_file']
        
        # Create logs directory if it doesn't exist
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        
        logging.basicConfig(
            level=log_level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file, encoding='utf-8'),
                logging.StreamHandler(sys.stdout)
            ]
        )
    
    def _setup_workspace(self):
        """Create workspace directory if it doesn't exist"""
        workspace = Path(self.config['agent']['workspace'])
        workspace.mkdir(parents=True, exist_ok=True)
        logging.info(f"Workspace ready: {workspace}")
    
    def get_tools_description(self):
        """Get descriptions of all available tools for the LLM"""
        tools = [
            {
                "name": "create_folder",
                "description": "Create a new folder/directory",
                "parameters": {
                    "path": "Path of the folder to create (relative to workspace)"
                }
            },
            {
                "name": "write_file",
                "description": "Create a NEW file with content. Use this when the file doesn't exist yet. For existing files, use edit_file instead.",
                "parameters": {
                    "path": "Path of the file (relative to workspace)",
                    "content": "Content to write to the file",
                    "force_overwrite": "Set to true to overwrite existing files (optional, default: false)"
                }
            },
            {
                "name": "read_file",
                "description": "Read the contents of a file",
                "parameters": {
                    "path": "Path of the file to read (relative to workspace)"
                }
            },
            {
                "name": "list_directory",
                "description": "List contents of a directory",
                "parameters": {
                    "path": "Path of directory to list (relative to workspace, defaults to workspace root)"
                }
            },
            {
                "name": "edit_file",
                "description": "Modify an EXISTING file (file must already exist). CANNOT create new files - use write_file for that.",
                "parameters": {
                    "path": "Path of the file to edit (relative to workspace)",
                    "mode": "append, prepend, replace, replace_once, insert_at_line, replace_lines, insert_after, insert_before",
                    "content": "Content to add/insert",
                    "search": "Text to find (ONLY for replace/replace_once modes)",
                    "replace": "Replacement text (ONLY for replace/replace_once modes)",
                    "line_number": "Line number (ONLY for insert_at_line mode, 1-based)",
                    "start_line": "Start line (ONLY for replace_lines mode, 1-based)",
                    "end_line": "End line (ONLY for replace_lines mode, 1-based, inclusive)",
                    "insert_after": "Pattern to insert after (ONLY for insert_after mode - DO NOT use search param)",
                    "insert_before": "Pattern to insert before (ONLY for insert_before mode - DO NOT use search param)"
                }
            },
            {
                "name": "smart_edit",
                "description": "RECOMMENDED: Edit code using natural language instructions. LLM automatically chooses best edit strategy. Use this for complex edits like 'Add error handling to divide function' or 'Refactor the login method to use async/await'",
                "parameters": {
                    "path": "Path of the file to edit (relative to workspace)",
                    "instruction": "Natural language description of what to change (e.g., 'Add a divide function with zero-division error handling')"
                }
            },
            {
                "name": "diff_edit",
                "description": "ADVANCED: For major refactoring or complex changes. Generates complete modified file with self-correction loop. Use for: refactoring entire functions, restructuring code, multiple coordinated changes. Has built-in linter feedback and will retry up to 3 times to fix issues.",
                "parameters": {
                    "path": "Path of the file to edit (relative to workspace)",
                    "instruction": "Detailed description of refactoring/changes needed (e.g., 'Refactor all functions to use type hints and add comprehensive docstrings')",
                    "max_iterations": "Maximum self-correction attempts (optional, default: 3)"
                }
            },
            {
                "name": "multi_file_edit",
                "description": "ATOMIC: Coordinate changes across multiple files with automatic rollback. ALL operations succeed or ALL rollback. Use for: renaming across files, coordinated refactoring, moving code between files. Safer than individual edits when changes must be synchronized.",
                "parameters": {
                    "operations": "Array of operations. Each operation is an object with 'file', 'action' (write_file/edit_file/smart_edit/diff_edit), and action-specific parameters. Example: [{\"file\": \"file1.py\", \"action\": \"edit_file\", \"mode\": \"replace\", \"search\": \"old\", \"replace\": \"new\"}, {\"file\": \"file2.py\", \"action\": \"smart_edit\", \"instruction\": \"Add import\"}]"
                }
            },
            {
                "name": "delete_file",
                "description": "Delete a file",
                "parameters": {
                    "path": "Path of the file to delete (relative to workspace)"
                }
            },
            {
                "name": "run_command",
                "description": "Execute a shell command (only whitelisted commands allowed)",
                "parameters": {
                    "command": "The command to execute"
                }
            },
            {
                "name": "get_system_info",
                "description": "Get system information (CPU, memory, disk usage)",
                "parameters": {}
            },
            {
                "name": "find_files",
                "description": "Find files matching a pattern (e.g., *.py, test_*)",
                "parameters": {
                    "pattern": "Glob pattern to match",
                    "path": "Directory to search in (default: workspace root)"
                }
            },
            {
                "name": "grep_content",
                "description": "Search for text pattern in files",
                "parameters": {
                    "pattern": "Text or regex pattern to search for",
                    "path": "Directory to search in",
                    "file_pattern": "File pattern (e.g., *.py)",
                    "case_sensitive": "Whether search is case sensitive (default: false)"
                }
            },
            {
                "name": "list_processes",
                "description": "List running processes",
                "parameters": {
                    "filter_name": "Optional: filter by process name"
                }
            },
            {
                "name": "get_process_info",
                "description": "Get detailed information about a specific process",
                "parameters": {
                    "pid": "Process ID"
                }
            },
            {
                "name": "check_process_running",
                "description": "Check if a process with given name is running",
                "parameters": {
                    "name": "Process name to check"
                }
            },
            {
                "name": "ping",
                "description": "Ping a host to check network connectivity",
                "parameters": {
                    "host": "Hostname or IP address",
                    "count": "Number of pings (default: 4)"
                }
            },
            {
                "name": "check_port",
                "description": "Check if a port is open on a host",
                "parameters": {
                    "host": "Hostname or IP address",
                    "port": "Port number"
                }
            },
            {
                "name": "http_request",
                "description": "Make an HTTP request",
                "parameters": {
                    "url": "URL to request",
                    "method": "HTTP method (GET, POST, etc.)",
                    "headers": "Optional headers dict",
                    "data": "Optional data for POST/PUT"
                }
            },
            {
                "name": "get_ip_info",
                "description": "Get network interface information",
                "parameters": {}
            },
            {
                "name": "parse_json",
                "description": "Parse JSON from file or string",
                "parameters": {
                    "file_path": "Path to JSON file",
                    "json_string": "JSON string (if not using file)"
                }
            },
            {
                "name": "write_json",
                "description": "Write data as JSON to a file",
                "parameters": {
                    "file_path": "Path to write JSON file",
                    "data": "Data to write",
                    "pretty": "Format with indentation (default: true)"
                }
            },
            {
                "name": "parse_csv",
                "description": "Parse CSV file",
                "parameters": {
                    "file_path": "Path to CSV file",
                    "delimiter": "Column delimiter (default: ,)",
                    "has_header": "Whether CSV has header row (default: true)"
                }
            },
            {
                "name": "write_csv",
                "description": "Write data as CSV to a file",
                "parameters": {
                    "file_path": "Path to write CSV file",
                    "data": "List of dicts or list of lists",
                    "headers": "Optional column headers"
                }
            },
            {
                "name": "store_memory",
                "description": "Store a fact in long-term memory",
                "parameters": {
                    "key": "Unique identifier for the memory",
                    "value": "The information to remember",
                    "category": "Category (default: general)"
                }
            },
            {
                "name": "retrieve_memory",
                "description": "Retrieve a stored memory",
                "parameters": {
                    "key": "Memory identifier",
                    "category": "Category (default: general)"
                }
            },
            {
                "name": "search_memory",
                "description": "Search memories by keyword",
                "parameters": {
                    "query": "Search query",
                    "category": "Optional category filter"
                }
            },
            {
                "name": "list_memories",
                "description": "List all stored memories",
                "parameters": {
                    "category": "Optional category filter"
                }
            },
            {
                "name": "index_codebase",
                "description": "Index the entire codebase for semantic search (run once or when files change)",
                "parameters": {}
            },
            {
                "name": "search_codebase",
                "description": "Semantic search across indexed codebase to find relevant code",
                "parameters": {
                    "query": "Search query (e.g., 'authentication logic', 'logging setup')",
                    "n_results": "Number of results to return (default: 5)"
                }
            },
            {
                "name": "rag_stats",
                "description": "Get RAG indexing statistics (how many chunks indexed)",
                "parameters": {}
            }
        ]
        return tools
    
    def execute_tool(self, tool_name, parameters):
        """Execute a tool by name with given parameters"""
        logging.info(f"Executing tool: {tool_name} with params: {parameters}")
        
        # Log tool start and track execution time
        self.log_manager.log_tool_start(tool_name, parameters)
        start_time = time.time()
        
        try:
            # File system tools
            if tool_name == "create_folder":
                result = self.fs_tools.create_folder(parameters.get("path"))
            elif tool_name == "write_file":
                # Smart file writing: check if file exists and prevent accidental overwrites
                file_path = parameters.get("path")
                file_content = parameters.get("content", "")
                force_overwrite = parameters.get("force_overwrite", False)

                # Convert string "false" to boolean
                if isinstance(force_overwrite, str):
                    force_overwrite = force_overwrite.lower() == "true"

                # Check if file already exists OR was created in this session
                full_path = self.fs_tools._get_safe_path(file_path)
                file_exists = full_path.exists() and full_path.is_file()

                # Also check session files with normalized paths
                normalized_path = str(full_path.relative_to(self.fs_tools.workspace)) if full_path.is_relative_to(self.fs_tools.workspace) else file_path
                created_this_session = normalized_path in self.session_files["created"] or file_path in self.session_files["created"]

                if (file_exists or created_this_session) and not force_overwrite:
                    # File exists - return error telling LLM to use edit_file
                    logging.warning(f"Blocked write_file on existing file: {file_path}")
                    context_msg = " (created earlier in this session)" if created_this_session else ""
                    result = {
                        "success": False,
                        "error": f"File '{file_path}' already exists{context_msg}. Use edit_file with mode 'append', 'prepend', or 'replace' to modify it, or use write_file with force_overwrite=true to intentionally overwrite.",
                        "suggestion": "Use edit_file instead",
                        "file_exists": True,
                        "created_this_session": created_this_session
                    }
                else:
                    result = self.fs_tools.write_file(file_path, file_content)
                    if result.get("success"):
                        self.session_files["created"].add(normalized_path)
                        # Auto-reindex the new file for RAG
                        self._reindex_file(file_path)
            elif tool_name == "read_file":
                result = self.fs_tools.read_file(parameters.get("path"))
                if result.get("success"):
                    self.session_files["read"].add(parameters.get("path"))
            elif tool_name == "list_directory":
                result = self.fs_tools.list_directory(parameters.get("path", "."))
            elif tool_name == "edit_file":
                file_path = parameters.get("path")
                mode = parameters.get("mode", "append")

                # Convert string numbers to int
                line_number = parameters.get("line_number")
                if line_number and isinstance(line_number, str):
                    line_number = int(line_number)

                start_line = parameters.get("start_line")
                if start_line and isinstance(start_line, str):
                    start_line = int(start_line)

                end_line = parameters.get("end_line")
                if end_line and isinstance(end_line, str):
                    end_line = int(end_line)

                # WORKAROUND: LLM often uses 'search' param instead of 'insert_after'/'insert_before'
                # Auto-correct this common mistake
                insert_after_param = parameters.get("insert_after", "")
                insert_before_param = parameters.get("insert_before", "")

                if mode == "insert_after" and not insert_after_param and parameters.get("search"):
                    logging.warning("LLM used 'search' instead of 'insert_after' - auto-correcting")
                    insert_after_param = parameters.get("search")

                if mode == "insert_before" and not insert_before_param and parameters.get("search"):
                    logging.warning("LLM used 'search' instead of 'insert_before' - auto-correcting")
                    insert_before_param = parameters.get("search")

                result = self.fs_tools.edit_file(
                    file_path,
                    mode=mode,
                    content=parameters.get("content", ""),
                    search=parameters.get("search", ""),
                    replace=parameters.get("replace", ""),
                    line_number=line_number,
                    start_line=start_line,
                    end_line=end_line,
                    insert_after=insert_after_param,
                    insert_before=insert_before_param
                )
                if result.get("success"):
                    self.session_files["modified"].add(file_path)
                    # Auto-reindex the modified file for RAG
                    self._reindex_file(file_path)
            elif tool_name == "smart_edit":
                file_path = parameters.get("path")
                instruction = parameters.get("instruction", "")

                if not instruction:
                    result = {"success": False, "error": "instruction parameter is required for smart_edit"}
                else:
                    # Provide LLM callback for smart_edit
                    def llm_callback(prompt):
                        """Call LLM with the given prompt and return response"""
                        try:
                            response = requests.post(
                                f"{self.api_url}/api/generate",
                                json={
                                    "model": self.config['ollama']['model'],
                                    "prompt": prompt,
                                    "stream": False,
                                    "options": {
                                        "temperature": 0.1  # Low temp for consistent JSON
                                    }
                                }
                            )
                            if response.status_code == 200:
                                return response.json().get("response", "")
                            else:
                                logging.error(f"LLM API error: {response.status_code}")
                                return ""
                        except Exception as e:
                            logging.error(f"Error calling LLM: {e}")
                            return ""

                    result = self.fs_tools.smart_edit(file_path, instruction, llm_callback)

                    if result.get("success"):
                        self.session_files["modified"].add(file_path)
                        # Auto-reindex the modified file for RAG
                        self._reindex_file(file_path)
            elif tool_name == "diff_edit":
                file_path = parameters.get("path")
                instruction = parameters.get("instruction", "")
                max_iterations = parameters.get("max_iterations", 3)

                if not instruction:
                    result = {"success": False, "error": "instruction parameter is required for diff_edit"}
                else:
                    # Provide LLM callback for diff_edit (same as smart_edit)
                    def llm_callback(prompt):
                        """Call LLM with the given prompt and return response"""
                        try:
                            response = requests.post(
                                f"{self.api_url}/api/generate",
                                json={
                                    "model": self.config['ollama']['model'],
                                    "prompt": prompt,
                                    "stream": False,
                                    "options": {
                                        "temperature": 0.1  # Low temp for consistent code generation
                                    }
                                }
                            )
                            if response.status_code == 200:
                                return response.json().get("response", "")
                            else:
                                logging.error(f"LLM API error: {response.status_code}")
                                return ""
                        except Exception as e:
                            logging.error(f"Error calling LLM: {e}")
                            return ""

                    result = self.fs_tools.diff_edit(file_path, instruction, llm_callback, max_iterations)

                    if result.get("success"):
                        self.session_files["modified"].add(file_path)
                        # Auto-reindex the modified file for RAG
                        self._reindex_file(file_path)
            elif tool_name == "multi_file_edit":
                operations = parameters.get("operations", [])

                if not operations:
                    result = {"success": False, "error": "operations parameter is required for multi_file_edit"}
                else:
                    # Provide LLM callback for operations that need it
                    def llm_callback(prompt):
                        """Call LLM with the given prompt and return response"""
                        try:
                            response = requests.post(
                                f"{self.api_url}/api/generate",
                                json={
                                    "model": self.config['ollama']['model'],
                                    "prompt": prompt,
                                    "stream": False,
                                    "options": {
                                        "temperature": 0.1
                                    }
                                }
                            )
                            if response.status_code == 200:
                                return response.json().get("response", "")
                            else:
                                logging.error(f"LLM API error: {response.status_code}")
                                return ""
                        except Exception as e:
                            logging.error(f"Error calling LLM: {e}")
                            return ""

                    result = self.fs_tools.multi_file_edit(operations, llm_callback)

                    if result.get("success"):
                        # Track all modified files
                        for file_path in result.get("files_modified", []):
                            self.session_files["modified"].add(file_path)
                            # Auto-reindex each modified file
                            self._reindex_file(file_path)
            elif tool_name == "delete_file":
                file_path = parameters.get("path")
                result = self.fs_tools.delete_file(file_path)
                if result.get("success"):
                    self.session_files["deleted"].add(file_path)
                    # Remove from created/modified if it was tracked
                    self.session_files["created"].discard(file_path)
                    self.session_files["modified"].discard(file_path)
                    # Remove from RAG index
                    self._delete_from_index(file_path)

            # Command tools
            elif tool_name == "run_command":
                result = self.cmd_tools.run_command(parameters.get("command"))

            # System tools
            elif tool_name == "get_system_info":
                result = self.sys_tools.get_system_info()

            # Search tools
            elif tool_name == "find_files" or tool_name == "list_files":
                result = self.search_tools.find_files(
                    parameters.get("pattern"),
                    parameters.get("path", ".")
                )
            elif tool_name == "grep_content":
                result = self.search_tools.grep_content(
                    parameters.get("pattern"),
                    parameters.get("path", "."),
                    parameters.get("file_pattern", "*"),
                    parameters.get("case_sensitive", True)
                )

            # Process tools
            elif tool_name == "list_processes":
                result = self.proc_tools.list_processes(
                    parameters.get("name_filter", None)
                )
            elif tool_name == "get_process_info":
                result = self.proc_tools.get_process_info(
                    parameters.get("pid")
                )

            # Network tools
            elif tool_name == "ping":
                result = self.net_tools.ping(parameters.get("host"))
            elif tool_name == "check_port":
                result = self.net_tools.check_port(
                    parameters.get("host"),
                    parameters.get("port")
                )
            elif tool_name == "http_request":
                result = self.net_tools.http_request(
                    parameters.get("url"),
                    parameters.get("method", "GET"),
                    parameters.get("headers", {}),
                    parameters.get("data", None)
                )

            # Data tools
            elif tool_name == "parse_json":
                result = self.data_tools.parse_json(
                    parameters.get("source"),
                    parameters.get("is_file", False)
                )
            elif tool_name == "write_json":
                result = self.data_tools.write_json(
                    parameters.get("data"),
                    parameters.get("path")
                )
            elif tool_name == "parse_csv":
                result = self.data_tools.parse_csv(
                    parameters.get("path")
                )
            elif tool_name == "write_csv":
                result = self.data_tools.write_csv(
                    parameters.get("data"),
                    parameters.get("path"),
                    parameters.get("headers", None)
                )

            # Memory tools
            elif tool_name == "store_memory":
                result = self.memory.store(
                    parameters.get("key"),
                    parameters.get("value"),
                    parameters.get("category", "general")
                )
            elif tool_name == "recall_memory" or tool_name == "retrieve_memory":
                result = self.memory.retrieve(
                    parameters.get("key"),
                    parameters.get("category", "general")
                )
            elif tool_name == "search_memory":
                result = self.memory.search(
                    parameters.get("query"),
                    parameters.get("category", None)
                )
            elif tool_name == "list_memories":
                result = self.memory.list_all(
                    parameters.get("category", None)
                )
            elif tool_name == "delete_memory":
                result = self.memory.delete(
                    parameters.get("category"),
                    parameters.get("key")
                )

            # RAG tools
            elif tool_name == "index_codebase":
                result = self.rag.index_codebase() if self.rag else {"success": False, "error": "RAG not available"}
            elif tool_name == "search_codebase":
                if self.rag:
                    n_results = parameters.get("n_results", 5)
                    # Convert to int if it's a string
                    if isinstance(n_results, str):
                        n_results = int(n_results)
                    result = self.rag.search(
                        parameters.get("query"),
                        n_results
                    )
                else:
                    result = {"success": False, "error": "RAG not available"}
            elif tool_name == "rag_stats":
                result = self.rag.get_stats() if self.rag else {"success": False, "error": "RAG not available"}

            else:
                result = {"success": False, "error": f"Unknown tool: {tool_name}"}

            # Log tool completion
            execution_time = time.time() - start_time
            logging.info(f"Tool {tool_name} completed in {execution_time:.2f}s")

            return result
        except Exception as e:
            logging.error(f"Error executing tool {tool_name}: {e}")
            execution_time = time.time() - start_time
            error_result = {"success": False, "error": str(e)}
            logging.error(f"Tool {tool_name} failed after {execution_time:.2f}s")
            return error_result

    def _reindex_file(self, file_path):
        """Re-index a file for RAG after creation/modification"""
        if self.rag:
            try:
                from pathlib import Path
                # Convert to absolute Path object
                full_path = self.fs_tools._get_safe_path(file_path)
                self.rag.index_file(full_path)
            except Exception as e:
                logging.warning(f"Failed to index file {file_path}: {e}")

    def _delete_from_index(self, file_path):
        """Remove a file from RAG index after deletion"""
        if self.rag:
            try:
                self.rag.delete_file_chunks(file_path)
            except Exception as e:
                logging.warning(f"Failed to delete file from index {file_path}: {e}")

    def _load_agent_rules(self):
        """Load project-specific rules from .agentrules file"""
        try:
            rules_path = Path(".agentrules")
            if rules_path.exists():
                with open(rules_path, 'r') as f:
                    return f.read()
        except Exception as e:
            logging.debug(f"No .agentrules file found or error loading: {e}")
        return None

    def chat(self, user_message):
        """Send a message to the agent and get response with tool execution"""
        try:
            # Add to session history
            self.history.add_message("user", user_message)

            # ========== MULTI-MODEL ROUTING ==========
            # Analyze task to determine best execution strategy
            task_analysis = self.task_analyzer.analyze(user_message)
            logging.info(f"Task analysis: {task_analysis}")

            # Check if we should use two-phase execution
            use_two_phase = self.model_router.should_use_two_phase(task_analysis)

            if use_two_phase:
                logging.info("Using TWO-PHASE execution (Plan → Execute)")
                return self._execute_two_phase(user_message, task_analysis)
            else:
                logging.info("Using SINGLE-PHASE execution")
                return self._execute_single_phase(user_message, task_analysis)

        except requests.exceptions.ConnectionError:
            return "Error: Cannot connect to Ollama. Make sure Ollama is running with 'ollama serve'"
        except Exception as e:
            logging.error(f"Error in chat: {e}", exc_info=True)
            return f"Error: {str(e)}"

    def _execute_single_phase(self, user_message, task_analysis):
        """Execute task using a single model"""
        try:
            # Select best model for this task
            selected_model = self.model_router.select_model(task_analysis)
            logging.info(f"Selected model: {selected_model}")

            # Build session context
            session_context = self._build_session_context()

            # Load project rules if available
            agent_rules = self._load_agent_rules()
            rules_section = f"\nPROJECT-SPECIFIC RULES:\n{agent_rules}\n" if agent_rules else ""

            # Check if using a reasoning model and adjust prompt accordingly
            is_reasoning_model = self._is_reasoning_model(selected_model)

            # Build reasoning-specific instructions
            if is_reasoning_model:
                reasoning_instructions = """
⚡ REASONING MODEL - IMPORTANT ⚡
You can think step-by-step using <think>...</think> tags, but you MUST also output tool calls.

Response structure:
1. <think>Your reasoning here</think> (optional)
2. TOOL: tool_name | PARAMS: {{"param": "value"}} (REQUIRED)

Never output ONLY thinking - always follow with actual TOOL calls.
"""
            else:
                reasoning_instructions = ""

            # Build prompt with system context and tool format instructions
            system_prompt = f"""You are {self.config['agent']['name']}, an AI assistant with access to various tools.
You can execute commands, manage files, search information, and more.
Your workspace is: {self.config['agent']['workspace']}

{session_context}
{rules_section}
{reasoning_instructions}
Available tools:
{self.get_tools_description()}

TOOL USAGE FORMAT:
To use a tool, respond EXACTLY in this format:
TOOL: tool_name | PARAMS: {{"param1": "value1", "param2": "value2"}}

CRITICAL JSON FORMATTING RULES:
- Parameters MUST be valid JSON
- For multi-line strings, use \\n for newlines (e.g., "line1\\nline2")
- NEVER use triple quotes in JSON - they are invalid
- Always escape backslashes and quotes inside strings
- Example: {{"content": "def add(a, b):\\n    return a + b\\n"}}

You can call multiple tools in one response. After tool execution, you'll see the results.

FILE WRITING RULES (CRITICAL):
- Use write_file ONLY for creating NEW files that don't exist yet
- NEVER use write_file to modify existing files - it will OVERWRITE them completely
- Use edit_file to modify/add content to existing files with these modes:

  SIMPLE MODES:
  - mode="append" - add content to end of file
  - mode="prepend" - add content to beginning of file
  - mode="replace" - find and replace ALL occurrences (needs search + replace params)
  - mode="replace_once" - replace only FIRST occurrence (needs search + replace params)

  ADVANCED MODES (for precise code editing):
  - mode="insert_at_line" - insert content at specific line (needs line_number param)
  - mode="replace_lines" - replace line range (needs start_line + end_line params)
  - mode="insert_after" - insert after line matching pattern (needs insert_after param)
  - mode="insert_before" - insert before line matching pattern (needs insert_before param)

  EXAMPLES:
  - Add function to end:
    TOOL: edit_file | PARAMS: {{"path": "main.py", "mode": "append", "content": "def new_func():\\n    pass\\n"}}

  - Insert at line 5:
    TOOL: edit_file | PARAMS: {{"path": "main.py", "mode": "insert_at_line", "line_number": 5, "content": "import os\\n"}}

  - Replace lines 10-15:
    TOOL: edit_file | PARAMS: {{"path": "main.py", "mode": "replace_lines", "start_line": 10, "end_line": 15, "content": "new code\\n"}}

  - Insert after pattern (IMPORTANT - use SHORT pattern that appears in a SINGLE line):
    TOOL: edit_file | PARAMS: {{"path": "main.py", "mode": "insert_after", "insert_after": "import sys", "content": "import os\\n"}}
    TOOL: edit_file | PARAMS: {{"path": "calc.py", "mode": "insert_after", "insert_after": "def multiply", "content": "\\ndef divide(a, b):\\n    return a / b\\n"}}

  - Insert before pattern (IMPORTANT - use SHORT pattern that appears in a SINGLE line):
    TOOL: edit_file | PARAMS: {{"path": "main.py", "mode": "insert_before", "insert_before": "def main", "content": "# Main function\\n"}}

  - Find and replace text:
    TOOL: edit_file | PARAMS: {{"path": "main.py", "mode": "replace", "search": "old_name", "replace": "new_name"}}

- Use RELATIVE paths (e.g., "my_app/src/main.py" NOT "c:\\Users\\...")

CODEBASE UNDERSTANDING (RAG):
- Use search_codebase to find relevant code semantically
- Run index_codebase once to index the workspace
- RAG search helps you understand existing code before making changes
- Check rag_stats to see if codebase is indexed

Respond helpfully to user requests. Execute tools when needed."""

            # Call Ollama API with selected model
            response = requests.post(
                f"{self.api_url}/api/generate",
                json={
                    "model": selected_model,
                    "prompt": f"{system_prompt}\n\nUser: {user_message}\n\nAssistant:",
                    "stream": False,
                    "options": {
                        "temperature": self.config['ollama'].get('temperature', 0.7),
                        "num_ctx": self.config['ollama'].get('num_ctx', 8192),
                        "num_predict": self.config['ollama'].get('num_predict', 2048)
                    }
                },
                timeout=self.config['ollama'].get('timeout', 120)
            )

            if response.status_code == 200:
                result = response.json()
                assistant_message = result.get('response', '')

                # Log thinking if present (for reasoning models)
                if '<think>' in assistant_message.lower():
                    import re
                    thinks = re.findall(r'<think>(.*?)</think>', assistant_message, re.DOTALL | re.IGNORECASE)
                    for i, thought in enumerate(thinks, 1):
                        # Log first 300 chars of each thinking block
                        thought_preview = thought.strip()[:300]
                        if len(thought.strip()) > 300:
                            thought_preview += "..."
                        logging.info(f"[REASONING BLOCK {i}]: {thought_preview}")

                # Parse and execute any tool calls in the response
                tool_calls = self.parse_tool_calls(assistant_message)

                if tool_calls:
                    # Execute all tools and collect results
                    tool_results = []
                    for tool_call in tool_calls:
                        tool_name = tool_call.get('tool')
                        params = tool_call.get('params', {})

                        logging.info(f"Executing tool: {tool_name} with params: {params}")
                        result = self.execute_tool(tool_name, params)
                        tool_results.append({
                            'tool': tool_name,
                            'result': result
                        })

                    # Build response with tool results
                    response_parts = []

                    # Add any text before the tool calls
                    first_tool_pos = assistant_message.find('TOOL:')
                    if first_tool_pos > 0:
                        response_parts.append(assistant_message[:first_tool_pos].strip())

                    # Add tool execution results
                    for tr in tool_results:
                        response_parts.append(f"\n[Executed: {tr['tool']}]")
                        if tr['result'].get('success'):
                            if 'message' in tr['result']:
                                response_parts.append(tr['result']['message'])
                            elif 'results' in tr['result']:  # For search results
                                response_parts.append(f"Found {tr['result'].get('count', 0)} results")
                            elif 'files_indexed' in tr['result']:  # For indexing
                                response_parts.append(f"Indexed {tr['result']['files_indexed']} files ({tr['result']['total_chunks']} chunks)")
                            elif 'total_chunks' in tr['result']:  # For stats
                                response_parts.append(f"RAG database contains {tr['result']['total_chunks']} chunks")
                            else:
                                response_parts.append(str(tr['result']))
                        else:
                            response_parts.append(f"Error: {tr['result'].get('error', 'Unknown error')}")

                    final_response = '\n'.join(response_parts)
                else:
                    # No tool calls found
                    # Check if this is a reasoning model stuck in thinking
                    if self._is_reasoning_model() and '<think>' in assistant_message and 'TOOL:' not in assistant_message.upper():
                        logging.warning("Reasoning model output thinking but no tool calls - attempting recovery")

                        # Try ONE more time with a direct prompt
                        followup_prompt = f"""Request: {user_message}

Output the tool call needed to complete this request.
Format: TOOL: tool_name | PARAMS: {{"param": "value"}}
Output only the tool call:"""

                        try:
                            response2 = requests.post(
                                f"{self.api_url}/api/generate",
                                json={
                                    "model": self.config['ollama']['model'],
                                    "prompt": followup_prompt,
                                    "stream": False,
                                    "options": {
                                        "temperature": 0.1,
                                        "num_predict": 512
                                    }
                                },
                                timeout=30
                            )

                            if response2.status_code == 200:
                                recovery_response = response2.json().get('response', '')
                                logging.info(f"Recovery attempt response: {recovery_response[:200]}")

                                # Try to parse tool calls from recovery response
                                recovery_tools = self._parse_standard_format(recovery_response)

                                if recovery_tools:
                                    logging.info(f"Recovery successful - found {len(recovery_tools)} tool calls")
                                    # Execute the recovered tool calls
                                    tool_results = []
                                    for tool_call in recovery_tools:
                                        tool_name = tool_call.get('tool')
                                        params = tool_call.get('params', {})
                                        logging.info(f"Executing recovered tool: {tool_name}")
                                        result = self.execute_tool(tool_name, params)
                                        tool_results.append({'tool': tool_name, 'result': result})

                                    # Build response
                                    response_parts = ["[Recovered tool execution after reasoning]"]
                                    for tr in tool_results:
                                        response_parts.append(f"\n[Executed: {tr['tool']}]")
                                        if tr['result'].get('success'):
                                            response_parts.append(tr['result'].get('message', str(tr['result'])))
                                        else:
                                            response_parts.append(f"Error: {tr['result'].get('error')}")

                                    final_response = '\n'.join(response_parts)
                                else:
                                    # Recovery failed - return thinking summary
                                    logging.warning("Recovery failed - no valid tool calls generated")
                                    final_response = f"I analyzed the task but couldn't generate valid tool calls.\n\nReasoning summary: {assistant_message[:500]}"
                            else:
                                final_response = assistant_message
                        except Exception as e:
                            logging.error(f"Error in recovery attempt: {e}")
                            final_response = assistant_message
                    else:
                        # Not a reasoning model or no thinking tags - return as-is
                        final_response = assistant_message

                # Add to session history
                self.history.add_message("assistant", final_response)

                return final_response
            else:
                error_msg = f"Ollama API error: {response.status_code} - {response.text}"
                logging.error(error_msg)
                return f"Error: {error_msg}"

        except Exception as e:
            logging.error(f"Error in single-phase execution: {e}", exc_info=True)
            return f"Error: {str(e)}"

    def _execute_two_phase(self, user_message, task_analysis):
        """Execute task using two-phase approach: Planning → Execution"""
        planning_model = self.model_router.get_planning_model()
        execution_model = self.model_router.get_execution_model()

        if not planning_model or not execution_model:
            logging.warning("Two-phase execution requires both planning and execution models configured")
            return self._execute_single_phase(user_message, task_analysis)

        # Execute with two-phase approach
        result = self.two_phase_executor.execute(
            user_message,
            planning_model,
            execution_model,
            parse_callback=self.parse_tool_calls,
            execute_callback=self.execute_tool
        )

        if result['success']:
            # Build response message
            response_parts = [
                "✨ TWO-PHASE EXECUTION COMPLETE ✨",
                "",
                f"📋 Planning Model: {planning_model}",
                f"⚙️  Execution Model: {execution_model}",
                "",
                result['execution_result']
            ]

            final_response = '\n'.join(response_parts)

            # Add to session history
            self.history.add_message("assistant", final_response)

            return final_response
        else:
            error_msg = f"Two-phase execution failed: {result.get('error', 'Unknown error')}"
            logging.error(error_msg)

            # Add to session history
            self.history.add_message("assistant", error_msg)

            return error_msg

    def parse_tool_calls(self, llm_response):
        """
        Parse tool calls from LLM response.
        Supports:
        1. Direct TOOL: format (qwen2.5-coder, llama, etc.)
        2. Reasoning format with <think> tags (OpenThinker, DeepSeek-R1)
        """
        import re

        # Step 1: Strip thinking tags to get action content
        cleaned_response = self._strip_thinking_tags(llm_response)

        # Step 2: Try standard TOOL: format first
        tool_calls = self._parse_standard_format(cleaned_response)

        # Step 3: If no tools found and response has thinking, try to extract intent
        if not tool_calls and '<think>' in llm_response:
            logging.info("No tool calls found after thinking - attempting to extract intent")
            tool_calls = self._extract_tools_from_reasoning(llm_response)

        return tool_calls

    def _strip_thinking_tags(self, response):
        """Remove <think>...</think> blocks to get action content"""
        import re
        # Remove all thinking blocks
        cleaned = re.sub(r'<think>.*?</think>', '', response, flags=re.DOTALL | re.IGNORECASE)
        return cleaned.strip()

    def _parse_standard_format(self, text):
        """Parse TOOL: name | PARAMS: {...} format"""
        tool_calls = []
        import re
        import json

        # Find all TOOL: positions
        tool_positions = [m.start() for m in re.finditer(r'TOOL:\s*(\w+)', text, re.IGNORECASE)]

        for i, pos in enumerate(tool_positions):
            # Extract tool name
            tool_match = re.match(r'TOOL:\s*(\w+)\s*\|\s*PARAMS:\s*', text[pos:], re.IGNORECASE)
            if not tool_match:
                continue

            tool_name = tool_match.group(1)
            json_start = pos + tool_match.end()

            # Find matching closing brace using brace counting
            brace_count = 0
            in_string = False
            escape_next = False
            json_end = -1

            for j in range(json_start, len(text)):
                char = text[j]

                if escape_next:
                    escape_next = False
                    continue

                if char == '\\':
                    escape_next = True
                    continue

                if char == '"' and not escape_next:
                    in_string = not in_string

                if not in_string:
                    if char == '{':
                        brace_count += 1
                    elif char == '}':
                        brace_count -= 1
                        if brace_count == 0:
                            json_end = j + 1
                            break

            if json_end == -1:
                logging.error(f"Could not find closing brace for tool {tool_name}")
                continue

            params_str = text[json_start:json_end]

            try:
                # Preprocess to handle common JSON issues
                # 1. Fix Windows backslashes in paths (e.g., code\file.py -> code\\file.py)
                # But only if not already escaped
                import re
                # Replace single backslashes that aren't already escaped
                params_str_fixed = re.sub(r'(?<!\\)\\(?!["\\/bfnrt])', r'\\\\', params_str)

                # 2. Try to handle triple-quoted strings (convert """ to ")
                # This is a heuristic - may not work for all cases
                params_str_fixed = params_str_fixed.replace('"""', '"')

                params = json.loads(params_str_fixed)
                tool_calls.append({
                    'tool': tool_name,
                    'params': params
                })
            except json.JSONDecodeError as e:
                logging.error(f"Failed to parse tool params for {tool_name}: {params_str[:100]}, error: {e}")
                # Try one more time without preprocessing
                try:
                    params = json.loads(params_str)
                    tool_calls.append({
                        'tool': tool_name,
                        'params': params
                    })
                except:
                    continue

        return tool_calls

    def _extract_tools_from_reasoning(self, response):
        """
        For reasoning models that don't follow TOOL: format,
        extract intent and generate tool calls.

        Approach:
        1. Check if we have thinking but no actions
        2. Use a lightweight LLM call to convert reasoning -> tool calls
        3. Parse the generated tool calls
        """
        import re

        # Extract all thinking blocks
        think_pattern = r'<think>(.*?)</think>'
        thinks = re.findall(think_pattern, response, re.DOTALL | re.IGNORECASE)

        if not thinks:
            return []

        # Use the last thinking block (final decision)
        final_thought = thinks[-1].strip()

        logging.info(f"Attempting to convert reasoning to tool calls. Thought length: {len(final_thought)} chars")

        # Make a focused LLM call to convert reasoning -> actions
        conversion_prompt = f"""Task reasoning:
{final_thought}

Based on this reasoning, output the required tool calls in this EXACT format:
TOOL: tool_name | PARAMS: {{"param1": "value1"}}

Output ONLY tool calls, nothing else:"""

        # Call LLM with low temperature for consistent output
        tool_response = self._call_llm_simple(conversion_prompt, temperature=0.1)

        if tool_response:
            logging.info(f"Conversion response: {tool_response[:200]}...")
            # Parse the generated tool calls
            return self._parse_standard_format(tool_response)

        return []

    def _call_llm_simple(self, prompt, temperature=0.1):
        """Simple LLM call without tool execution (for meta-prompting)"""
        try:
            response = requests.post(
                f"{self.api_url}/api/generate",
                json={
                    "model": self.config['ollama']['model'],
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": temperature,
                        "num_predict": 512
                    }
                },
                timeout=30
            )

            if response.status_code == 200:
                return response.json().get('response', '')
            else:
                logging.error(f"LLM simple call failed: {response.status_code}")
                return ''
        except Exception as e:
            logging.error(f"Error in simple LLM call: {e}")
            return ''

    def _is_reasoning_model(self, model_name=None):
        """Detect if a model is a reasoning model based on name"""
        if model_name is None:
            model_name = self.config['ollama']['model']

        reasoning_models = [
            'openthinker', 'deepseek-r1', 'qwen-r1', 'qwq',
            'thinking', 'reasoning', 'r1', '-r-'
        ]
        return any(rm in model_name.lower() for rm in reasoning_models)

    def _build_session_context(self):
        """Build context about files created/modified in this session"""
        parts = []
        if self.session_files["created"]:
            files = ", ".join(sorted(self.session_files["created"]))
            parts.append(f"Files you created this session: {files}")
        if self.session_files["modified"]:
            files = ", ".join(sorted(self.session_files["modified"]))
            parts.append(f"Files you modified this session: {files}")

        if parts:
            return "SESSION FILE TRACKING:\n" + "\n".join(parts) + "\n\nIMPORTANT: If you need to modify a file you created/modified earlier in this session, use edit_file NOT write_file."
        return ""

    def chat_with_verification(self, user_message):
        """
        Enhanced chat with gather → execute → verify → repeat loop
        (Cursor/Claude Code pattern)
        """
        try:
            # Add to history
            self.history.add_message("user", user_message)

            logging.info("=" * 80)
            logging.info("SMART ROUTING WORKFLOW (Phase 2): Minimize swaps")
            logging.info("=" * 80)

            # PHASE 0: CLASSIFY TASK (Phase 2 smart routing)
            logging.info("PHASE 0: Classifying task...")
            classification = self.task_classifier.classify(user_message)
            logging.info(f"Classification: {classification['tier']} - {classification['reasoning']}")
            logging.info(f"Route: {classification['route_strategy']} - Swap overhead: {classification['estimated_swap_overhead']}s")

            # PHASE 1: GATHER CONTEXT (minimal, only if needed)
            logging.info("PHASE 1: Gathering context...")
            context = self.context_gatherer.gather_for_task(user_message)
            context_formatted = self.context_gatherer.format_for_llm(context)
            logging.info(f"Context gathered: {context['summary']}")

            # PHASE 2: PLAN & EXECUTE
            logging.info("PHASE 2: Planning and execution...")

            # Execute with appropriate strategy based on classification
            use_two_phase = self.model_router.should_use_two_phase(classification)

            if use_two_phase:
                logging.info("Using TWO-PHASE execution (openthinker -> qwen)")
                # Plan with OpenThinker, execute with Qwen
                execution_result = self._execute_two_phase_with_context(
                    user_message, context_formatted, classification
                )
            else:
                logging.info("Using SINGLE-PHASE execution (qwen only - 0s swap)")
                # Use qwen only (no swap needed for simple/standard tasks)
                selected_model = self.model_router.select_model_from_classification(classification)
                self.model_manager.ensure_in_vram(selected_model)
                execution_result = self._execute_single_phase_with_context(
                    user_message, context_formatted, classification
                )

            # PHASE 3: VERIFY WORK
            logging.info("PHASE 3: Verifying results...")

            # Extract tool calls that were executed
            tool_calls = execution_result.get('tool_calls', [])

            if tool_calls:
                # Verify each action
                verification_results = []
                all_verified = True

                for tool_call in tool_calls:
                    tool_name = tool_call.get('tool')
                    params = tool_call.get('params', {})
                    result = tool_call.get('result', {})

                    verification = self.verifier.verify_action(tool_name, params, result)
                    verification_results.append({
                        'tool': tool_name,
                        'verification': verification
                    })

                    if not verification['verified']:
                        all_verified = False
                        logging.warning(f"Verification failed for {tool_name}: {verification['issues']}")

                # PHASE 4: RETRY IF FAILED
                if not all_verified:
                    logging.info("PHASE 4: Verification failed, attempting retry...")
                    retry_result = self._retry_failed_actions(
                        user_message, verification_results, max_retries=2
                    )
                    return retry_result
                else:
                    logging.info("✓ All actions verified successfully!")

            logging.info("=" * 80)
            return execution_result.get('response', 'Task completed')

        except Exception as e:
            logging.error(f"Error in enhanced chat: {e}", exc_info=True)
            return f"Error: {str(e)}"

    def _execute_single_phase_with_context(self, user_message, context, task_analysis):
        """Execute single-phase with context included - returns dict format for verification"""
        # Execute and get response string
        response_string = self._execute_single_phase(user_message, task_analysis)

        # Return in dict format expected by chat_with_verification
        return {
            'response': response_string,
            'tool_calls': [],  # Single phase doesn't track individual tool calls in structured way
            'success': True
        }

    def _execute_two_phase_with_context(self, user_message, context, task_analysis):
        """Execute two-phase with context included - returns dict format for verification"""
        # Execute and get result
        result = self._execute_two_phase(user_message, task_analysis)

        # Two-phase already returns dict format, just ensure it has required fields
        if isinstance(result, dict):
            if 'tool_calls' not in result:
                result['tool_calls'] = []
            return result
        else:
            # If it returned a string for some reason, wrap it
            return {
                'response': str(result),
                'tool_calls': [],
                'success': True
            }

    def _retry_failed_actions(self, user_message, verification_results, max_retries=2):
        """
        Retry failed actions with smarter model (Cursor's reapply pattern)
        """
        logging.info(f"Retrying with smarter model (max {max_retries} attempts)...")

        # Use OpenThinker to reason about failures
        self.model_manager.smart_load_for_phase('debugging')

        failed_actions = [
            vr for vr in verification_results if not vr['verification']['verified']
        ]

        retry_prompt = f"""Original request: {user_message}

Some actions failed verification:
"""
        for failed in failed_actions:
            issues = failed['verification']['issues']
            suggestion = failed['verification']['suggestion']
            retry_prompt += f"\n- {failed['tool']}: {', '.join(issues)}"
            retry_prompt += f"\n  Suggestion: {suggestion}"

        retry_prompt += "\n\nAnalyze the failures and create a fix plan."

        # Use OpenThinker to create fix plan
        fix_plan_response = self.model_manager.call_model(
            self.model_manager.get_model_for_role('context_master'),
            retry_prompt
        )

        if not fix_plan_response.get('success'):
            return {
                'success': False,
                'response': f"Retry failed: Could not create fix plan",
                'tool_calls': []
            }

        fix_plan = fix_plan_response.get('response', '')
        logging.info(f"Fix plan created: {fix_plan[:200]}...")

        # Execute fix with Qwen
        self.model_manager.smart_load_for_phase('execution')

        # For now, return the fix plan
        # TODO: Actually execute the fix plan
        return {
            'success': True,
            'response': f"Verification failed. Fix plan created:\n{fix_plan}",
            'tool_calls': []
        }


def main():
    """Main entry point for the agent"""
    import sys

    # Fix Windows console encoding for special characters
    if sys.platform == 'win32':
        try:
            sys.stdout.reconfigure(encoding='utf-8')
            sys.stderr.reconfigure(encoding='utf-8')
        except AttributeError:
            pass  # Python < 3.7

    # Create agent
    agent = Agent()

    print(f"\n{'='*60}")
    print(f"  {agent.config['agent']['name']} - Ready")
    print(f"{'='*60}")
    print(f"Workspace: {agent.config['agent']['workspace']}")
    print(f"Ollama: {agent.api_url}")
    print(f"Model: {agent.config['ollama']['model']}")
    if not RAG_AVAILABLE:
        print("⚠ RAG features disabled (chromadb/tiktoken not installed)")
    print(f"{'='*60}\n")

    # Interactive loop
    print("Enter your requests (type 'quit' or 'exit' to stop):\n")

    while True:
        try:
            user_input = input("You: ").strip()

            if user_input.lower() in ['quit', 'exit', 'q']:
                print("\nShutting down agent...")
                break

            if not user_input:
                continue

            # Send request to agent
            print(f"\nAgent: Thinking...")
            response = agent.chat(user_input)
            print(f"\n{response}\n")

        except KeyboardInterrupt:
            print("\n\nInterrupted by user. Shutting down...")
            break
        except Exception as e:
            print(f"\nError: {e}\n")
            logging.error(f"Error in main loop: {e}", exc_info=True)


if __name__ == "__main__":
    main()