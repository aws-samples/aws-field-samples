from converseagent.content import TextContentBlock
from converseagent.messages import SystemMessage

DEFAULT_SYSTEM_PROMPT_TEMPLATE = """
You are a helpful AI assistant. You will respond in a friendly manner.
"""

DEFAULT_SYSTEM_MESSAGE = SystemMessage()
DEFAULT_SYSTEM_MESSAGE.append_content(
    TextContentBlock(text=DEFAULT_SYSTEM_PROMPT_TEMPLATE)
)
