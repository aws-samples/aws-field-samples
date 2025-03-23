from typing import List, Literal

from pydantic import Field, model_validator

from converseagent.content import (
    TextContentBlock,
)
from converseagent.content.user import UserContentBlock
from converseagent.messages.base import BaseMessage


class UserMessage(BaseMessage[UserContentBlock]):
    """This represent an Amazon Bedrock Runtime Message with a role of user.

    The user role has specific ContentBlocks that is allowed.
        (Text, Image, Document, ToolResult)

    Attributes:
        role (Literal["user"]): The role of the Message. Set to "user"
        text (str, optional): Creates a UserMessage with
            a single TextContentBlock for convenience. If content is specified,
            this is ignored.
        content (list[UserContentBlock]): List of content blocks
            for the user message.

    """

    role: Literal["user"] = "user"
    content: List[UserContentBlock] = Field(default_factory=list)
    text: str | None = Field(default=None)

    @model_validator(mode="after")
    def validate_text(self):
        """Appends a TextContentBlock for convenience. Ignores text
        if content is specified.
        """
        if self.text and self.content == []:
            self.append_text_block(text=self.text)

        return self

    def append_text_block(self, text: str):
        """Appends a text block to the user message"""
        self.append_content(TextContentBlock(text=text))

    def append_content(self, block: UserContentBlock):
        """Appends a content block to the user message"""
        self.content.append(block)
