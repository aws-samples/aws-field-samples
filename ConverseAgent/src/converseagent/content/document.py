from typing import ClassVar, Dict, Literal, Union

from pydantic import computed_field, field_validator

from converseagent.content.base import BaseAttachmentContentBlock
from converseagent.logging_utils.logger_config import setup_logger

logger = setup_logger(__name__)


class DocumentContentBlock(BaseAttachmentContentBlock):
    """Represents an Amazon Bedrock Runtime DocumentBlock

    This content block supports pdf, csv, doc, docx, xls, xlsx, html, txt, and md.

    Attributes:
        type (Literal["document"]): The type identifier for the content block. The
            value is set to "document".

    Example:
        ```
            document_block = DocumentContentBlock(uri="file://path/to/file.pdf")
        ```

    Raises:
        ValueError: If the file extension is not in the supported formats
            (pdf, csv, doc, docx, xls, xlsx, html, txt, md)

    """

    type: Literal["document"] = "document"

    SUPPORTED_EXTENSIONS: ClassVar[set] = {
        "pdf",
        "csv",
        "doc",
        "docx",
        "xls",
        "xlsx",
        "html",
        "txt",
        "md",
    }

    @field_validator("extension")
    def validate_extension(cls, v) -> str:
        """
        Validate the file extension.

        Args:
            v (str): The file extension.

        Returns:
            str: The validated file extension.

        Raises:
            ValueError: If the file extension is not supported.
        """
        if v not in cls.SUPPORTED_EXTENSIONS:
            error_msg = (
                f"File extension '{v}' is not supported. "
                f"Supported extensions are: {', '.join(sorted(cls.SUPPORTED_EXTENSIONS))}"
            )
            logger.error(error_msg)
            raise ValueError(error_msg)

        return v

    def format(self) -> Dict[str, Dict[str, Union[str, Dict[str, bytes]]]]:
        """Formats the document block to Convorse Format


        Returns:
            Dict[str, Dict[str, Union[str, Dict[str, bytes]]]]: A dictionary containing:
                - document: Dict containing format, name, and source information
                    - format: str - The document format/extension
                    - name: str - A unique name for the document
                    - source: Dict containing the image bytes
                        - bytes: bytes - The raw image data
        """

        if isinstance(self.name, str) and isinstance(self.extension, str):
            return {
                "document": {
                    "format": self.extension,
                    "name": self.name,
                    "source": {"bytes": self.content_bytes},
                }
            }
        else:
            raise ValueError("Missing extension for document content block")
