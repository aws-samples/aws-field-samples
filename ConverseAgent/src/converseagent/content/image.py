from typing import ClassVar, Dict, Literal, Union

from pydantic import field_validator

from converseagent.content.base import BaseAttachmentContentBlock
from converseagent.logging_utils.logger_config import setup_logger

logger = setup_logger(__name__)


class ImageContentBlock(BaseAttachmentContentBlock):
    """Represents an Amazon Bedrock Runtime ImageBlock

    This content block supports png, jpeg, gif, and webp.

    Attributes:
        type(Literal["image"]): The type identifier for the content block. The
            value is set to "image".

    Example:
        ```
            image_block = ImageContentBlock(uri="file://path/to/image.png")
        ```

    Raises:
        ValueError: If the file extension is not in the supported formats
            (png, jpeg, gif, webp)
    """

    type: Literal["image"] = "image"

    SUPPORTED_EXTENSIONS: ClassVar[set] = {"png", "jpeg", "jpg", "gif", "webp"}

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
        """Format the image content block to converse format.

        Returns:
            Dict[str, Dict[str, Union[str, Dict[str, bytes]]]]: A dictionary containing:
                - image: Dict containing format and source information
                    - format: str - The image format/extension
                    - source: Dict containing the image bytes
                        - bytes: bytes - The raw image data

        Raises:
            ValueError: If the extension is not set for the document content block
        """
        if isinstance(self.extension, str):
            if self.extension.lower() == "jpg":
                self.extension = "jpeg"

            return {
                "image": {
                    "format": self.extension,
                    "source": {"bytes": self.content_bytes},
                }
            }
        else:
            raise ValueError("Missing extension for document content block")
