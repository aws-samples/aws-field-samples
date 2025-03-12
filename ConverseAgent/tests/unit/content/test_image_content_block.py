import pytest

from converseagent.content import ImageContentBlock  # type: ignore


class TestImageContentBlock:
    def test_image_content_block(self, sample_image):
        """
        Test the ImageContentBlock class.
        """
        # Create a ImageContentBlock instance with a sample document
        test_image_content_block = ImageContentBlock(uri=sample_image["uri"])

        assert test_image_content_block.name == sample_image["filename"]
        assert test_image_content_block.extension == sample_image["extension"]
        assert test_image_content_block.filename == sample_image["filename"]
        assert isinstance(test_image_content_block, ImageContentBlock)

    def test_image_content_block_invalid_uri(self):
        """
        Test the ImageContentBlock class with an invalid URI.
        """
        # Test creating a ImageContentBlock instance with an invalid URI
        with pytest.raises(ValueError):
            ImageContentBlock(uri="invalid_uri")

    def test_image_content_block_missing_uri(self):
        """
        Test the ImageContentBlock class with a missing URI.
        """
        # Test creating a ImageContentBlock instance with a missing URI
        with pytest.raises(ValueError):
            ImageContentBlock()

    def test_document_converse_format(self, sample_image):
        """
        Test the converse_format method of the ImageContentBlock class.
        """
        # Create a ImageContentBlock instance with a sample document
        test_image_content_block = ImageContentBlock(uri=sample_image["uri"])

        converse_format = {
            "image": {
                "format": test_image_content_block.extension,
                "source": {"bytes": test_image_content_block.content_bytes},
            }
        }

        # Test the converse_format method
        assert test_image_content_block.format() == converse_format

    def test_content_bytes_only(self, sample_image):
        """
        Test for ensuring filename or name is provided and extension is provided.
        """

        with open(sample_image["uri"][7:], "rb") as f:
            content_bytes = f.read()

        with pytest.raises(ValueError):
            # Test creating a ImageContentBlock instance without a filename or name
            ImageContentBlock(content_bytes=content_bytes)

        with pytest.raises(ValueError):
            # Test creating a ImageContentBlock instance without an extension
            ImageContentBlock(content_bytes=content_bytes)

    def test_serialization(self, sample_image):
        """
        Test the serialization of the ImageContentBlock class.
        """
        # Create a ImageContentBlock instance with a sample document
        test_image_content_block = ImageContentBlock(uri=sample_image["uri"])

        serialized_document = test_image_content_block.model_dump_json()

        test_image_content_block_2 = ImageContentBlock.model_validate_json(
            serialized_document
        )

        # Test the serialization method
        assert test_image_content_block == test_image_content_block_2
