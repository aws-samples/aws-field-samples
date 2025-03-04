from converseagent.content import TextContentBlock
from converseagent.messages import UserMessage


class TestUserMessage:
    """Tests the UserMessage class"""

    def test_user_message(self):
        """Tests the UserMessage class"""

        text_block = TextContentBlock(text="Hello, world!")
        text_block_2 = TextContentBlock(text="Hello, world again!")

        # Test if text is provided only
        message = UserMessage(text=text_block.text)
        assert message.text == text_block.text
        assert message.content == [text_block]

        # Test if text is ignored when content is provided
        message = UserMessage(text=text_block.text, content=[text_block_2])
        assert message.content == [text_block_2]

        # Test if content is provided only
        message = UserMessage(content=[text_block, text_block_2])
        assert message.content == [text_block, text_block_2]

    def test_user_message_append_content(self):
        """Tests the UserMessage append_content method"""

        text_block = TextContentBlock(text="Hello, world!")
        text_block_2 = TextContentBlock(text="Hello, world again!")

        message = UserMessage()

        message.append_content(text_block)
        message.append_content(text_block_2)

        assert message.content == [text_block, text_block_2]

    def test_user_message_serialization(self):
        """Tests the user message serialization"""

        message = UserMessage(text="Hi")

        message_json = message.model_dump_json()

        message_2 = UserMessage.model_validate_json(message_json)

        assert message == message_2
