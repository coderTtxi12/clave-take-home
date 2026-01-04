"""
Tools for coding agent
Adapted to work with Docker code-executor instead of e2b sandbox
"""
import json
from typing import Callable, Optional, Dict, Any
from app.utils.code_executor import (
    execute_code,
    list_directory,
    read_file,
    write_file,
    replace_in_file,
    search_file_content,
    glob_files,
    install_packages
)


def execute_code_tool(code: str, sbx=None, language: str = "python"):
    """
    Execute code using the Docker code-executor
    
    Args:
        code: Python code to execute
        sbx: Mock sandbox (not used, kept for compatibility)
        language: Language to execute (default: python)
        
    Returns:
        Tuple of (result_dict, metadata)
    """
    if language == "bash":
        # For bash, wrap in Python subprocess call
        code = f"import subprocess\nimport sys\nresult = subprocess.run(['bash', '-c', {repr(code)}], capture_output=True, text=True)\nprint(result.stdout)\nif result.stderr:\n    print(result.stderr, file=sys.stderr)\nsys.exit(result.returncode)"
    
    execution = execute_code(code)
    
    # Convert to dict format similar to e2b
    result = {
        "results": execution["results"],
        "errors": execution["errors"]
    }
    
    metadata = {}
    return result, metadata


def list_directory_tool(path: str = ".", ignore: Optional[list] = None, offset: int = 0, limit: Optional[int] = 16, sbx=None):
    """List directory contents"""
    try:
        result = list_directory(path, ignore, offset, limit)
        return result, {}
    except Exception as e:
        return {"error": str(e), "results": []}, {}


def read_file_tool(file_path: str, limit: Optional[int] = None, offset: int = 0, sbx=None):
    """Read file content"""
    try:
        result = read_file(file_path, limit, offset)
        return result, {}
    except Exception as e:
        return {"error": str(e)}, {}


def write_file_tool(content: str, file_path: str, sbx=None):
    """Write content to file"""
    try:
        result = write_file(file_path, content)
        return result, {}
    except Exception as e:
        return {"error": str(e)}, {}


def replace_in_file_tool(file_path: str, old_string: str, new_string: str, expected_replacements: int = 1, sbx=None):
    """Replace text in file"""
    try:
        result = replace_in_file(file_path, old_string, new_string, expected_replacements)
        return result, {}
    except Exception as e:
        return {"error": str(e)}, {}


def search_file_content_tool(pattern: str, include: Optional[str] = None, path: str = ".", 
                             use_regex: bool = False, fuzzy_threshold: Optional[int] = None,
                             offset: int = 0, limit: Optional[int] = 16, sbx=None):
    """Search for pattern in file contents"""
    try:
        result = search_file_content(pattern, include, path, use_regex, fuzzy_threshold, offset, limit)
        return result, {}
    except Exception as e:
        return {"error": str(e), "results": []}, {}


def glob_tool(pattern: str, path: str = ".", ignore: Optional[list] = None, 
              offset: int = 0, limit: Optional[int] = 16, sbx=None):
    """Find files matching glob pattern"""
    try:
        result = glob_files(pattern, path, ignore, offset, limit)
        return result, {}
    except Exception as e:
        return {"error": str(e), "results": []}, {}


def install_packages_tool(packages: list, package_manager: str = "bun", sbx=None):
    """Install packages using bun or npm"""
    try:
        result = install_packages(packages, package_manager)
        return result, {}
    except Exception as e:
        return {"error": str(e)}, {}


# Define tools dictionary
tools: Dict[str, Callable] = {
    "execute_code": execute_code_tool,
    "execute_bash": lambda **a: execute_code_tool(**a, language="bash"),
    "list_directory": list_directory_tool,
    "read_file": read_file_tool,
    "write_file": write_file_tool,
    "replace_in_file": replace_in_file_tool,
    "search_file_content": search_file_content_tool,
    "glob": glob_tool,
    "install_packages": install_packages_tool,
}


def execute_tool(name: str, args: str, tools_dict: Dict[str, Callable], **kwargs):
    """
    Execute a tool by name with given arguments
    
    Args:
        name: Tool name
        args: Arguments as JSON string or dict
        tools_dict: Dictionary of available tools
        **kwargs: Additional keyword arguments (e.g., sbx)
        
    Returns:
        Tuple of (result_dict, metadata)
    """
    metadata = {}
    try:
        args_dict = json.loads(args) if isinstance(args, str) else args
        if name not in tools_dict:
            return {"error": f"Tool {name} doesn't exist."}, metadata
        result, metadata = tools_dict[name](**args_dict, **kwargs)
    except json.JSONDecodeError as e:
        result = {"error": f"{name} failed to parse arguments: {str(e)}"}
    except KeyError as e:
        result = {"error": f"Missing key in arguments: {str(e)}"}
    except Exception as e:
        result = {"error": str(e)}
    return result, metadata

