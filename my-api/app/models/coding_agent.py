"""
Coding agent request/response models
"""
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any


class CodeExecutionRequest(BaseModel):
    """Request model for code execution"""
    code: str


class CodeExecutionResponse(BaseModel):
    """Response model for code execution"""
    results: List[str]
    errors: List[str]


class CodingAgentRequest(BaseModel):
    """Request model for coding agent with query"""
    query: str = Field(..., description="Natural language query for data analysis")
    session_id: Optional[str] = Field(None, description="Session ID for conversation continuity (auto-generated if not provided)")
    max_steps: int = Field(default=5, description="Maximum number of iterations", ge=1, le=20)
    context: Optional[str] = Field(None, description="Additional context or data description")
    messages: Optional[List[Dict[str, Any]]] = Field(default=None, description="Conversation history (deprecated, use session_id instead)")


class CodingAgentResponse(BaseModel):
    """Response model for coding agent"""
    answer: str = Field(..., description="Final answer to the query")
    image_base64: Optional[str] = Field(None, description="Base64 encoded image if a chart was generated")
    image_mime: Optional[str] = Field(None, description="MIME type of the image (e.g., 'image/png')")
    session_id: str = Field(..., description="Session ID for this conversation")
    code_executed: List[str] = Field(default_factory=list, description="Code snippets that were executed")
    results: List[Dict[str, Any]] = Field(default_factory=list, description="Execution results")
    steps_taken: int = Field(..., description="Number of steps taken")
    messages: List[Dict[str, Any]] = Field(default_factory=list, description="Full conversation history")
    session_ttl: Optional[int] = Field(None, description="Session time-to-live in seconds")

