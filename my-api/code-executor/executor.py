"""
Isolated code execution service
Runs in a separate Docker container for security isolation
"""
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import sys
from io import StringIO
import os
import subprocess
import fnmatch
import glob as glob_module
import re
from pathlib import Path

app = FastAPI(title="Code Executor Service")

# Data directory with available files
DATA_DIR = "/app/data"
# Next.js project directory
NEXTJS_DIR = "/home/user"


class CodeRequest(BaseModel):
    code: str


class ExecutionResponse(BaseModel):
    results: List[str]
    errors: List[str]


class FilesResponse(BaseModel):
    files: List[str]
    data_dir: str


class ListDirectoryRequest(BaseModel):
    path: str = "."
    ignore: Optional[List[str]] = None
    offset: int = 0
    limit: Optional[int] = 16


class ReadFileRequest(BaseModel):
    file_path: str
    limit: Optional[int] = None
    offset: int = 0


class WriteFileRequest(BaseModel):
    file_path: str
    content: str


class ReplaceInFileRequest(BaseModel):
    file_path: str
    old_string: str
    new_string: str
    expected_replacements: int = 1


class SearchFileContentRequest(BaseModel):
    pattern: str
    include: Optional[str] = None
    path: str = "."
    use_regex: bool = False
    fuzzy_threshold: Optional[int] = None
    offset: int = 0
    limit: Optional[int] = 16


class GlobRequest(BaseModel):
    pattern: str
    path: str = "."
    ignore: Optional[List[str]] = None
    offset: int = 0
    limit: Optional[int] = 16


class InstallPackagesRequest(BaseModel):
    packages: List[str]
    package_manager: str = "bun"  # "bun" or "npm"


@app.post("/execute", response_model=ExecutionResponse)
async def execute_code(request: CodeRequest):
    """
    Execute Python code in isolated environment with access to data files
    
    Args:
        request: CodeRequest containing Python code to execute
        
    Returns:
        ExecutionResponse: Results and errors from code execution
    """
    execution = {"results": [], "errors": []}
    old_stdout = sys.stdout
    old_cwd = os.getcwd()
    
    try:
        # Change to data directory so code can access files
        os.chdir(DATA_DIR)
        
        # Capture stdout
        sys.stdout = StringIO()
        
        # Create a namespace for execution with persistent globals
        # Use a shared namespace stored in the app state
        if not hasattr(app.state, 'exec_namespace'):
            # Import database helper into namespace (READ-ONLY access)
            sys.path.insert(0, '/app')
            from db_helper import query_db, get_db_connection, DB_CONFIG
            
            app.state.exec_namespace = {
                '__builtins__': __builtins__,
                'query_db': query_db,  # SELECT only
                'get_db_connection': get_db_connection,  # READ-ONLY connection
                'DB_CONFIG': DB_CONFIG,
                # Note: execute_sql is intentionally NOT included (read-only access)
            }
        
        # Execute code in the namespace
        exec(request.code, app.state.exec_namespace)
        
        # Get captured output
        result = sys.stdout.getvalue()
        sys.stdout = old_stdout
        
        if result:
            execution["results"] = [result]
        else:
            execution["results"] = []
            
    except Exception as e:
        execution["errors"] = [str(e)]
    finally:
        sys.stdout = old_stdout
        os.chdir(old_cwd)
    
    return ExecutionResponse(
        results=execution["results"],
        errors=execution["errors"]
    )


@app.get("/files", response_model=FilesResponse)
async def list_files():
    """
    List available data files
    
    Returns:
        FilesResponse: List of available files in data directory
    """
    try:
        files = []
        if os.path.exists(DATA_DIR):
            files = [f for f in os.listdir(DATA_DIR) if os.path.isfile(os.path.join(DATA_DIR, f))]
        return FilesResponse(files=files, data_dir=DATA_DIR)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health():
    """Health check endpoint"""
    # Check if Next.js is running
    nextjs_running = False
    try:
        import socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = sock.connect_ex(('localhost', 3000))
        sock.close()
        nextjs_running = (result == 0)
    except:
        pass
    
    return {
        "status": "healthy", 
        "service": "code-executor", 
        "data_dir": DATA_DIR,
        "nextjs_running": nextjs_running,
        "nextjs_url": "http://localhost:3001" if nextjs_running else None
    }


