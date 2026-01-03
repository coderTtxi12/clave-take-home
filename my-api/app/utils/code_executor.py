"""
Code execution utilities for coding agent
Executes code in isolated Docker container via HTTP
"""
from typing import TypedDict
import httpx
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger()


class Execution(TypedDict):
    results: list[str]
    errors: list[str]


def execute_code(code: str) -> Execution:
    """
    Execute Python code in isolated Docker container
    
    Args:
        code: Python code as string to execute
        
    Returns:
        Execution: Dictionary with results and errors lists
    """
    execution: Execution = {"results": [], "errors": []}
    
    try:
        # Make HTTP request to code executor service
        with httpx.Client(
            timeout=settings.CODE_EXECUTOR_TIMEOUT,
            base_url=settings.CODE_EXECUTOR_URL
        ) as client:
            response = client.post(
                "/execute",
                json={"code": code}
            )
            response.raise_for_status()
            data = response.json()
            execution["results"] = data.get("results", [])
            execution["errors"] = data.get("errors", [])
            
    except httpx.TimeoutException:
        logger.error("Code execution timeout")
        execution["errors"] = ["Code execution timed out"]
    except httpx.HTTPError as e:
        logger.error(f"HTTP error communicating with code executor: {e}")
        execution["errors"] = [f"Service error: {str(e)}"]
    except Exception as e:
        logger.error(f"Unexpected error in code execution: {e}")
        execution["errors"] = [f"Unexpected error: {str(e)}"]
    
    return execution

