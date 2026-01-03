"""
Tools for coding agent
Adapted to work with Docker code-executor instead of e2b sandbox
"""
import json
from typing import Callable, Optional, Dict, Any
from app.utils.code_executor import execute_code


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
    ignore_str = repr(ignore) if ignore else "None"
    limit_str = str(limit) if limit else "None"
    
    code = f"""
import os
import json

path = {repr(path)}
ignore = {ignore_str}
offset = {offset}
limit = {limit_str}

entries = []
if os.path.exists(path) and os.path.isdir(path):
    for item in os.listdir(path):
        if ignore:
            import fnmatch
            if any(fnmatch.fnmatch(item, pattern) for pattern in ignore):
                continue
        item_path = os.path.join(path, item)
        stat = os.stat(item_path)
        entries.append({{
            "name": item,
            "type": "directory" if os.path.isdir(item_path) else "file",
            "size": stat.st_size,
            "modified": stat.st_mtime,
        }})

entries.sort(key=lambda x: (x["type"] != "directory", x["name"]))
total = len(entries)
start = max(0, offset)
end = start + (limit if limit else total)
page = entries[start:end]

result = {{
    "pagination": {{
        "total": total,
        "offset": start,
        "limit": limit if limit else total,
        "has_more": end < total,
    }},
    "results": page,
    "path": os.path.abspath(path)
}}
print(json.dumps(result, indent=2))
"""
    execution = execute_code(code)
    try:
        if execution["results"]:
            result = json.loads("".join(execution["results"]))
        else:
            result = {"error": "No output", "results": []}
    except:
        result = {"error": "Failed to parse result", "results": execution["results"]}
    
    if execution["errors"]:
        result["errors"] = "; ".join(execution["errors"]) if isinstance(execution["errors"], list) else str(execution["errors"])
    
    return result, {}


def read_file_tool(file_path: str, limit: Optional[int] = None, offset: int = 0, sbx=None):
    """Read file content"""
    limit_str = str(limit) if limit else "None"
    
    code = f"""
import json

file_path = {repr(file_path)}
limit = {limit_str}
offset = {offset}

try:
    with open(file_path, "r", encoding="utf-8", errors="replace") as f:
        if offset > 0:
            f.seek(offset)
        content = f.read(limit) if limit else f.read()
    
    result = {{
        "content": content,
        "size": len(content)
    }}
    print(json.dumps(result, indent=2))
except Exception as e:
    print(json.dumps({{"error": str(e)}}, indent=2))
"""
    execution = execute_code(code)
    try:
        if execution["results"]:
            result = json.loads("".join(execution["results"]))
        else:
            result = {"error": "No output"}
    except:
        result = {"error": "Failed to parse result", "raw": execution["results"]}
    
    if execution["errors"]:
        result["errors"] = "; ".join(execution["errors"]) if isinstance(execution["errors"], list) else str(execution["errors"])
    
    return result, {}


def write_file_tool(content: str, file_path: str, sbx=None):
    """Write content to file"""
    code = f"""
import json
import os

content = {repr(content)}
file_path = {repr(file_path)}

try:
    directory = os.path.dirname(file_path)
    if directory:
        os.makedirs(directory, exist_ok=True)
    
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)
    
    file_size = os.path.getsize(file_path)
    result = {{
        "message": f"Written {{file_size}} bytes to {{file_path}}",
        "size": file_size
    }}
    print(json.dumps(result, indent=2))
except Exception as e:
    print(json.dumps({{"error": str(e)}}, indent=2))
"""
    execution = execute_code(code)
    try:
        if execution["results"]:
            result = json.loads("".join(execution["results"]))
        else:
            result = {"error": "No output"}
    except:
        result = {"error": "Failed to parse result"}
    
    if execution["errors"]:
        result["errors"] = "; ".join(execution["errors"]) if isinstance(execution["errors"], list) else str(execution["errors"])
    
    return result, {}


def replace_in_file_tool(file_path: str, old_string: str, new_string: str, expected_replacements: int = 1, sbx=None):
    """Replace text in file"""
    code = f"""
import json

file_path = {repr(file_path)}
old_string = {repr(old_string)}
new_string = {repr(new_string)}
expected_replacements = {expected_replacements}

try:
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    actual_count = content.count(old_string)
    if actual_count != expected_replacements:
        result = {{"error": f"Expected {{expected_replacements}} occurrences, found {{actual_count}}"}}
    else:
        new_content = content.replace(old_string, new_string, expected_replacements)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(new_content)
        result = {{
            "replacements": expected_replacements,
            "message": f"Replaced {{expected_replacements}} occurrences"
        }}
    print(json.dumps(result, indent=2))
except Exception as e:
    print(json.dumps({{"error": str(e)}}, indent=2))
"""
    execution = execute_code(code)
    try:
        if execution["results"]:
            result = json.loads("".join(execution["results"]))
        else:
            result = {"error": "No output"}
    except:
        result = {"error": "Failed to parse result"}
    
    if execution["errors"]:
        result["errors"] = "; ".join(execution["errors"]) if isinstance(execution["errors"], list) else str(execution["errors"])
    
    return result, {}