@app.post("/reset")
async def reset_namespace():
    """Reset the execution namespace (clear all variables)"""
    if hasattr(app.state, 'exec_namespace'):
        delattr(app.state, 'exec_namespace')
    return {"status": "namespace reset"}


def secure_path(requested_path: str, base_dir: str = NEXTJS_DIR) -> str:
    """Keep paths locked to base_dir or die trying"""
    base_real = os.path.realpath(base_dir)
    
    if not requested_path:
        return base_real
    
    # Handle absolute vs relative paths
    if os.path.isabs(requested_path):
        target_real = os.path.realpath(requested_path)
    else:
        target_real = os.path.realpath(os.path.join(base_real, requested_path))
    
    # Ensure target is within base_dir
    if not target_real.startswith(base_real + os.sep) and target_real != base_real:
        raise ValueError(f"Path '{requested_path}' escapes working directory. You can read/edit only files in '{base_dir}'.")
    
    return target_real


@app.post("/list_directory")
async def list_directory(request: ListDirectoryRequest):
    """List directory contents with pagination"""
    try:
        path = secure_path(request.path, NEXTJS_DIR)
        
        if not os.path.exists(path):
            raise HTTPException(status_code=404, detail=f"Path does not exist: {path}")
        if not os.path.isdir(path):
            raise HTTPException(status_code=400, detail=f"Path is not a directory: {path}")
        
        entries = []
        for item in os.listdir(path):
            if request.ignore and any(fnmatch.fnmatch(item, pattern) for pattern in request.ignore):
                continue
            
            item_path = os.path.join(path, item)
            stat = os.stat(item_path)
            entries.append({
                "name": item,
                "type": "directory" if os.path.isdir(item_path) else "file",
                "size": stat.st_size,
                "modified": stat.st_mtime,
            })
        
        entries.sort(key=lambda x: (x["type"] != "directory", x["name"]))
        total = len(entries)
        start = max(0, request.offset)
        limit = min(request.limit, 64) if request.limit else total
        end = start + limit
        page = entries[start:end]
        
        return {
            "pagination": {
                "total": total,
                "offset": start,
                "limit": limit,
                "has_more": end < total,
            },
            "results": page,
            "path": path
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/read_file")
async def read_file(request: ReadFileRequest):
    """Read file content with optional offset and limit"""
    try:
        file_path = secure_path(request.file_path, NEXTJS_DIR)
        
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail=f"File does not exist: {file_path}")
        if not os.path.isfile(file_path):
            raise HTTPException(status_code=400, detail=f"Path is not a file: {file_path}")
        
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            if request.offset > 0:
                f.seek(request.offset)
            content = f.read(request.limit) if request.limit else f.read()
        
        return {"content": content, "size": len(content)}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/write_file")
