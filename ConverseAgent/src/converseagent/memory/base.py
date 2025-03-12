from typing import Annotated, Any, Dict, List, Union

from pydantic import BaseModel, Field

from converseagent.messages import AssistantMessage, UserMessage

Message = Annotated[Union[UserMessage, AssistantMessage], Field(discriminator="role")]


class BaseMemory(BaseModel):
    """Base memory class for storing message history.

    This class provides basic memory operations for storing and retrieving messages.
    This will store the message history in-memory.

    Attributes:
        memory (List[Message]): The list of messages

    Example:
        ```
            memory = BaseMemory()

            # Add message
            memory.append(message=message)

            # Get messages
            memory.get_messages()

            # Get formatted messages
            memory.get_converse_messages()

            # Clears memory
            memory.clear()
    """

    # Stores the list of messages
    memory: List[Message] = Field(default_factory=list)

    def append(self, message: Message) -> None:
        """Append a message to the memory.

        Args:
            message (Message): The Message to append to memory
        """
        self.memory.append(message)

    def get_messages(self) -> List[Message]:
        """Returns the full message history

        Returns:
            list: The list of user (UserMessage) and
                assistant (AssistantMessage) messages
        """

        return self.memory

    def set_messages(self, messages: List[Message]) -> None:
        """Sets the messages in memory

        Args:
            messages (List[Message]): The list of messages to set
        """
        self.memory = messages

    def get_converse_messages(self) -> List[Dict[str, Any]]:
        """Returns the full message history in Converse format

        Returns:
            list: The list of stored messages in Converse format
        """

        return [message.format() for message in self.memory]

    def clear(self) -> None:
        """Clear all messages from memory."""
        self.memory = []
