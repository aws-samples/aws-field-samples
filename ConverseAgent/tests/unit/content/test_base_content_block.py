from typing import Dict

from converseagent.content.base import (  # type: ignore
    BaseAttachmentContentBlock,
    BaseContentBlock,
)


class TestBaseContentBlock:
    def test_inheritance(self):
        class TestContentBlock(BaseContentBlock):
            def format(self) -> Dict:
                return {"text": "test"}

        test_content_block = TestContentBlock(type="test")
        assert isinstance(test_content_block, BaseContentBlock)

    def test_format_return_type(self):
        class TestContentBlock(BaseContentBlock):
            def format(self) -> Dict:
                return {"text": "test"}

        test_content_block = TestContentBlock(type="test")
        assert isinstance(test_content_block.format(), Dict)


class TestBaseAttachmentContentBlock:
    def test_inheritance(self, sample_image):
        class TestAttachmentContentBlock(BaseAttachmentContentBlock):
            def format(self) -> Dict:
                return {"text": "test"}

        test_attachment_content_block = TestAttachmentContentBlock(
            type="test", uri=sample_image["uri"]
        )

        assert isinstance(test_attachment_content_block, BaseAttachmentContentBlock)

    def test_format_return_type(self, sample_image):
        class TestAttachmentContentBlock(BaseAttachmentContentBlock):
            def format(self) -> Dict:
                return {"text": "test"}

        test_attachment_content_block = TestAttachmentContentBlock(
            type="test", uri=sample_image["uri"]
        )
        assert isinstance(test_attachment_content_block.format(), Dict)

    def test_content(self, sample_image):
        class TestAttachmentContentBlock(BaseAttachmentContentBlock):
            def format(self) -> Dict:
                return {"text": "test"}

        test_attachment_content_block = TestAttachmentContentBlock(
            type="test", uri=sample_image["uri"]
        )

        assert test_attachment_content_block.filename == sample_image["filename"]
        assert test_attachment_content_block.extension == sample_image["extension"]
        assert isinstance(test_attachment_content_block.content_bytes, bytes)
