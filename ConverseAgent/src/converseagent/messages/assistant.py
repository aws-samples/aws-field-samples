from typing import Annotated, Dict, List, Literal, Union

from pydantic import Field, model_validator

from converseagent.content import (
    DocumentContentBlock,
    ImageContentBlock,
    TextContentBlock,
    ToolUseContentBlock,
)
from converseagent.logging_utils.logger_config import setup_logger
from converseagent.messages.base import BaseMessage
from converseagent.utils.utils import extract_xml_content

logger = setup_logger(__name__)

AssistantContentBlock = Annotated[
    Union[
        TextContentBlock, ImageContentBlock, DocumentContentBlock, ToolUseContentBlock
    ],
    Field(discriminator="type"),
]


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
    message: Dict | None = Field(default_factory=dict)
    text: str | None = Field(default=None)
    content: List[AssistantContentBlock] = Field(default_factory=list)
    current_plan: str | None = Field(default=None)
    update_message: str | None = Field(default=None)
    thinking: str | None = Field(default=None)
    final_response: str | None = Field(default=None)

    @model_validator(mode="after")
    def validate_text(self) -> "AssistantMessage":
        """Appends a TextContentBlock for convenience. Ignores text
        if content is specified.

        Returns:
            AssistantMessage: The AssistMessage instance
        """
        if self.text and self.content == [] and self.message == {}:
            self.append_text_block(text=self.text)

        return self

    def model_post_init(self, *args, **kwargs):
        """Post initialization for the AssistantMessage class

        Extracts the following information:
            - current plan
            - thinking
            - update message
            - final response
            - tool use information

        """

        if self.message:
            for block in self.message["content"]:
                if "text" in block:
                    self.append_content(TextContentBlock(text=block["text"]))

                    self.text = block["text"]

                    self.current_plan = extract_xml_content(
                        block["text"], "current_plan"
                    )

                    if self.current_plan:
                        self.current_plan = self.current_plan
                        logger.debug(f"Current plan: {self.current_plan}")

                    self.thinking = extract_xml_content(block["text"], "thinking")

                    if self.thinking:
                        self.thinking = self.thinking
                        logger.debug(f"Thinking: {self.thinking}")

                    self.update_message = extract_xml_content(
                        block["text"], "update_message"
                    )
                    if self.update_message:
                        self.update_message = self.update_message
                        logger.debug(f"Update message: {self.update_message}")

                    self.final_response = extract_xml_content(
                        block["text"], "final_response"
                    )
                    if self.final_response:
                        self.final_response = self.final_response
                        logger.debug(f"Final response: {self.final_response}")

                if "toolUse" in block:
                    tool = block["toolUse"]
                    tool_use_id = tool["toolUseId"]
                    tool_name = tool["name"]
                    tool_input = tool["input"]

                    self.append_content(
                        ToolUseContentBlock(
                            tool_use_id=tool_use_id,
                            tool_name=tool_name,
                            tool_input=tool_input,
                        )
                    )

        return self

    def append_text_block(self, text: str):
        """Appends a text block to the user message"""
        self.append_content(TextContentBlock(text=text))

    def append_content(self, block: AssistantContentBlock):
        """Appends a content block to the user message"""
        self.content.append(block)
