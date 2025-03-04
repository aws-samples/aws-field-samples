from abc import abstractmethod
from base64 import b64decode, b64encode
from typing import Dict, Optional

import boto3  # type: ignore
from botocore.exceptions import ClientError  # type: ignore
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    computed_field,
    field_validator,
    model_validator,
)

from converseagent.logging_utils.logger_config import setup_logger

logger = setup_logger(__name__)


class BaseContentBlock(BaseModel):
    """Abstract base class representing a content block.

    This class serves as a base template for all content block types.
    Each subclass must implement the format method.

    Attributes:
        type (str): The type identifier for the content block.

    Example:
        ```
            class TextContentBlock(BaseContentBlock):

            type: Literal["text"] = "text"
            text: str = Field(description="The text content")

            def format(self) -> Dict[str, any]:
                return {"text": self.text}
        ```
    """

    type: str = Field(description="The type of content block")

    @abstractmethod
    def format(self) -> Dict:
        """Formats the content block into a Converse-compatible dictionary.

        The format method should convert the content block's data into
        a format compatible with Amazon Bedrock Runtime. The final format
        output must be supported by Amazon Bedrock Runtime. Refer to the ContentBlock
        specification.

        Returns:
            Dict: A dictionary containing the formatted content block. The structure
                depends on the specific content block type.

        Raises:
            NotImplementedError: If the subclass does not implement this.

        Example:
            ```
            def format(self) -> Dict:
                return {
                    "text": self.text
                }
        """
        raise NotImplementedError("Subclasses must implement this method")


class BaseAttachmentContentBlock(BaseContentBlock):
    """Abstract base class representing attachment content blocks.

    This class represents content blocks such as image, document, and video.
    Each subclass must implement the format method. This content block
    supports loading from a file, Amazon S3, or content bytes passed directly.

    You must provide either a URI or content_bytes.

    Attributes:
        uri (str): The URI of the attachment prefixed by file:// or s3://
        name (str): The name of the attachment. Defaults to filename if not specified
        content_bytes (bytes): The raw bytes content of the attachment
        filename (Optional[str]): The filename extracted from the URI if URI is provided.
        extension (str): The file extension extracted from the filename. If the
            URI is not provided, you must provide the extension.


    Example:
        ```
            class DocumentContentBlock(BaseAttachmentContentBlock):
                type: Literal["document"] = "document"

                def format(self) -> Dict[str, Dict[str, Union[str, Dict[str, bytes]]]]:
                    return {
                        "document": {
                            "format": self.extension,
                            "name": self.name,
                            "source": {"bytes": self.content_bytes},
                        }
                    }
        ```
    Methods:
        validate_uri: Validates that the URI starts with file:// or s3://
        model_post_init: Initializes filename and extension from URI, sets default name,
                        and loads content
    """

    uri: Optional[str] = Field(
        default=None,
        description="The uri of the attachment, it must be prefixed by file:// or s3://",
    )
    name: Optional[str] = Field(default=None, description="Name of the document")
    content_bytes: bytes = Field(
        default=None, description="The raw bytes content of the attachment"
    )
    filename: Optional[str] = Field(default=None, description="The filename")
    extension: Optional[str] = Field(default=None, description="The file extension")

    model_config = ConfigDict(
        json_encoders={bytes: lambda v: b64encode(v).decode("utf-8")},
        arbitrary_types_allowed=True,
    )

    @field_validator("content_bytes", mode="before")
    def decode_bytes(cls, value):
        if isinstance(value, str):
            try:
                return b64decode(value)
            except Exception as e:
                raise ValueError(f"Invalid base64 encoded string: {str(e)}")
        return value

    @model_validator(mode="after")
    def validate_setup(self) -> "BaseAttachmentContentBlock":
        """Validates and sets up the attachment content block based on provided inputs.


        This method handles the logic for three scenarios:
        - URI only
        - Content bytes only
        - Both URI and content bytes

        Returns:
            BaseAttachmentContentBlock: The validated and setup instance

        Raises:
            ValueError: If neither URI nor content_bytes is provided or
                if filename/extension are missing when only content_bytes is provided
        """

        if self.uri is None and self.content_bytes is None:
            raise ValueError("Either URI or content_bytes must be provided")

        # URI only
        if self.uri:
            if not (self.uri.startswith("file://") or self.uri.startswith("s3://")):
                error_msg = "Invalid URI prefix. Must be file:// or s3://"
                logger.error(error_msg)
                raise ValueError(error_msg)

            # Extract filename and extension from URI
            uri_filename = self.uri.split("/")[-1]
            if not self.filename:
                self.filename = uri_filename
            if not self.extension:
                self.extension = uri_filename.split(".")[-1]
                if not self.extension:
                    error_msg = (
                        "Unable to parse extension. Please provide an extension."
                    )
                    logger.error(error_msg)
                    raise ValueError(error_msg)

        # Content bytes only
        elif self.content_bytes and not self.uri:
            # Ensure filename and extension are provided
            if not self.filename or not self.extension:
                raise ValueError(
                    "Filename and extension must be provided when only content_bytes is provided"
                )

        # Set default name if not provided
        if self.name is None:
            self.name = self.filename

        # Load the content if content_bytes is not provided
        if not self.content_bytes:
            self.load_content()

        return self

    def load_content(self):
        """Loads the content of the attachment from the specified URI.

        Supports loading content from local files (file://) or Amazon S3 (s3://)
        The loaded content is stored in the content_bytes attribute.

        For local files:
            - Strips 'file://' prefix and reads the file in binary mode
            - Example: 'file://path/to/file.pdf'

        For Amazon S3:
            - Parses the bucket and key from the URI
            - Example: "s3://bucket-name/path/to/file.pdf'

        Raises:
            FileNotFoundError: When local file doesn't exist
            ValueError: When URI has invalid prefix
            ClientError: When S3 operations fail
            Exception: For other errors

        Example:
            ```
            # Local file
            attachment = Attachment(uri="file://documents/sample.pdf")
            attachment.load_content() # Loads file content into content_bytes

            # S3 file
            attachment = Attachment(uri="s3://my-bucket/sample.pdf")
            attachment.load_content() # Loads file content into content_bytes

        """
        if self.uri.startswith("file://"):
            try:
                with open(self.uri[7:], "rb") as f:
                    self.content_bytes = f.read()
            except FileNotFoundError as e:
                error_msg = f"File {self.uri[7:]} not found"
                logger.error(error_msg)
                raise e
            except Exception as e:
                error_msg = f"Error loading file {self.uri[7:]}: {e}"
                logger.error(error_msg)
                raise e

        elif self.uri.startswith("s3://"):
            client = boto3.client("s3")

            # Download the file from S3 as bytes
            try:
                response = client.get_object(
                    Bucket=self.uri[5:].split("/")[0],
                    Key="/".join(self.uri[5:].split("/")[1:]),
                )
                self.content_bytes = response["Body"].read()
            except ClientError as e:
                error_msg = f"Error downloading file from S3: {e}"
                logger.error(error_msg)
                raise e

        else:
            raise ValueError("Invalid URI prefix. Must be file:// or s3://")
