"""
Tool Router - Handles tool execution and descriptions
Extracted from agent.py to reduce file size
"""

from typing import Dict, Any, Optional
from pathlib import Path
import logging


class ToolRouter:
    """Routes and executes tool calls"""

    def __init__(self, agent):
        """
        Initialize ToolRouter.

        Args:
            agent: Reference to parent Agent instance
        """
        self.agent = agent

    def get_tools_description(self) -> str:
        """
        Get description of all available tools.

        Returns:
            Formatted string describing all available tools
        """
        return """
AVAILABLE TOOLS (call with format: TOOL: tool_name | PARAMS: {json_params}):

=== FILE SYSTEM TOOLS ===
• write_file | {"path": "relative/path.txt", "content": "file contents"}
  - Create or overwrite a file with content
  - Path is relative to workspace

• edit_file | {"path": "relative/path.txt", "mode": "append|prepend|replace|...", ...}
  - Edit existing file with 8 modes:
    * append: Add content to end
    * prepend: Add content to beginning
    * replace: Replace all occurrences (params: search, replace)
    * replace_once: Replace first occurrence (params: search, replace)
    * insert_at_line: Insert at line number (params: line_number, content)
    * replace_lines: Replace line range (params: start_line, end_line, content)
    * insert_after: Insert after pattern (params: insert_after, content)
    * insert_before: Insert before pattern (params: insert_before, content)

• read_file | {"path": "relative/path.txt"}
  - Read file contents

• delete_file | {"path": "relative/path.txt"}
  - Delete a file

• create_folder | {"path": "relative/folder"}
  - Create directory (creates parent dirs if needed)

• list_directory | {"path": "relative/folder"}
  - List files and folders in directory

=== SEARCH TOOLS ===
• find_files | {"pattern": "*.py", "path": "optional/start/path"}
  - Find files matching glob pattern
  - Examples: "*.py", "src/**/*.js", "test_*.py"

• search_content | {"query": "search text", "file_pattern": "*.py"}
  - Search file contents using grep
  - Returns matching lines with file paths

=== COMMAND EXECUTION ===
• run_command | {"command": "ls -la"}
  - Execute whitelisted shell commands
  - Allowed: ls, pwd, whoami, date, echo, cat, grep, find, df, free, uptime, ps

=== SYSTEM INFO ===
• get_system_info | {}
  - Get CPU, memory, disk usage
  - Cross-platform (Windows/Linux/macOS)

=== PROCESS MANAGEMENT ===
• list_processes | {"filter": "optional_name_filter"}
  - List running processes

• process_info | {"pid": 1234}
  - Get detailed process information

=== NETWORK TOOLS ===
• ping | {"host": "google.com", "count": 4}
  - Ping a host

• check_port | {"host": "localhost", "port": 8080}
  - Check if port is open

• http_request | {"url": "https://api.example.com", "method": "GET"}
  - Make HTTP request

=== DATA TOOLS ===
• parse_json | {"data": "json_string"}
  - Parse JSON data

• parse_csv | {"data": "csv_string"}
  - Parse CSV data

• write_json | {"path": "data.json", "data": {...}}
  - Write JSON to file

• write_csv | {"path": "data.csv", "data": [...]}
  - Write CSV to file

=== MEMORY & HISTORY ===
• remember | {"key": "fact_name", "value": "information"}
  - Store information in long-term memory

• recall | {"key": "fact_name"}
  - Retrieve stored information

• get_history | {"limit": 10}
  - Get recent conversation history
"""

    def execute_tool(self, tool_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a tool by name.

        Args:
            tool_name: Name of tool to execute
            parameters: Tool parameters

        Returns:
            Tool execution result dict
        """
        try:
            # File system tools
            if tool_name == "write_file":
                return self.agent.fs_tools.write_file(parameters.get('path'), parameters.get('content'))

            elif tool_name == "read_file":
                return self.agent.fs_tools.read_file(parameters.get('path'))

            elif tool_name == "edit_file":
                return self.agent.fs_tools.edit_file(
                    path=parameters.get('path'),
                    mode=parameters.get('mode', 'append'),
                    content=parameters.get('content', ''),
                    search=parameters.get('search'),
                    replace=parameters.get('replace'),
                    line_number=parameters.get('line_number'),
                    start_line=parameters.get('start_line'),
                    end_line=parameters.get('end_line'),
                    insert_after=parameters.get('insert_after'),
                    insert_before=parameters.get('insert_before')
                )

            elif tool_name == "delete_file":
                return self.agent.fs_tools.delete_file(parameters.get('path'))

            elif tool_name == "create_folder":
                return self.agent.fs_tools.create_folder(parameters.get('path'))

            elif tool_name == "list_directory":
                return self.agent.fs_tools.list_directory(parameters.get('path', '.'))

            # Search tools
            elif tool_name == "find_files":
                return self.agent.search_tools.find_files(
                    parameters.get('pattern'),
                    parameters.get('path')
                )

            elif tool_name == "search_content":
                return self.agent.search_tools.search_content(
                    parameters.get('query'),
                    parameters.get('file_pattern')
                )

            # Command execution
            elif tool_name == "run_command":
                return self.agent.cmd_tools.execute(parameters.get('command'))

            # System info
            elif tool_name == "get_system_info":
                return self.agent.sys_tools.get_system_info()

            # Process tools
            elif tool_name == "list_processes":
                return self.agent.process_tools.list_processes(parameters.get('filter'))

            elif tool_name == "process_info":
                return self.agent.process_tools.get_process_info(parameters.get('pid'))

            # Network tools
            elif tool_name == "ping":
                return self.agent.network_tools.ping(
                    parameters.get('host'),
                    parameters.get('count', 4)
                )

            elif tool_name == "check_port":
                return self.agent.network_tools.check_port(
                    parameters.get('host'),
                    parameters.get('port')
                )

            elif tool_name == "http_request":
                return self.agent.network_tools.http_request(
                    parameters.get('url'),
                    parameters.get('method', 'GET'),
                    parameters.get('headers'),
                    parameters.get('data')
                )

            # Data tools
            elif tool_name == "parse_json":
                return self.agent.data_tools.parse_json(parameters.get('data'))

            elif tool_name == "parse_csv":
                return self.agent.data_tools.parse_csv(parameters.get('data'))

            elif tool_name == "write_json":
                return self.agent.data_tools.write_json(
                    parameters.get('path'),
                    parameters.get('data')
                )

            elif tool_name == "write_csv":
                return self.agent.data_tools.write_csv(
                    parameters.get('path'),
                    parameters.get('data')
                )

            # Memory tools
            elif tool_name == "remember":
                return self.agent.memory.store_fact(
                    parameters.get('key'),
                    parameters.get('value')
                )

            elif tool_name == "recall":
                return self.agent.memory.retrieve_fact(parameters.get('key'))

            # History tools
            elif tool_name == "get_history":
                return self.agent.history.get_recent_messages(parameters.get('limit', 10))

            else:
                return {
                    "success": False,
                    "error": f"Unknown tool: {tool_name}"
                }

        except Exception as e:
            logging.error(f"Error executing tool {tool_name}: {e}")
            return {
                "success": False,
                "error": str(e),
                "tool": tool_name
            }

    def handle_file_tracking(self, tool_name: str, parameters: Dict[str, Any],
                           result: Dict[str, Any]) -> None:
        """
        Track file changes for RAG indexing.

        Args:
            tool_name: Tool that was executed
            parameters: Tool parameters
            result: Tool execution result
        """
        if not hasattr(self.agent, 'rag_indexer'):
            return

        if result.get('success'):
            if tool_name in ['write_file', 'edit_file']:
                file_path = parameters.get('path')
                if file_path:
                    self.agent._reindex_file(file_path)
                    self.agent.context_builder.track_modified_file(file_path)

            elif tool_name == 'delete_file':
                file_path = parameters.get('path')
                if file_path:
                    self.agent._delete_from_index(file_path)

            elif tool_name == 'create_folder':
                folder_path = parameters.get('path')
                if folder_path:
                    self.agent.context_builder.track_created_file(folder_path)
