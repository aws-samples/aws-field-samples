from typing import List, Literal

from pydantic import Field

from converseagent.content import (
    TextContentBlock,
)
from converseagent.content.assistant import AssistantContentBlock
from converseagent.logging_utils.logger_config import setup_logger
from converseagent.messages.base import BaseMessage
from converseagent.utils.utils import extract_xml_content

logger = setup_logger(__name__)


class AssistantMessage(BaseMessage):
    """This represents an Amazon Bedrock Runtime Message with a role of assistant.

    The assistant role has specific ContentBlocks that is allowed.
        (Text, Image, Document, ToolUse)

    Attributes:
        role (Literal["assistant"]): The role of the Message. Set to "assistant"
        message (Dict): The raw message received from the Converse API after the
            converse call. This message is then parsed into the AssistantMessage.
        text (str): Creates an AssistantMessage with a single TextContentBlock for
            convenience. If content is specified, this is ignored.
        current_plan (str): The current plan extracted from the message. This is used
            to improve the plan following capabilities of the agent. The current_plan
            is extracted from <current_plan></current_plan> tags.
        update_message (str): The update message extracted from the message. This is
            used to pass into the update_callback_function to show updates to the front
            end. The update_message is extracted from <update_message></update_message>.
        thinking (str): The thinking of the agent extracted from the message. The
            thinking message is extracted from <thinking></thinking>.
        final_response (str): The final response extracted from the message. The
            final response is extracted from <final_response></final_response>.
    """

    role: Literal["assistant"] = "assistant"

    # The raw assistant response message from Converse API
    text: str | None = Field(default=None)
    content: List[AssistantContentBlock] = Field(default_factory=list)
    current_plan: str | None = Field(default=None)
    update_message: str | None = Field(default=None)
    thinking: str | None = Field(default=None)
    final_response: str | None = Field(default=None)
    reasoning: str | None = Field(default=None)

    def model_post_init(self, *args, **kwargs):
        """Post initialization for the AssistantMessage class

        Extracts the text from the assistant messages
        """

        if self.content:
            for block in self.content:
                if isinstance(block, TextContentBlock):
                    self.text = block.text

                    self.current_plan = extract_xml_content(self.text, "current_plan")

                    self.final_response = extract_xml_content(
                        self.text, "final_response"
                    )

                    self.thinking = extract_xml_content(self.text, "thinking")

                    if self.thinking:
                        self.thinking = self.thinking
                        logger.debug(f"Thinking: {self.thinking}")

                    self.update_message = extract_xml_content(
                        self.text, "update_message"
                    )
                    if self.update_message:
                        self.update_message = self.update_message
                        logger.debug(f"Update message: {self.update_message}")

                    if self.final_response:
                        self.final_response = self.final_response
                        logger.debug(f"Final response: {self.final_response}")
        return self

    def append_text_block(self, text: str):
        """Appends a text block to the user message"""
        self.append_content(TextContentBlock(text=text))

    def append_content(self, block: AssistantContentBlock):
        """Appends a content block to the user message"""
        self.content.append(block)
