"""
Coding Agent Service
Implements an agentic loop for code generation and execution
"""
from typing import List, Dict, Any, Optional, Callable, Generator, Literal
from openai import OpenAI
import json
import re
import base64
from app.core.config import settings
from app.core.logging import get_logger
from app.utils.rich_logger import log_tool_call
from app.utils.tols_schemas import tools_schemas, execute_code_schema
from app.utils.tools import tools, execute_tool
import sys
from pathlib import Path
# Add parent directory to path to import prompts
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from prompts.prompts import SYSTEM_PROMPT_COMPRESS_MESSAGES

logger = get_logger()

# Mock Sandbox class for compatibility (we use Docker code-executor instead)
class MockSandbox:
    """Mock Sandbox for compatibility with coding_agent interface"""
    pass

TOKEN_LIMIT = 60_000
COMPRESS_THRESHOLD = 0.7
STATE_SNAPSHOT_PATTERN = re.compile(
    r"<state_snapshot>(.*?)</state_snapshot>", re.DOTALL
)


def clean_messages_for_llm(messages: list[dict]) -> list[dict]:
    return [{k: v for k, v in msg.items() if not k.startswith("_")} for msg in messages]


def compress_messages(client: OpenAI, messages: list[dict]) -> list[dict]:
    # Use standard OpenAI API
    response = client.chat.completions.create(
        model="gpt-5-nano",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT_COMPRESS_MESSAGES},
            *messages,
            {
                "role": "user",
                "content": "First, reason in your scratchpad. Then, generate the <state_snapshot>.",
            },
        ],
    )

    text = response.choices[0].message.content or ""
    # we extract the <state_snapshot>
    context = "\n".join(STATE_SNAPSHOT_PATTERN.findall(text))
    new_messages = [
        {
            "role": "user",
            "content": f"This is snapshot of the conversation so far:\n{context}",
        },
        {
            "role": "assistant",
            "content": "Got it. Thanks for the additional context!",
        },
    ]

    return new_messages


def format_messages(messages: list[dict]) -> str:
    content = ""
    for message in messages:
        if "role" in message:
            if message["role"] == "user":
                content += f"[user]: {message['content']}\n"
            elif message["role"] == "assistant":
                content += f"[assistant]: {message.get('content', '')}\n"
            elif message["role"] == "tool":
                content += f"[function_result]: {message.get('content', '')}\n"
        elif "type" in message:
            if message["type"] == "function_call":
                content += f"[assistant] Calls {message['name']}\n"
            elif message["type"] == "function_call_output":
                content += f"[function_result]: {message['output']}\n"
    return content



def get_compress_message_index(messages: list[dict]) -> int:
    # couting the number of chars
    chars = [len(json.dumps(message)) for message in messages]
    total_chars = sum(chars)
    # we keep a portion of them
    target_chars = total_chars * COMPRESS_THRESHOLD
    curr_chars = 0
    for index, char in enumerate(chars):
        curr_chars += char
        if (curr_chars) >= target_chars:
            return index
    return len(messages)



def get_first_user_message_index(messages: list[dict]) -> int:
    first_user_message_index = 0
    for index, message in enumerate(messages):
        if "role" in message:
            if message["role"] == "user":
                first_user_message_index = index
                break
    return first_user_message_index

def maybe_compress_messages(
    client: OpenAI, messages: list[dict], usage: int
) -> list[dict]:
    if usage <= TOKEN_LIMIT * COMPRESS_THRESHOLD:
        return messages
    compress_index = get_compress_message_index(messages)
    if compress_index >= len(messages):
        return messages
    compress_index += get_first_user_message_index(messages[compress_index:])
    if compress_index <= 0:
        return messages
    # edge case, if we cut and the last message is `function_call`
    # we need to add the output as well
    last_message = messages[compress_index - 1]
    if "type" in last_message:
        if last_message["type"] == "function_call":
            # add its output as well
            compress_index += 1

    to_compress_messages = messages[:compress_index]
    to_keep_messages = messages[compress_index:]

    if len(to_compress_messages) > 0:
        logger.info(f"[agent] 📦 compressing messages [0...{compress_index}]...")
        return [*compress_messages(client, to_compress_messages), *to_keep_messages]

    return messages



