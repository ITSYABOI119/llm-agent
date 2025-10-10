"""
Progress Indicator for Streaming Execution

Displays real-time progress using Rich library with spinners, progress bars,
and status updates. Provides visual feedback during LLM thinking and tool execution.
"""

from typing import Dict, Any, Optional
from rich.console import Console
from rich.live import Live
from rich.spinner import Spinner
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
import time


class ProgressIndicator:
    """Display streaming execution progress to users"""

    def __init__(self, use_rich: bool = True):
        """
        Initialize progress indicator

        Args:
            use_rich: Whether to use Rich library (vs simple text)
        """
        self.use_rich = use_rich
        self.console = Console() if use_rich else None

        # State tracking
        self.current_phase: Optional[str] = None
        self.current_model: Optional[str] = None
        self.thinking_content: str = ""
        self.tools_total: int = 0
        self.tools_completed: int = 0
        self.tool_results: list = []

        # Rich components
        self.live: Optional[Live] = None
        self.progress: Optional[Progress] = None
        self.task_id: Optional[int] = None

    def start(self):
        """Start the progress indicator"""
        if self.use_rich:
            self.progress = Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TaskProgressColumn(),
                console=self.console
            )
            self.live = Live(self.progress, console=self.console, refresh_per_second=10)
            self.live.start()

    def stop(self):
        """Stop the progress indicator"""
        if self.live:
            self.live.stop()
            self.live = None

    def handle_event(self, event: Dict[str, Any]):
        """
        Handle streaming event and update display

        Args:
            event: Event dictionary with type, data, timestamp
        """
        event_type = event['type']
        data = event['data']

        if event_type == 'status':
            self._handle_status(data)
        elif event_type == 'thinking':
            self._handle_thinking(data)
        elif event_type == 'tool_call':
            self._handle_tool_call(data)
        elif event_type == 'tool_result':
            self._handle_tool_result(data)
        elif event_type == 'complete':
            self._handle_complete(data)

    def _handle_status(self, data: Dict):
        """Handle status update event"""
        phase = data.get('phase', 'unknown')
        model = data.get('model', 'unknown')

        self.current_phase = phase
        self.current_model = model

        # Use ASCII symbols for Windows compatibility
        if self.use_rich:
            if phase == 'initializing':
                self.console.print(f"[bold blue]>> Initializing...[/bold blue]")
            elif phase == 'calling_llm':
                self.console.print(f"[bold yellow]>> Thinking with {model}...[/bold yellow]")
                if self.progress and self.task_id is None:
                    self.task_id = self.progress.add_task(
                        f"Processing with {model}",
                        total=None  # Indeterminate progress
                    )
            elif phase == 'parsing_tools':
                self.console.print(f"[bold cyan]>> Preparing tools...[/bold cyan]")
        else:
            # Simple text output
            if phase == 'initializing':
                print(">> Initializing...")
            elif phase == 'calling_llm':
                print(f">> Thinking with {model}...")
            elif phase == 'parsing_tools':
                print(">> Preparing tools...")

    def _handle_thinking(self, data: Dict):
        """Handle thinking/reasoning event"""
        content = data.get('content', '')
        self.thinking_content += content

        if self.use_rich:
            # Show abbreviated thinking content
            preview = self.thinking_content[-100:].strip()
            if preview:
                self.console.print(f"[dim].. {preview}...[/dim]", end='\r')
        else:
            # Simple text - overwrite line
            preview = self.thinking_content[-80:].strip()
            if preview:
                print(f".. {preview}...", end='\r', flush=True)

    def _handle_tool_call(self, data: Dict):
        """Handle tool call event"""
        if 'status' in data and data['status'] == 'executing':
            tool_name = data['tool']
            index = data['index']
            total = data['total']

            self.tools_total = total
            self.tools_completed = index

            if self.use_rich:
                # Update progress bar
                if self.task_id and self.progress:
                    self.progress.update(
                        self.task_id,
                        description=f"Executing {tool_name} ({index + 1}/{total})",
                        completed=index,
                        total=total
                    )
                self.console.print(f"[bold green]>> Executing {tool_name} ({index + 1}/{total})...[/bold green]")
            else:
                print(f"\n>> Executing {tool_name} ({index + 1}/{total})...")

    def _handle_tool_result(self, data: Dict):
        """Handle tool result event"""
        tool_name = data['tool']
        status = data['status']
        execution_time = data.get('execution_time', 0)

        self.tools_completed += 1
        self.tool_results.append(data)

        status_icon = '[OK]' if status == 'success' else '[FAIL]'
        status_color = 'green' if status == 'success' else 'red'

        if self.use_rich:
            self.console.print(
                f"[{status_color}]{status_icon} {tool_name} ({execution_time:.2f}s)[/{status_color}]"
            )
            # Update progress
            if self.task_id and self.progress:
                self.progress.update(
                    self.task_id,
                    completed=self.tools_completed
                )
        else:
            print(f"{status_icon} {tool_name} ({execution_time:.2f}s)")

    def _handle_complete(self, data: Dict):
        """Handle completion event"""
        status = data.get('status', 'unknown')

        if self.use_rich:
            if status == 'success':
                self.console.print("[bold green]>> Complete![/bold green]")
            else:
                self.console.print(f"[bold red]>> Failed: {data.get('error', 'Unknown error')}[/bold red]")

            # Show summary table
            if self.tool_results:
                self._show_summary_table()
        else:
            if status == 'success':
                print("\n>> Complete!")
            else:
                print(f"\n>> Failed: {data.get('error', 'Unknown error')}")

    def _show_summary_table(self):
        """Show summary table of tool executions"""
        if not self.use_rich or not self.tool_results:
            return

        table = Table(title="Execution Summary", show_header=True, header_style="bold magenta")
        table.add_column("Tool", style="cyan")
        table.add_column("Status", style="green")
        table.add_column("Time (s)", justify="right", style="yellow")

        for result in self.tool_results:
            status_icon = '[OK]' if result['status'] == 'success' else '[FAIL]'
            table.add_row(
                result['tool'],
                status_icon,
                f"{result.get('execution_time', 0):.2f}"
            )

        self.console.print(table)

    def show_model_switch(self, from_model: str, to_model: str, reason: str = ""):
        """Show model switching notification"""
        if self.use_rich:
            text = Text()
            text.append(">> Model Switch: ", style="bold yellow")
            text.append(from_model, style="cyan")
            text.append(" -> ", style="dim")
            text.append(to_model, style="green")
            if reason:
                text.append(f" ({reason})", style="dim")

            panel = Panel(text, border_style="yellow")
            self.console.print(panel)
        else:
            msg = f">> Model Switch: {from_model} -> {to_model}"
            if reason:
                msg += f" ({reason})"
            print(msg)

    def show_two_phase_start(self, planning_model: str, execution_model: str):
        """Show two-phase execution start notification"""
        if self.use_rich:
            text = Text()
            text.append(">> Two-Phase Execution\n", style="bold magenta")
            text.append("Planning: ", style="bold")
            text.append(f"{planning_model}\n", style="cyan")
            text.append("Execution: ", style="bold")
            text.append(execution_model, style="green")

            panel = Panel(text, border_style="magenta")
            self.console.print(panel)
        else:
            print(f">> Two-Phase Execution")
            print(f"Planning: {planning_model}")
            print(f"Execution: {execution_model}")
