"""
Coding agent endpoints
"""
from fastapi import APIRouter, status, HTTPException
from app.core.logging import get_logger
from app.core.config import settings
import json
import uuid
from app.models.coding_agent import (
    CodeExecutionRequest, 
    CodeExecutionResponse,
    CodingAgentRequest,
    CodingAgentResponse
)
from app.utils.code_executor import execute_code
from app.utils.tools import tools as all_tools
from app.utils.tols_schemas import tools_schemas as all_tools_schemas, execute_code_schema
from app.services.coding_agent_service import coding_agent, log, MockSandbox
from app.services.session_manager import get_session_manager
from app.utils.image_processor import process_agent_response_with_images
from openai import OpenAI
from prompts.prompts import SYSTEM_PROMPT_DATA_ANALYST

router = APIRouter(tags=["coding-agent"])
logger = get_logger()


@router.post(
    "/coding-agent/execute",
    response_model=CodeExecutionResponse,
    status_code=status.HTTP_200_OK,
    summary="Execute code in isolated container",
    description="Execute Python code and return results or errors"
)
async def execute_code_endpoint(request: CodeExecutionRequest):
    """
    Execute code endpoint - runs code in isolated Docker container
    
    Args:
        request: CodeExecutionRequest containing Python code to execute
        
    Returns:
        CodeExecutionResponse: Results and errors from code execution
    """
    logger.info("Code execution endpoint called")
    
    execution = execute_code(request.code)
    
    return CodeExecutionResponse(
        results=execution["results"],
        errors=execution["errors"]
    )


@router.post(
    "/coding-agent/query",
    response_model=CodingAgentResponse,
    status_code=status.HTTP_200_OK,
    summary="Data analyst agent",
    description="Send a natural language query and get code generation + execution"
)
async def coding_agent_endpoint(request: CodingAgentRequest):
    """
    Coding agent endpoint - natural language to code execution
    
    Args:
        request: CodingAgentRequest with query and optional parameters
        
    Returns:
        CodingAgentResponse: Answer, code executed, results, and conversation history
    """
    logger.info(f"Coding agent query: {request.query[:100]}...")
    
    # Check if OpenAI API key is configured
    if not settings.OPENAI_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="OpenAI API key not configured. Set OPENAI_API_KEY environment variable."
        )
    
    try:
        # Initialize session manager
        session_manager = get_session_manager()
        
        # Generate or use provided session_id
        session_id = request.session_id or str(uuid.uuid4())
        
        # Retrieve conversation history from Redis
        # If messages are provided in request (deprecated), use those instead
        if request.messages:
            logger.warning("Using deprecated 'messages' field. Consider using session_id instead.")
            messages = request.messages
        else:
            messages = session_manager.get_messages(session_id)
        
        # Track the number of messages BEFORE this execution
        # This helps us identify which results are from THIS execution only
        messages_before_execution = len(messages)
        
        # Initialize OpenAI client
        client = OpenAI(api_key=settings.OPENAI_API_KEY)
        
        # Create mock sandbox (we use Docker code-executor instead)
        sbx = MockSandbox()
        
        # Use only execute_code tool
        tools = {"execute_code": all_tools["execute_code"]}
        tools_schemas = [execute_code_schema]
        
        # Run coding agent with log wrapper
        messages, usage = log(
            coding_agent,
            client=client,
            sbx=sbx,
            query=request.query,
            tools=tools,
            tools_schemas=tools_schemas,
            max_steps=request.max_steps,
            system=SYSTEM_PROMPT_DATA_ANALYST,
            messages=messages,
            usage=0,
        )
        
        # Save updated conversation history to Redis
        session_manager.save_messages(session_id, messages)
        
        # Get session TTL
        session_ttl = session_manager.get_session_ttl(session_id)
        
        # Extract final answer and code executed from messages
        # IMPORTANT: Only process messages from THIS execution (new messages)
        final_answer = None
        code_executed = []
        results = []
        
        # Only process NEW messages (from this execution)
        new_messages = messages[messages_before_execution:]
        
        for msg in new_messages:
            if msg.get("role") == "assistant" and msg.get("content"):
                final_answer = msg.get("content")
            elif msg.get("role") == "tool":
                # Parse tool output - only from THIS execution
                content = msg.get("content", "")
                try:
                    output = json.loads(content)
                    results.append(output)
                except:
                    pass
        
        # If no final answer in new messages, check the last assistant message overall
        if not final_answer:
            for msg in reversed(messages):
                if msg.get("role") == "assistant" and msg.get("content"):
                    final_answer = msg.get("content")
                    break
        
        # If no final answer found, use last assistant message
        if not final_answer:
            for msg in reversed(messages):
                if msg.get("role") == "assistant" and msg.get("content"):
                    final_answer = msg.get("content")
                    break
        
        if not final_answer:
            final_answer = "Unable to generate a response. Please try again."
        
        # Process images: detect IMAGE: markers and extract base64
        processed_response = process_agent_response_with_images(final_answer, results)
        
        return CodingAgentResponse(
            answer=processed_response["answer"],
            image_base64=processed_response.get("image_base64"),
            image_mime=processed_response.get("image_mime"),
            session_id=session_id,
            code_executed=code_executed,
            results=results,
            steps_taken=len([m for m in messages if m.get("type") == "function_call"]),
            messages=messages,
            session_ttl=session_ttl
        )
        
    except Exception as e:
        logger.error(f"Coding agent error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Coding agent failed: {str(e)}"
        )


@router.delete(
    "/coding-agent/session/{session_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete a conversation session",
    description="Delete a session and its conversation history from Redis"
)
async def delete_session_endpoint(session_id: str):
    """
    Delete a session endpoint
    
    Args:
        session_id: Session ID to delete
        
    Returns:
        Success message
    """
    try:
        session_manager = get_session_manager()
        success = session_manager.delete_session(session_id)
        
        if success:
            return {"message": f"Session {session_id} deleted successfully"}
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Session {session_id} not found"
            )
    except Exception as e:
        logger.error(f"Failed to delete session: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete session: {str(e)}"
        )


@router.get(
    "/coding-agent/session/{session_id}",
    status_code=status.HTTP_200_OK,
    summary="Get session information",
    description="Retrieve session metadata and conversation history"
)
async def get_session_endpoint(session_id: str):
    """
    Get session information endpoint
    
    Args:
        session_id: Session ID to retrieve
        
    Returns:
        Session information including messages and TTL
    """
    try:
        session_manager = get_session_manager()
        messages = session_manager.get_messages(session_id)
        ttl = session_manager.get_session_ttl(session_id)
        
        if ttl is None and len(messages) == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Session {session_id} not found"
            )
        
        return {
            "session_id": session_id,
            "message_count": len(messages),
            "messages": messages,
            "ttl_seconds": ttl,
            "ttl_hours": round(ttl / 3600, 2) if ttl else None
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get session: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get session: {str(e)}"
        )


