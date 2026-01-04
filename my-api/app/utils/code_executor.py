"""
Code Execution Utilities

This module provides the interface for executing Python code in an isolated
Docker container. The code executor service runs as a separate container
with read-only database access, ensuring security and isolation.

The execution flow:
1. Code is sent via HTTP POST to the code executor service
2. Code is executed in an isolated Python environment
3. Results (stdout, stderr) are captured and returned
4. Generated files (e.g., charts) are saved to a shared volume

Security:
- Code runs in isolated Docker container
- Database access is read-only
- Resource limits prevent abuse
- Timeout protection prevents infinite loops
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

