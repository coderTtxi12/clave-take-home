"""
Code execution utilities for coding agent
Executes code in isolated Docker container via HTTP
"""
from typing import TypedDict, Optional, List, Dict, Any
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


def _make_request(endpoint: str, json_data: Dict[str, Any]) -> Dict[str, Any]:
    """Make HTTP request to code executor service"""
    try:
        with httpx.Client(
            timeout=settings.CODE_EXECUTOR_TIMEOUT,
            base_url=settings.CODE_EXECUTOR_URL
        ) as client:
            response = client.post(endpoint, json=json_data)
            response.raise_for_status()
            return response.json()
    except httpx.TimeoutException:
        logger.error(f"Request timeout for {endpoint}")
        raise Exception("Request timed out")
    except httpx.HTTPError as e:
        logger.error(f"HTTP error for {endpoint}: {e}")
        raise Exception(f"Service error: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error for {endpoint}: {e}")
        raise


def list_directory(path: str = ".", ignore: Optional[List[str]] = None, 
                   offset: int = 0, limit: Optional[int] = 16) -> Dict[str, Any]:
    """List directory contents"""
    return _make_request("/list_directory", {
        "path": path,
        "ignore": ignore,
        "offset": offset,
        "limit": limit
    })


def read_file(file_path: str, limit: Optional[int] = None, offset: int = 0) -> Dict[str, Any]:
    """Read file content"""
    return _make_request("/read_file", {
        "file_path": file_path,
        "limit": limit,
        "offset": offset
    })


def write_file(file_path: str, content: str) -> Dict[str, Any]:
    """Write content to file"""
    return _make_request("/write_file", {
        "file_path": file_path,
        "content": content
    })


def replace_in_file(file_path: str, old_string: str, new_string: str, 
                   expected_replacements: int = 1) -> Dict[str, Any]:
    """Replace text in file"""
    return _make_request("/replace_in_file", {
        "file_path": file_path,
        "old_string": old_string,
        "new_string": new_string,
        "expected_replacements": expected_replacements
    })


def search_file_content(pattern: str, include: Optional[str] = None, path: str = ".",
                       use_regex: bool = False, fuzzy_threshold: Optional[int] = None,
                       offset: int = 0, limit: Optional[int] = 16) -> Dict[str, Any]:
    """Search for pattern in file contents"""
    return _make_request("/search_file_content", {
        "pattern": pattern,
        "include": include,
        "path": path,
        "use_regex": use_regex,
        "fuzzy_threshold": fuzzy_threshold,
        "offset": offset,
        "limit": limit
    })


def glob_files(pattern: str, path: str = ".", ignore: Optional[List[str]] = None,
              offset: int = 0, limit: Optional[int] = 16) -> Dict[str, Any]:
    """Find files matching glob pattern"""
    return _make_request("/glob", {
        "pattern": pattern,
        "path": path,
        "ignore": ignore,
        "offset": offset,
        "limit": limit
    })


def install_packages(packages: List[str], package_manager: str = "bun") -> Dict[str, Any]:
    """Install packages using bun or npm"""
    return _make_request("/install_packages", {
        "packages": packages,
        "package_manager": package_manager
    })

