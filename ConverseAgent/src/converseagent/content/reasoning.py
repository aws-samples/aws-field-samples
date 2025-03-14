from typing import Dict, Literal

from pydantic import Field

from converseagent.content.base import BaseContentBlock


class ReasoningContentBlock(BaseContentBlock):
    """Represents an Amazon Bedrock ContentBlock for thinking

    Attributes:
        type (Literal["thinking"]): The type identifier for the content block. The value is
            set to "thinking".

    Example:
        ```
            thinking_block = ThinkingContentBlock(thinking="The assistant thinking here")
        ```

    """

    type: Literal["thinking"] = "thinking"
    reasoning_text: str = Field(
        description="The thinking content of the block", min_length=1
    )
    signature: str = Field(description="The signature of the thinking")

    def format(self) -> Dict[str, Dict[str, Dict[str, str]]]:
        """Formats the content block to Converse Format

        Returns:
            Dict[str, str]: A dictionary containing:
                - text: str - The text content

        """
        return {
            "reasoningContent": {
                "reasoningText": {
                    "text": self.reasoning_text,
                    "signature": self.signature,
                }
            }
        }
