"""
Rich logging utilities for coding agent
Provides enhanced logging with emojis and tool call visualization
"""
import logging
from rich.logging import RichHandler
from rich.panel import Panel
from rich.console import Console

# Define custom logger levels with emojis
LOG_LEVELS = {
    "DEBUG": "🐛",
    "INFO": "✨",
    "WARNING": "⚠️",
    "ERROR": "❌",
    "CRITICAL": "🔥",
    "TOOL": "🤖",
}


class EmojiRichHandler(RichHandler):
    """Custom Rich handler with emoji support for log levels"""
    
    def get_level_text(self, record):
        level_emoji = LOG_LEVELS.get(record.levelname, "➡️")
        return f"[{record.levelname}] {level_emoji}"


# Configure the rich logger for coding agent
rich_logger = logging.getLogger("coding_agent")
rich_logger.setLevel(logging.INFO)
rich_logger.propagate = False

if not rich_logger.handlers:
    handler = EmojiRichHandler(
        rich_tracebacks=True,
        show_path=False,
        show_time=False,
        show_level=True,
        markup=False,
    )
    rich_logger.addHandler(handler)

console = Console()


def get_rich_logger(name: str | None = None):
    """
    Returns a logger instance with Rich formatting.
    
    Args:
        name: Optional logger name. Defaults to "coding_agent"
        
    Returns:
        Logger instance configured with Rich handler
    """
    if name:
        logger = logging.getLogger(name)
        if not logger.handlers:
            handler = EmojiRichHandler(
                rich_tracebacks=True,
                show_path=False,
                show_time=False,
                show_level=True,
                markup=False,
            )
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)
            logger.propagate = False
        return logger
    return rich_logger


def log_tool_call(tool_name: str, args_str: str, result: dict):
    """
    Logs a tool call with a card-like display using Rich panels.
    
    Args:
        tool_name: Name of the tool that was called
        args_str: String representation of the arguments
        result: Result dictionary from the tool execution
    """
    MAX_DISPLAY_LENGTH = 200

    result_str = str(result)

    # Truncate if too long
    if len(args_str) > MAX_DISPLAY_LENGTH:
        args_str = args_str[:MAX_DISPLAY_LENGTH] + "..."
    if len(result_str) > MAX_DISPLAY_LENGTH:
        result_str = result_str[:MAX_DISPLAY_LENGTH] + "..."

    panel_content = f"[bold]{tool_name}[/bold]\n"
    panel_content += f"Arguments: [cyan]{args_str}[/cyan]\n"
    panel_content += f"Result: [magenta]{result_str}[/magenta]"
    console.print(
        Panel(panel_content, title=f"{LOG_LEVELS['TOOL']} Tool Call", expand=False)
    )

