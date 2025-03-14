from typing import Any, Dict, Generic, List, Literal, TypeVar, Union

from pydantic import BaseModel, Field

from converseagent.content import BaseContentBlock

T = TypeVar("T", bound=BaseContentBlock)


class BaseMessage(BaseModel, Generic[T]):
    """This class represents an Amazon  Bedrock Runtime Message.

    Attributes:
        role (str): The role of the message. Must be "user" or "assistant"
        content (List[ContentBlock]): The list of content blocks

    """

    role: Literal["user", "assistant", "system", "tool"]
    content: List[T] = Field(default_factory=list)

    def format(self) -> Dict[str, Union[str, List[Dict[str, Any]]]]:
        """Returns the message in the Converse message format

        Returns:
            Dict[str, Union[str, List[Dict[str, Any]]]]: The dict containing
                the converse formatted Message

        """
        return {
            "role": self.role,
            "content": [block.format() for block in self.content],
        }

    def append_content(self, block: T) -> None:
        """Appends the block to the message

        Args:
            block (BaseContentBlock): The block to append to the message

        """
        self.content.append(block)

    def get_content(self) -> List[T]:
        """Returns the content blocks

        Returns:
            List[ContentBlock]: The list of content blocks

        """
        return self.content

    def get_text(self):
        """Returns the text of the message"""
        return "\n".join([block.text for block in self.content if block.type == "text"])
