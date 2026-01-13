import logging
import sys
from typing import Optional, Dict, Any, AsyncGenerator
from rich.console import Console
from rich.logging import RichHandler
from rich.panel import Panel
from rich.text import Text
from rich.markdown import Markdown

# 1. System Logger Configuration
def setup_logger(name: str = "deepeye", level: int = logging.INFO) -> logging.Logger:
    """
    Configures and returns a standard logger with RichHandler.
    """
    logging.basicConfig(
        level=level,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler(rich_tracebacks=True)]
    )
    return logging.getLogger(name)

logger = setup_logger()

# 2. Agent Stream Logger (The "Pretty Printer")
class AgentStreamLogger:
    """
    Helper to pretty-print agent execution events (tokens, tool calls).
    """
    def __init__(self):
        self.console = Console()
        self.last_node = None

    async def print_stream(self, event_stream: AsyncGenerator[Dict[str, Any], None]):
        """
        Consumes an astream_events iterator and prints it beautifully.
        """
        async for event in event_stream:
            event_type = event.get("event")
            name = event.get("name")
            data = event.get("data", {})
            tags = event.get("tags", [])
            
            is_sub_agent = "sub_agent" in tags

            # 1. LLM Token Streaming
            if event_type == "on_chat_model_stream":
                chunk = data.get("chunk")
                if hasattr(chunk, "content") and chunk.content:
                    # Style: 
                    # Sub-Agent: Dim text on dark grey background (visualizing "internal thought")
                    # Supervisor: Bold cyan (visualizing "final response")
                    style = "dim white on #1c1c1c" if is_sub_agent else "bold cyan"
                    self.console.print(chunk.content, end="", style=style)

            # 1.1 LLM Stream End (Ensure newline)
            elif event_type == "on_chat_model_end":
                self.console.print() # Newline after streaming finishes

            # 2. Tool Call Start
            elif event_type == "on_tool_start":
                self.console.print() # Newline
                tool_name = name
                tool_input = data.get("input")
                
                title_prefix = "  ↳ " if is_sub_agent else ""
                title = f"{title_prefix}🛠️ Tool Call: [bold yellow]{tool_name}[/bold yellow]"
                
                self.console.print(
                    Panel(
                        f"Input: {tool_input}", 
                        title=title,
                        border_style="dim yellow" if is_sub_agent else "yellow",
                        padding=(0, 2) if is_sub_agent else (1, 2)
                    )
                )

            # 3. Tool Result
            elif event_type == "on_tool_end":
                output = data.get("output")
                if hasattr(output, "content"):
                    content = output.content
                else:
                    content = str(output)
                
                # Truncate if too long
                display_content = content[:500] + "..." if len(content) > 500 else content
                
                title_prefix = "  ↳ " if is_sub_agent else ""
                title = f"{title_prefix}✅ Tool Result: [bold green]{name}[/bold green]"
                
                self.console.print(
                    Panel(
                        display_content,
                        title=title,
                        border_style="dim green" if is_sub_agent else "green",
                        padding=(0, 2) if is_sub_agent else (1, 2)
                    )
                )
                # Removed "Agent: " prefix to avoid formatting issues.
                # The next stream chunk will simply appear.

            # 4. Chain Error
            elif event_type == "on_chain_error":
                self.console.print(f"\n❌ Error: {str(data)}", style="bold red")

        self.console.print("\n\n[End of Stream]", style="dim")

