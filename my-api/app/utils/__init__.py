"""
Utility functions and helpers
"""
from app.utils.rich_logger import get_rich_logger, log_tool_call
from app.utils.image_processor import (
    convert_image_to_base64,
    embed_images_in_markdown,
    extract_image_paths_from_results,
    process_agent_response_with_images
)

__all__ = [
    "get_rich_logger", 
    "log_tool_call",
    "convert_image_to_base64",
    "embed_images_in_markdown",
    "extract_image_paths_from_results",
    "process_agent_response_with_images",
]

