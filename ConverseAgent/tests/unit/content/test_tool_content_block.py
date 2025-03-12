from converseagent.content import (  # type: ignore
    TextContentBlock,
    ToolResultContentBlock,
    ToolUseContentBlock,
)


class TestToolUseContentBlock:
    def test_tool_use_content_block(self, sample_tool_use):
        tool_use_content_block = ToolUseContentBlock(
            tool_use_id=sample_tool_use["tool_use_id"],
            tool_name=sample_tool_use["tool_name"],
            tool_input=sample_tool_use["tool_input"],
        )

        assert tool_use_content_block.tool_use_id == sample_tool_use["tool_use_id"]
        assert tool_use_content_block.tool_name == sample_tool_use["tool_name"]
        assert tool_use_content_block.tool_input == sample_tool_use["tool_input"]

    def test_tool_use_converse_format(self, sample_tool_use):
        tool_use_content_block = ToolUseContentBlock(
            tool_use_id=sample_tool_use["tool_use_id"],
            tool_name=sample_tool_use["tool_name"],
            tool_input=sample_tool_use["tool_input"],
        )

        converse_format = {
            "toolUse": {
                "toolUseId": tool_use_content_block.tool_use_id,
                "name": tool_use_content_block.tool_name,
                "input": tool_use_content_block.tool_input,
            }
        }

        assert tool_use_content_block.format() == converse_format


class TestToolResultContentBlock:
    def test_tool_result_content_block(self, sample_tool_use):
        # Create sample content
        text_content_block = TextContentBlock(text="Sample 1")
        text_content_block_2 = TextContentBlock(text="Sample 2")

        tool_result_content_block = ToolResultContentBlock(
            tool_use_id=sample_tool_use["tool_use_id"],
            tool_result_content=[text_content_block, text_content_block_2],
        )

        assert tool_result_content_block.tool_use_id == sample_tool_use["tool_use_id"]
        assert tool_result_content_block.tool_result_content == [
            text_content_block,
            text_content_block_2,
        ]

    def test_tool_result_append_content(self, sample_tool_use):
        tool_result_content_block = ToolResultContentBlock(
            tool_use_id=sample_tool_use["tool_use_id"], tool_result_content=[]
        )

        text_content_block = TextContentBlock(text="Sample 1")
        text_content_block_2 = TextContentBlock(text="Sample 2")

        tool_result_content_block.append_content(text_content_block)
        tool_result_content_block.append_content(text_content_block_2)

        assert tool_result_content_block.tool_result_content == [
            text_content_block,
            text_content_block_2,
        ]

    def test_tool_result_converse_format(self, sample_tool_use):
        tool_result_content_block = ToolResultContentBlock(
            tool_use_id=sample_tool_use["tool_use_id"], tool_result_content=[]
        )

        text_content_block = TextContentBlock(text="Sample 1")
        text_content_block_2 = TextContentBlock(text="Sample 2")

        tool_result_content_block.append_content(text_content_block)
        tool_result_content_block.append_content(text_content_block_2)

        converse_format = {
            "toolResult": {
                "toolUseId": tool_result_content_block.tool_use_id,
                "content": [text_content_block.format(), text_content_block_2.format()],
            }
        }

        assert tool_result_content_block.format() == converse_format

    def test_tool_result_serialization(self, sample_tool_use):
        # Create sample content
        text_content_block = TextContentBlock(text="Sample 1")
        text_content_block_2 = TextContentBlock(text="Sample 2")

        tool_result_content_block = ToolResultContentBlock(
            tool_use_id=sample_tool_use["tool_use_id"],
            tool_result_content=[text_content_block, text_content_block_2],
        )

        tool_result_json = tool_result_content_block.model_dump_json()

        tool_result_expected = (
            '{"type":"tool_result","metadata":{},"tool_use_id":"some_id",'
            '"tool_result_content":[{"type":"text","metadata":{},"text":"Sample 1"},'
            '{"type":"text","metadata":{},"text":"Sample 2"}]}'
        )

        assert tool_result_json == tool_result_expected

    def test_tool_result_deserialization(self, sample_tool_use):
        # Create sample content
        text_content_block = TextContentBlock(text="Sample 1")
        text_content_block_2 = TextContentBlock(text="Sample 2")

        tool_result_content_block = ToolResultContentBlock(
            tool_use_id=sample_tool_use["tool_use_id"],
            tool_result_content=[text_content_block, text_content_block_2],
        )

        tool_result_json = tool_result_content_block.model_dump_json()

        tool_result_content_block_2 = ToolResultContentBlock.model_validate_json(
            tool_result_json
        )

        assert tool_result_content_block == tool_result_content_block_2
