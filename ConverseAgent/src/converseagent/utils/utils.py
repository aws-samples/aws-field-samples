import re
from datetime import datetime
from typing import Dict, List


def extract_xml_content(text: str, tag_name: str) -> str | None:
    pattern = f"<{tag_name}>(.*?)</{tag_name}>"
    match = re.search(pattern, text, re.DOTALL)
    if match:
        return match.group(1).strip()
    else:
        return None


def get_max_tokens(model_id: str) -> int:
    if "claude" in model_id or "llama3-1" in model_id or "llama3-2" in model_id:
        return 4096
    else:
        return 2048


def get_context_window(model_id: str) -> int:
    if "claude-3-5" in model_id:
        return 200000
    elif "llama3-1" in model_id or "llama3-2" in model_id:
        return 128000
    elif "llama3" in model_id:
        return 8000
    else:
        return 4096


def create_timestamp_content_block(
    start_datetime: datetime, current_datetime: datetime | None = None
) -> Dict[str, str]:
    "Returns a timestamp content block"

    if current_datetime is None:
        current_datetime = datetime.now()

    total_runtime = current_datetime - start_datetime

    # Format the output
    formatted_current_datetime = current_datetime.strftime("%A, %Y-%m-%d %H:%M:%S")
    formatted_start_datetime = start_datetime.strftime("%A, %Y-%m-%d %H:%M:%S")

    return {
        "text": f"""<execution_runtime_info> Current Datetime Timestamp: {formatted_current_datetime}\nStart Execution Datetime: {formatted_start_datetime}\nApprox. Total Runtime: {total_runtime}</execution_runtime_info>"""
    }


def create_token_count_content_block(
    input_count: int, output_count: int, total_count: int
) -> Dict[str, str]:
    return {
        "text": f"<execution_token_info>Last Input Tokens: {input_count}\nLast Output Tokens: {output_count}\nLast Total Tokens: {total_count}</execution_token_info>"
    }


def text_tool_response(text: str) -> Dict[str, str | List[Dict[str, str]]]:
    """
    Helper function to create a simple tool response for text only responses

    Args:
        text (str): The text to be included in the tool response

    Returns:
        dict: A dictionary containing the tool response
    """

    tool_result_content: List[Dict[str, str]] = [{"text": text}]

    tool_response: Dict[str, str | List[Dict[str, str]]] = {
        "type": "content",
        "content": tool_result_content,
    }

    return tool_response
