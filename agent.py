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
from typing import Dict, Any, List, Optional, Tuple

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
from tools.executors import SinglePhaseExecutor, TwoPhaseExecutor  # Phase 2: Extracted executors
from tools.parser import ToolParser  # Phase 2: Extracted parser
from tools.context_builder import ContextBuilder  # Phase 2: Extracted context builder
from tools.tool_router import ToolRouter  # Phase 7: Extracted tool routing
from tools.verification_workflow import VerificationWorkflow  # Phase 7: Extracted verification
from safety.sandbox import Sandbox
from safety.validators import Validator

# Import new Cursor-style improvements
from tools.context_gatherer import ContextGatherer
from tools.verifier import ActionVerifier
from tools.model_manager import SmartModelManager

# Phase 6: Enhanced observability
from tools.metrics import MetricsCollector, get_global_metrics
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
    def __init__(self, config_path: str = "config.yaml") -> None:
        """Initialize the agent with configuration"""
        self.config: Dict[str, Any] = self._load_config(config_path)
        self._setup_logging()
        self._setup_workspace()
        
        # Lazy-load tools (initialize on first use)
        self._fs_tools = None
        self._cmd_tools = None
        self._sys_tools = None
        self._search_tools = None
        self._process_tools = None
        self._network_tools = None
        self._data_tools = None
        self._memory = None
        self._history = None
        
        # Initialize enhanced logging
        self.log_manager = LogManager(self.config)
        self.log_analyzer = LogAnalyzer(self.config)
        self.log_query = LogQuery(self.config)

        # Phase 6: Initialize metrics collection
        self.metrics = get_global_metrics()

        # Initialize RAG indexer (optional)
        if RAG_AVAILABLE:
            self.rag = RAGIndexer(self.config)
        else:
            self.rag = None

        # Initialize safety
        self.sandbox = Sandbox(self.config)
        self.validator = Validator(self.config)

        # Initialize rate limiting and resource monitoring
        from safety.rate_limiter import RateLimiter
        from safety.resource_monitor import ResourceMonitor
        self.rate_limiter = RateLimiter(self.config)
        self.resource_monitor = ResourceMonitor(self.config)

        # Initialize multi-model system
        self.task_analyzer = TaskAnalyzer()  # Legacy analyzer
        self.task_classifier = TaskClassifier()  # Phase 2: Smart routing
        self.model_router = ModelRouter(self.config)

        # Phase 2: Extracted executors
        api_url = f"http://{self.config['ollama']['host']}:{self.config['ollama']['port']}"
        self.single_phase_executor = SinglePhaseExecutor(self.config)
        self.two_phase_executor = TwoPhaseExecutor(api_url, self.config)

        self.parser = ToolParser(self.config)  # Phase 2: Extracted parser
        self.context_builder = ContextBuilder(self.config)  # Phase 2: Extracted context builder

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

        # Phase 7: Tool Router (extracted tool routing logic)
        self.tool_router = ToolRouter(self)

        # Phase 7: Verification Workflow (extracted verification logic)
        self.verification_workflow = VerificationWorkflow(self)

        # Phase 1 Enhancement: Streaming with progress indicator
        from tools.progress_indicator import ProgressIndicator
        from tools.event_bus import get_event_bus
        streaming_config = self.config.get('ollama', {}).get('multi_model', {}).get('streaming', {})
        use_rich = streaming_config.get('use_rich_progress', True)
        self.progress_indicator = ProgressIndicator(use_rich=use_rich)

        # Subscribe progress indicator to event bus if streaming is enabled
        if streaming_config.get('enabled', False):
            event_bus = get_event_bus()
            event_bus.subscribe(self.progress_indicator.handle_event)
            logging.info("Streaming progress indicator enabled")

        # Phase 2: Tool parser for reasoning model responses
        self.tool_parser = ToolParser()

        # Note: Model swaps take ~2.5s on Windows (disk → VRAM)
        # Phase 2 minimizes swaps, Phase 3 adds smart retries
        logging.info("Agent initialized with Phase 1+2+3+7+Streaming improvements")

        logging.info(f"Agent initialized: {self.config['agent']['name']}")
        logging.info(f"Workspace: {self.config['agent']['workspace']}")
        logging.info(f"Ollama API: {self.api_url}")

    # Lazy loading properties for tools
    @property
    def fs_tools(self):
        """Lazy-load FileSystemTools"""
        if self._fs_tools is None:
            self._fs_tools = FileSystemTools(self.config)
            logging.debug("Lazy-loaded FileSystemTools")
        return self._fs_tools

    @property
    def cmd_tools(self):
        """Lazy-load CommandTools"""
        if self._cmd_tools is None:
            self._cmd_tools = CommandTools(self.config)
            logging.debug("Lazy-loaded CommandTools")
        return self._cmd_tools

    @property
    def sys_tools(self):
        """Lazy-load SystemTools"""
        if self._sys_tools is None:
            self._sys_tools = SystemTools(self.config)
            logging.debug("Lazy-loaded SystemTools")
        return self._sys_tools

    @property
    def search_tools(self):
        """Lazy-load SearchTools"""
        if self._search_tools is None:
            self._search_tools = SearchTools(self.config)
            logging.debug("Lazy-loaded SearchTools")
        return self._search_tools

    @property
    def process_tools(self):
        """Lazy-load ProcessTools"""
        if self._process_tools is None:
            self._process_tools = ProcessTools(self.config)
            logging.debug("Lazy-loaded ProcessTools")
        return self._process_tools

    @property
    def network_tools(self):
        """Lazy-load NetworkTools"""
        if self._network_tools is None:
            self._network_tools = NetworkTools(self.config)
            logging.debug("Lazy-loaded NetworkTools")
        return self._network_tools

    @property
    def data_tools(self):
        """Lazy-load DataTools"""
        if self._data_tools is None:
            self._data_tools = DataTools(self.config)
            logging.debug("Lazy-loaded DataTools")
        return self._data_tools

    @property
    def memory(self):
        """Lazy-load MemorySystem"""
        if self._memory is None:
            self._memory = MemorySystem(self.config)
            logging.debug("Lazy-loaded MemorySystem")
        return self._memory

    @property
    def history(self):
        """Lazy-load SessionHistory"""
        if self._history is None:
            self._history = SessionHistory(self.config)
            logging.debug("Lazy-loaded SessionHistory")
        return self._history

    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """Load configuration from YAML file"""
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)

    def _setup_logging(self) -> None:
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
        """Get descriptions of all available tools for the LLM - delegated to ToolRouter"""
        return self.tool_router.get_tools_description()
    
    def execute_tool(self, tool_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a tool by name with given parameters"""
        logging.info(f"Executing tool: {tool_name} with params: {parameters}")

        # Phase 6: Start metrics tracking
        start_time = time.time()

        # Check rate limits
        if not self.rate_limiter.check_rate_limit(tool_name):
            error_msg = f"Rate limit exceeded for {tool_name}. Please try again later."
            # Record failed execution
            self.metrics.record_tool_execution(
                tool_name=tool_name,
                duration=time.time() - start_time,
                success=False,
                parameters=parameters,
                error=error_msg
            )
            return {
                "success": False,
                "error": error_msg
            }

        # Check resource usage
        resource_error = self.resource_monitor.check_resources()
        if resource_error:
            logging.warning(f"Resource check failed: {resource_error}")
            return {
                "success": False,
                "error": f"Resource limit exceeded: {resource_error}"
            }

        # Log tool start (start_time already set above for metrics)
        self.log_manager.log_tool_start(tool_name, parameters)

        try:
            # Delegate core tool routing to ToolRouter, with special handling for complex tools
            result = self.tool_router.execute_tool(tool_name, parameters)

            # Handle file tracking for RAG indexing
            self.tool_router.handle_file_tracking(tool_name, parameters, result)

            # Log tool completion
            execution_time = time.time() - start_time
            logging.info(f"Tool {tool_name} completed in {execution_time:.2f}s")

            # Phase 6: Record metrics
            self.metrics.record_tool_execution(
                tool_name=tool_name,
                duration=execution_time,
                success=result.get("success", False),
                parameters=parameters,
                error=result.get("error") if not result.get("success") else None
            )

            return result
        except Exception as e:
            logging.error(f"Error executing tool {tool_name}: {e}")
            execution_time = time.time() - start_time
            error_result = {"success": False, "error": str(e)}
            logging.error(f"Tool {tool_name} failed after {execution_time:.2f}s")

            # Phase 6: Record failed execution
            self.metrics.record_tool_execution(
                tool_name=tool_name,
                duration=execution_time,
                success=False,
                parameters=parameters,
                error=str(e)
            )

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
        return self.context_builder.load_agent_rules()

    def chat(self, user_message: str) -> str:
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
                logging.info("Using TWO-PHASE execution (Plan -> Execute)")
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
        """Execute task using a single model - delegated to SinglePhaseExecutor"""
        # Select best model for this task
        selected_model = self.model_router.select_model(task_analysis)
        logging.info(f"Selected model: {selected_model}")

        # Build session context and rules
        session_context = self._build_session_context()
        agent_rules = self._load_agent_rules()
        tools_description = self.get_tools_description()

        # Delegate to executor with callbacks
        return self.single_phase_executor.execute(
            user_message=user_message,
            selected_model=selected_model,
            session_context=session_context,
            agent_rules=agent_rules,
            tools_description=tools_description,
            parse_callback=self.parse_tool_calls,
            execute_callback=self.execute_tool,
            history_callback=self.history.add_message
        )

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

    def parse_tool_calls(self, llm_response: str) -> List[Dict[str, Any]]:
        """
        Parse tool calls from LLM response using ToolParser.
        Supports:
        1. Direct TOOL: format (qwen2.5-coder, llama, etc.)
        2. Reasoning format with <think> tags (OpenThinker, DeepSeek-R1)
        """
        # Delegate to ToolParser (Phase 2: Extracted module)
        tool_calls = self.parser.parse(llm_response)

        # If no tools found and response has thinking, try to extract intent
        if not tool_calls and '<think>' in llm_response:
            logging.info("No tool calls found after thinking - attempting to extract intent")
            tool_calls = self._extract_tools_from_reasoning(llm_response)

        return tool_calls

    # NOTE: _strip_thinking_tags and _parse_standard_format moved to ToolParser (Phase 2)

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
            return self.tool_parser._parse_standard_format(tool_response)

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
        return self.context_builder.build_session_context()

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
                # Export metrics before exit
                agent.metrics.export_metrics()
                print("Metrics exported to logs/metrics.json")
                break

            if not user_input:
                continue

            # Phase 6: Special commands for metrics
            if user_input.lower() == '/metrics':
                print("\n" + agent.metrics.generate_report())
                continue

            if user_input.lower() == '/metrics export':
                agent.metrics.export_metrics()
                print("Metrics exported to logs/metrics.json")
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