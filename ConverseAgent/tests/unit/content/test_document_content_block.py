import pytest

from converseagent.content.document import DocumentContentBlock  # type: ignore


class TestDocumentContentBlock:
    def test_document_content_block(self, sample_pdf):
        """
        Test the DocumentContentBlock class.
        """
        # Create a DocumentContentBlock instance with a sample document
        test_document_content_block = DocumentContentBlock(uri=sample_pdf["uri"])

        assert test_document_content_block.name == sample_pdf["filename"]
        assert test_document_content_block.extension == sample_pdf["extension"]
        assert test_document_content_block.filename == sample_pdf["filename"]
        assert isinstance(test_document_content_block, DocumentContentBlock)

    def test_document_content_block_invalid_uri(self):
        """
        Test the DocumentContentBlock class with an invalid URI.
        """
        # Test creating a DocumentContentBlock instance with an invalid URI
        with pytest.raises(ValueError):
            DocumentContentBlock(uri="invalid_uri")

    def test_document_content_block_missing_uri(self):
        """
        Test the DocumentContentBlock class with a missing URI.
        """
        # Test creating a DocumentContentBlock instance with a missing URI
        with pytest.raises(ValueError):
            DocumentContentBlock()

    def test_document_converse_format(self, sample_pdf):
        """
        Test the converse_format method of the DocumentContentBlock class.
        """
        # Create a DocumentContentBlock instance with a sample document
        test_document_content_block = DocumentContentBlock(
            uri=sample_pdf["uri"], name="doc1"
        )

        converse_format = {
            "document": {
                "format": test_document_content_block.extension,
                "name": test_document_content_block.name,
                "source": {"bytes": test_document_content_block.content_bytes},
            }
        }

        # Test the converse_format method
        assert test_document_content_block.format() == converse_format

    def test_content_bytes_only(self, sample_pdf):
        """
        Test for ensuring filename or name is provided and extension is provided.
        """

        with open(sample_pdf["uri"][7:], "rb") as f:
            content_bytes = f.read()

        with pytest.raises(ValueError):
            # Test creating a DocumentContentBlock instance without a filename or name
            DocumentContentBlock(content_bytes=content_bytes)

        with pytest.raises(ValueError):
            # Test creating a DocumentContentBlock instance without an extension
            DocumentContentBlock(content_bytes=content_bytes, name="doc1")

    def test_serialization(self, sample_pdf):
        """
        Test the serialization of the DocumentContentBlock class.
        """
        # Create a DocumentContentBlock instance with a sample document
        test_document_content_block = DocumentContentBlock(
            uri=sample_pdf["uri"], name="doc1"
        )

        serialized_document = test_document_content_block.model_dump_json()

        test_document_content_block_2 = DocumentContentBlock.model_validate_json(
            serialized_document
        )

        # Test the serialization method
        assert test_document_content_block == test_document_content_block_2
