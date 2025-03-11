from typing import List, Literal

from pydantic import Field, model_validator

from converseagent.content import TextContentBlock
from converseagent.logging_utils.logger_config import setup_logger
from converseagent.messages import BaseMessage

logger = setup_logger(__name__)


class SystemMessage(BaseMessage):
    role: Literal["system"] = "system"
    content: List[TextContentBlock] = Field(default_factory=list)
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

    def append_content(self, block: TextContentBlock):
        """Appends a content block to the user message"""
        self.content.append(block)
