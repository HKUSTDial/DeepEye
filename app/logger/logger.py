from ast import Dict
import sys
from datetime import datetime
from pathlib import Path
from loguru import logger as _logger

from app.config import WORKSPACE_ROOT


def create_info_box(title: str, content: Dict) -> str:
    """
    Create a clean info display with title and content, no borders.
    
    Args:
        title: The title of the info box
        content: Dictionary of key-value pairs to display
    
    Returns:
        A single string representing the formatted content with newlines
    """
    lines = []
    
    # Title with separator
    lines.append(f"{title}")
    lines.append("─" * (len(title) + 4))
    
    # Content lines - direct output without width control
    for key, value in content.items():
        lines.append(f"  {key}: {str(value)}")
    
    # Return the complete formatted content
    return "\n" + "\n".join(lines) + "\n"


_print_level = "INFO"


def define_log_level(print_level="INFO", logfile_level="DEBUG", name: str = None):
    """Adjust the log level to above level"""
    global _print_level
    _print_level = print_level

    current_date = datetime.now()
    formatted_date = current_date.strftime("%Y%m%d%H%M%S")
    log_name = (
        f"{name}_{formatted_date}" if name else formatted_date
    )  # name a log with prefix name

    _logger.remove()
    _logger.add(sys.stderr, level=print_level)
    _logger.add(WORKSPACE_ROOT / f"logs/{log_name}.log", level=logfile_level)
    return _logger


logger = define_log_level()


if __name__ == "__main__":
    logger.info("Starting application")
    logger.debug("Debug message")
    logger.warning("Warning message")
    logger.error("Error message")
    logger.critical("Critical message")

    try:
        raise ValueError("Test error")
    except Exception as e:
        logger.exception(f"An error occurred: {e}")