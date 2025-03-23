from converseagent.content import TextContentBlock  # type: ignore


class TestTextContentBlock:
    def test_text_content_block(self, sample_text):
        """Tests the TextContentBlock class
        """
        test_text_content_Block = TextContentBlock(text=sample_text["text"])

        assert isinstance(test_text_content_Block, TextContentBlock)

    def test_text_converse_format(self, sample_text):
        """Test the converse_format method of the TextDocumentBlock
        """
        test_text_content_block = TextContentBlock(text=sample_text["text"])

        converse_format = {"text": test_text_content_block.text}

        assert test_text_content_block.format() == converse_format