def search_file_content_tool(pattern: str, include: Optional[str] = None, path: str = ".", 
                             use_regex: bool = False, fuzzy_threshold: Optional[int] = None,
                             offset: int = 0, limit: Optional[int] = 16, sbx=None):
    """Search for pattern in file contents"""
    include_str = repr(include) if include else "None"
    fuzzy_str = str(fuzzy_threshold) if fuzzy_threshold else "None"
    limit_str = str(limit) if limit else "None"
    
    code = f"""
import os
import json
import re
import fnmatch

pattern = {repr(pattern)}
include = {include_str}
path = {repr(path)}
use_regex = {use_regex}
fuzzy_threshold = {fuzzy_str}
offset = {offset}
limit = {limit_str}

results = []
total_files_searched = 0

regex_pattern = None
if use_regex:
    try:
        regex_pattern = re.compile(pattern, re.IGNORECASE)
    except re.error as e:
        print(json.dumps({{"error": f"Invalid regex pattern: {{e}}"}}, indent=2))
        exit(1)

for root, dirs, files in os.walk(path):
    for file in files:
        if include and not fnmatch.fnmatch(file, include):
            continue
        
        filepath = os.path.join(root, file)
        total_files_searched += 1
        
        try:
            with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                for line_num, line in enumerate(f, 1):
                    line_stripped = line.strip()
                    match_data = {{
                        "file": filepath,
                        "line": line_num,
                        "content": line_stripped,
                    }}
                    
                    if fuzzy_threshold is not None:
                        from difflib import SequenceMatcher
                        similarity = int(SequenceMatcher(None, pattern.lower(), line.lower()).ratio() * 100)
                        if similarity >= fuzzy_threshold:
                            match_data["similarity"] = similarity
                            results.append(match_data)
                    elif use_regex:
                        if regex_pattern.search(line):
                            results.append(match_data)
                    else:
                        if pattern.lower() in line.lower():
                            results.append(match_data)
        except:
            continue

if fuzzy_threshold is not None:
    results.sort(key=lambda x: x["similarity"], reverse=True)

total = len(results)
start = max(0, offset)
end = start + (limit if limit else total)
page = results[start:end]

result = {{
    "pagination": {{
        "total": total,
        "offset": start,
        "limit": limit if limit else total,
        "has_more": end < total,
    }},
    "results": page,
    "files_searched": total_files_searched
}}
print(json.dumps(result, indent=2))
"""
    execution = execute_code(code)
    try:
        if execution["results"]:
            result = json.loads("".join(execution["results"]))
        else:
            result = {"error": "No output", "results": []}
    except:
        result = {"error": "Failed to parse result", "results": execution["results"]}
    
    if execution["errors"]:
        result["errors"] = "; ".join(execution["errors"]) if isinstance(execution["errors"], list) else str(execution["errors"])
    
    return result, {}


def glob_tool(pattern: str, path: str = ".", ignore: Optional[list] = None, 
              offset: int = 0, limit: Optional[int] = 16, sbx=None):
    """Find files matching glob pattern"""
    ignore_str = repr(ignore) if ignore else "None"
    limit_str = str(limit) if limit else "None"
    
    code = f"""
import os
import glob
import json
import fnmatch

pattern = {repr(pattern)}
path = {repr(path)}
ignore = {ignore_str}
offset = {offset}
limit = {limit_str}

original_cwd = os.getcwd()
try:
    os.chdir(path)
    matches = glob.glob(pattern, recursive=True)
    
    results = []
    for match in matches:
        if ignore:
            should_ignore = False
            path_parts = match.split(os.sep)
            
            for ignore_pattern in ignore:
                if any(fnmatch.fnmatch(part, ignore_pattern) for part in path_parts):
                    should_ignore = True
                    break
                if match.startswith(ignore_pattern + os.sep) or match == ignore_pattern:
                    should_ignore = True
                    break
                if fnmatch.fnmatch(match, ignore_pattern):
                    should_ignore = True
                    break
            
            if should_ignore:
                continue
        
        abs_path = os.path.abspath(match)
        if os.path.isfile(abs_path):
            stat = os.stat(abs_path)
            results.append({{
                "path": abs_path,
                "relative_path": match,
                "size": stat.st_size,
                "modified": stat.st_mtime,
            }})
    
    results.sort(key=lambda x: x["modified"], reverse=True)
    
    total = len(results)
    start = max(0, offset)
    end = start + (limit if limit else total)
    page = results[start:end]
    
    result = {{
        "pagination": {{
            "total": total,
            "offset": start,
            "limit": limit if limit else total,
            "has_more": end < total,
        }},
        "results": page,
        "pattern": pattern
    }}
    print(json.dumps(result, indent=2))
finally:
    os.chdir(original_cwd)
"""
    execution = execute_code(code)
    try:
        if execution["results"]:
            result = json.loads("".join(execution["results"]))
        else:
            result = {"error": "No output", "results": []}
    except:
        result = {"error": "Failed to parse result", "results": execution["results"]}
    
    if execution["errors"]:
        result["errors"] = "; ".join(execution["errors"]) if isinstance(execution["errors"], list) else str(execution["errors"])
    
    return result, {}


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

