from converseagent.content import TextContentBlock
from converseagent.memory import BaseMemory
from converseagent.messages import UserMessage, AssistantMessage


class TestBaseMemory:
    "Test the BaseMemory Class"

    def test_append(self):
        """Tests the append method"""

        memory = BaseMemory()
        user_message = UserMessage(text="Hi")
        memory.append(message=user_message)

        assert memory.get_messages() == [user_message]

    def test_get_converse_messages(self):
        """Tests the get_converse_messages method"""

        memory = BaseMemory()
        user_message = UserMessage(text="Hi")
        memory.append(message=user_message)

        assert memory.get_converse_messages() == [user_message.format()]

    def test_clear_messages(self):
        """Tests the clear method"""

        memory = BaseMemory()
        user_message = UserMessage(text="Hi")
        memory.append(message=user_message)

        # Check if append worked to ensure something is in it
        assert memory.get_messages() == [user_message]

        # Clear the memory
        memory.clear()

        # Check if the memory is empty
        assert memory.get_messages() == []

    def test_base_memory_serialization(self):
        """Tests to see if the model serializes correctly with both
        user and assistant messages present.
        """

        memory = BaseMemory()
        user_message = UserMessage(text="Hi")
        memory.append(message=user_message)

        assistant_message = AssistantMessage(text="How can I help you?")
        memory.append(message=assistant_message)

        memory_json = memory.model_dump_json()

        memory_2 = BaseMemory.model_validate_json(memory_json)

        assert memory == memory_2