def coding_agent(
    client: OpenAI,
    sbx: Any,  # MockSandbox or None
    query: str,
    tools: dict[str, Callable] = None,
    tools_schemas: list[dict] = None,
    max_steps: int = 5,
    system: Optional[str] = "You are a senior python programmer",
    messages: Optional[list[dict]] = None,
    usage: Optional[int] = 0,
    model: str = "gpt-4.1-mini",
    **model_kwargs,
) -> Generator[tuple[dict, dict, int], None, tuple[list[dict], int]]:
    # Use default tools if not provided
    if tools is None:
        from app.services.coding_agent_service import tools as default_tools
        tools = default_tools
    if tools_schemas is None:
        from app.services.coding_agent_service import tools_schemas as default_schemas
        tools_schemas = default_schemas
    if messages is None:
        messages = []
    # up to here
    start_index = len(messages)
    user_message = {"role": "user", "content": query}
    messages.append(user_message)
    yield user_message, messages, usage

    steps = 0
    # continue till max_steps
    while steps < max_steps:
        messages = maybe_compress_messages(
            client, clean_messages_for_llm(messages), usage
        )
        # Use chat.completions.create instead of responses.create (standard OpenAI API)
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system},
                *clean_messages_for_llm(messages),
            ],
            tools=tools_schemas,
            tool_choice="auto",
            **model_kwargs,
        )
        usage = response.usage.total_tokens
        has_function_call = False
        response_message = response.choices[0].message
        
        # Add assistant message
        assistant_msg = response_message.model_dump()
        messages.append(assistant_msg)
        yield assistant_msg, messages, usage
        
        # Handle tool calls
        if response_message.tool_calls:
            has_function_call = True
            for tool_call in response_message.tool_calls:
                name = tool_call.function.name
                arguments = tool_call.function.arguments
                result, metadata = execute_tool(name, arguments, tools, sbx=sbx)
                
                # OpenAI expects tool responses with role="tool"
                result_msg = {
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": json.dumps(result),
                    "_metadata": metadata,  # Internal metadata (won't be sent to OpenAI)
                }
                messages.append(result_msg)
                yield result_msg, messages, usage

        steps += 1
        if not has_function_call:
            break

    return messages, usage


def log(generator_func, *args, **kwargs):
    """Wraps the coding_agent and handles logging like the original"""
    gen = generator_func(*args, **kwargs)
    step = 0
    pending_tool_calls = {}  # tool_call_id -> (name, arguments)

    try:
        while True:
            part_dict, messages, usage = next(gen)
            
            # Handle different message types
            role = part_dict.get("role")
            part_type = part_dict.get("type")

            if part_type == "reasoning":
                if step == 0:
                    logger.info(f"✨: [agent-#{step}] Thinking...")
                    step += 1
                logger.info(" ...")
            elif part_type == "message":
                content = part_dict.get("content")
                if content and content[0].get("text"):
                    logger.info(f"✨: {content[0]['text']}")
            elif role == "assistant" and part_dict.get("tool_calls"):
                # Assistant is calling tools
                for tool_call in part_dict["tool_calls"]:
                    call_id = tool_call["id"]
                    name = tool_call["function"]["name"]
                    arguments = tool_call["function"]["arguments"]
                    pending_tool_calls[call_id] = (name, arguments)
            elif role == "tool":
                # Tool response
                tool_call_id = part_dict.get("tool_call_id")
                if tool_call_id in pending_tool_calls:
                    name, arguments = pending_tool_calls.pop(tool_call_id)
                    result = json.loads(part_dict.get("content", "{}"))
                    # Convert arguments to string if it's not already
                    args_str = arguments if isinstance(arguments, str) else json.dumps(arguments)
                    log_tool_call(name, args_str, result)
                metadata = part_dict.get("_metadata")
                if metadata:
                    images = metadata.get("images")
                    if images:
                        # Store images in metadata for potential future use
                        # In API context, we don't display images directly
                        logger.info(f"[agent] 📊 Generated {len(images)} image(s)")
            elif part_type == "function_call":
                # Legacy format support
                call_id = part_dict.get("call_id")
                name = part_dict.get("name")
                arguments = part_dict.get("arguments")
                pending_tool_calls[call_id] = (name, arguments)
            elif part_type == "function_call_output":
                # Legacy format support
                call_id = part_dict.get("call_id")
                if call_id in pending_tool_calls:
                    name, arguments = pending_tool_calls.pop(call_id)
                    result = json.loads(part_dict.get("output", "{}"))
                    args_str = arguments if isinstance(arguments, str) else json.dumps(arguments)
                    log_tool_call(name, args_str, result)
                metadata = part_dict.get("_metadata")
                if metadata:
                    images = metadata.get("images")
                    if images:
                        logger.info(f"[agent] 📊 Generated {len(images)} image(s)")

    except StopIteration as e:
        messages, final_usage = e.value
        logger.info(f"[agent] 🔢 tokens: {final_usage} total")
        return messages, final_usage
