from converseagent.content import TextContentBlock
from converseagent.messages import BaseMessage


class TestBaseMessage:
    """Tests the BaseMessage class"""

    def test_base_message(self):
        """Tests the BaseMessage class"""
        text_block = TextContentBlock(text="Hello, world!")
        text_block_2 = TextContentBlock(text="Hello, world again!")
        message = BaseMessage(role="user", content=[text_block, text_block_2])

        assert message.role == "user"
        assert message.content == [text_block, text_block_2]

    def test_base_message_append_content(self):
        """Tests the BaseMessage class"""
        text_block = TextContentBlock(text="Hello, world!")
        text_block_2 = TextContentBlock(text="Hello, world again!")

        message = BaseMessage(role="user")

        message.append_content(text_block)
        message.append_content(text_block_2)

        assert message.role == "user"
        assert message.content == [text_block, text_block_2]

    # def test_base_message_serialization(self):
    #     """Tests the BaseMessage serialization"""

    #     text_block = TextContentBlock(text="Hello, world!")
    #     text_block_2 = TextContentBlock(text="Hello, world again!")

    #     message = BaseMessage(role="user")

    #     message.append_content(text_block)
    #     message.append_content(text_block_2)

    #     message_json = message.model_dump_json()

    #     message_expected = (
    #         '{"role":"user","content":'
    #         '[{"type":"text","text":"Hello, world!"},'
    #         '{"type":"text","text":"Hello, world again!"}]}'
    #     )

    #     assert message_json == message_expected

    # def test_base_message_deserialization(self):
    #     """Tests the BaseMessage deserialization"""

    #     text_block = TextContentBlock(text="Hello, world!")
    #     text_block_2 = TextContentBlock(text="Hello, world again!")

    #     message = BaseMessage(role="user")

    #     message.append_content(text_block)
    #     message.append_content(text_block_2)

    #     message_json = message.model_dump_json()

    #     message_2 = BaseMessage.model_validate_json(message_json)

    #     assert message == message_2
