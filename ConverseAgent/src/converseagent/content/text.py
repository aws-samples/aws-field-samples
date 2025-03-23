from typing import Dict, Literal

from pydantic import Field

from converseagent.content.base import BaseContentBlock


class TextContentBlock(BaseContentBlock):
    """Represents an AmazonBedrock ContentBlock with just text.

    Attributes:
        type (Literal["text"]): The type identifier for the content block. The value is
            set to "text".

    Example:
        ```
            text_block = TextContentBlock(text="Sample text here")
        ```

    """

    type: Literal["text"] = "text"
    text: str = Field(description="The text content of the block", min_length=1)

    def format(self) -> Dict[str, str]:
        """Formats the content block to Converse Format

        Returns:
            Dict[str, str]: A dictionary containing:
                - text: str - The text content

        """
        return {"text": self.text}
