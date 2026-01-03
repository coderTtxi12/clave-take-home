"""
Isolated code execution service
Runs in a separate Docker container for security isolation
"""
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List
import sys
from io import StringIO
import os

app = FastAPI(title="Code Executor Service")

# Data directory with available files
DATA_DIR = "/app/data"


class CodeRequest(BaseModel):
    code: str


class ExecutionResponse(BaseModel):
    results: List[str]
    errors: List[str]


class FilesResponse(BaseModel):
    files: List[str]
    data_dir: str


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
    return {"status": "healthy", "service": "code-executor", "data_dir": DATA_DIR}


@app.post("/reset")
async def reset_namespace():
    """Reset the execution namespace (clear all variables)"""
    if hasattr(app.state, 'exec_namespace'):
        delattr(app.state, 'exec_namespace')
    return {"status": "namespace reset"}