async def write_file(request: WriteFileRequest):
    """Write content to file, creating directories if needed"""
    try:
        file_path = secure_path(request.file_path, NEXTJS_DIR)
        
        directory = os.path.dirname(file_path)
        if directory:
            os.makedirs(directory, exist_ok=True)
        
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(request.content)
        
        file_size = os.path.getsize(file_path)
        return {
            "message": f"Written {file_size} bytes to {file_path}",
            "size": file_size,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/replace_in_file")
async def replace_in_file(request: ReplaceInFileRequest):
    """Replace text in file with validation"""
    try:
        file_path = secure_path(request.file_path, NEXTJS_DIR)
        
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail=f"File does not exist: {file_path}")
        
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        
        actual_count = content.count(request.old_string)
        if actual_count != request.expected_replacements:
            raise HTTPException(
                status_code=400,
                detail=f"Expected {request.expected_replacements} occurrences, found {actual_count}"
            )
        
        new_content = content.replace(request.old_string, request.new_string, request.expected_replacements)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(new_content)
        
        return {
            "replacements": request.expected_replacements,
            "message": f"Replaced {request.expected_replacements} occurrences",
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/search_file_content")
async def search_file_content(request: SearchFileContentRequest):
    """Search for pattern in file contents with pagination"""
    try:
        results = []
        total_files_searched = 0
        base_path = secure_path(request.path, NEXTJS_DIR)
        
        regex_pattern = None
        if request.use_regex:
            try:
                regex_pattern = re.compile(request.pattern, re.IGNORECASE)
            except re.error as e:
                raise HTTPException(status_code=400, detail=f"Invalid regex pattern: {e}")
        
        for root, dirs, files in os.walk(base_path):
            for file in files:
                if request.include and not fnmatch.fnmatch(file, request.include):
                    continue
                
                filepath = os.path.join(root, file)
                total_files_searched += 1
                
                try:
                    with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                        for line_num, line in enumerate(f, 1):
                            line_stripped = line.strip()
                            match_data = {
                                "file": filepath,
                                "line": line_num,
                                "content": line_stripped,
                            }
                            
                            if request.fuzzy_threshold is not None:
                                # Simple fuzzy matching (contains check with threshold)
                                if request.pattern.lower() in line.lower():
                                    match_data["similarity"] = 100
                                    results.append(match_data)
                            elif request.use_regex:
                                if regex_pattern.search(line):
                                    results.append(match_data)
                            else:
                                if request.pattern.lower() in line.lower():
                                    results.append(match_data)
                except:
                    continue
        
        if request.fuzzy_threshold is not None:
            results.sort(key=lambda x: x.get("similarity", 0), reverse=True)
        
        total = len(results)
        start = max(0, request.offset)
        limit = min(request.limit, 64) if request.limit else total
        end = start + limit
        page = results[start:end]
        
        return {
            "pagination": {
                "total": total,
                "offset": start,
                "limit": limit,
                "has_more": end < total,
            },
            "results": page,
            "files_searched": total_files_searched
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/glob")
async def glob_files(request: GlobRequest):
    """Find files matching glob pattern with pagination and ignore patterns"""
    try:
        base_path = secure_path(request.path, NEXTJS_DIR)
        original_cwd = os.getcwd()
        
        try:
            os.chdir(base_path)
            
            # Auto-load simple .gitignore patterns if ignore is None
            ignore = request.ignore
            if ignore is None:
                gitignore_path = os.path.join(base_path, ".gitignore")
                if os.path.isfile(gitignore_path):
                    ignore = []
                    try:
                        with open(gitignore_path, "r", encoding="utf-8") as f:
                            for line in f:
                                line = line.strip()
                                if line and not line.startswith("#") and not line.startswith("/"):
                                    if line.endswith("/"):
                                        line = line[:-1]
                                    ignore.append(line)
                    except:
                        ignore = None
            
            matches = glob_module.glob(request.pattern, recursive=True)
            
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
                    results.append({
                        "path": abs_path,
                        "relative_path": match,
                        "size": stat.st_size,
                        "modified": stat.st_mtime,
                    })
            
            results.sort(key=lambda x: x["modified"], reverse=True)
            
            total = len(results)
            start = max(0, request.offset)
            limit = min(request.limit, 64) if request.limit else total
            end = start + limit
            page = results[start:end]
            
            return {
                "pagination": {
                    "total": total,
                    "offset": start,
                    "limit": limit,
                    "has_more": end < total,
                },
                "results": page,
                "pattern": request.pattern
            }
        finally:
            os.chdir(original_cwd)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/install_packages")
async def install_packages(request: InstallPackagesRequest):
    """Install packages using bun or npm"""
    try:
        if request.package_manager not in ["bun", "npm"]:
            raise HTTPException(status_code=400, detail="package_manager must be 'bun' or 'npm'")
        
        original_cwd = os.getcwd()
        try:
            os.chdir(NEXTJS_DIR)
            
            if request.package_manager == "bun":
                cmd = ["bun", "add"] + request.packages
            else:
                cmd = ["npm", "install"] + request.packages
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )
            
            if result.returncode != 0:
                raise HTTPException(
                    status_code=500,
                    detail=f"Package installation failed: {result.stderr}"
                )
            
            return {
                "message": f"Successfully installed {len(request.packages)} package(s)",
                "packages": request.packages,
                "package_manager": request.package_manager,
                "output": result.stdout
            }
        finally:
            os.chdir(original_cwd)
    except HTTPException:
        raise
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=500, detail="Package installation timed out")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
