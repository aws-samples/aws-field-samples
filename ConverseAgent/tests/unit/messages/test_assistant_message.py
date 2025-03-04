from converseagent.content import TextContentBlock, ToolUseContentBlock
from converseagent.messages import AssistantMessage

from converseagent.utils.utils import extract_xml_content


class TestAssistantMessage:
    """Tests the AssistantMessage class"""

    def test_assistant_message(self, sample_tool_use, sample_assistant_text):
        """Tests the AssistantMessage class"""

        # Used in the assertion
        text_content_block = TextContentBlock(text=sample_assistant_text)

        tool_use_dict = {
            "tool_use_id": sample_tool_use["tool_use_id"],
            "tool_name": sample_tool_use["tool_name"],
            "tool_input": sample_tool_use["tool_input"],
        }

        # Used in the assertion
        tool_use_content_block = ToolUseContentBlock(**tool_use_dict)

        # Used in the assertion
        content = [text_content_block, tool_use_content_block]

        # Mimic the assistant message from Converse API
        message = {
            "role": "assistant",
            "content": [block.format() for block in content],
        }

        # Build the assistant message
        assistant_message = AssistantMessage(message=message)

        # Test the extractions
        assert assistant_message.current_plan == extract_xml_content(
            sample_assistant_text, "current_plan"
        )
        assert assistant_message.update_message == extract_xml_content(
            sample_assistant_text, "update_message"
        )
        assert assistant_message.thinking == extract_xml_content(
            sample_assistant_text, "thinking"
        )
        assert assistant_message.final_response == extract_xml_content(
            sample_assistant_text, "final_response"
        )

        # Test the contents
        assert assistant_message.content == content
