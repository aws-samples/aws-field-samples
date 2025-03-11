from enum import Enum
from typing import List

from converseagent.content import (
    DocumentContentBlock,
    ImageContentBlock,
    TextContentBlock,
)
from converseagent.content.content import BasicContentBlock


class ResponseStatus(Enum):
    SUCCESS = "SUCCESS"
    ERROR = "ERROR"


class ResponseType(Enum):
    CONTENT = "content"


class BaseToolResponse:
    def __init__(
        self,
        status: ResponseStatus,
        type: ResponseType,
        content=None,
        metadata: dict = {},
    ):
        """
        Initializes the tool response

        Args:
            status (ResponseStatus): The status of the tool response
            type (ResponseType): The type of the tool response
            content (Optional[List[Dict]]): The content of the tool response.
                Defaults to None.
        """
        self.status: ResponseStatus = status
        self.type: ResponseType = type
        self.content: List[BasicContentBlock] = []
        if content:
            self.content = content

    def get_status(self) -> ResponseStatus:
        """Returns the status"""
        return self.status

    def get_type(self) -> ResponseType:
        """Returns the type"""
        return self.type

    def get_content(self) -> List[BasicContentBlock]:
        """Returns the content"""
        return self.content

    def append_content(self, content) -> None:
        """Appends content to the content list

        Args:
            content (BasicContentBlock): The content to append
        """
        self.content.append(content)


class TextToolResponse(BaseToolResponse):
    """Tool response for text responses"""

    def __init__(self, status: ResponseStatus, text: str, metadata: dict = {}):
        """Initializes the TextToolResponse object

        Args:
            status (ResponseStatus): A ResponseType enum value
            text (str): The text value
        """
        super().__init__(status, type=ResponseType.CONTENT)

        self.append_content(TextContentBlock(text=text, metadata=metadata))


class DocumentToolResponse(BaseToolResponse):
    """Tool response for document responses"""

    def __init__(self, status: ResponseStatus, uri: str, metadata: dict = {}):
        """Initializes the DocumentToolResponse

        Args:
            status (ResponseStatus): A ResponseType enum value
            uri (str): The uri of the document. Must start with
                s3:// or file://
        """

        super().__init__(status, type=ResponseType.CONTENT)

        self.append_content(DocumentContentBlock(uri=uri, metadata=metadata))


class ImageToolResponse(BaseToolResponse):
    """Tool response for image responses"""

    def __init__(self, status: ResponseStatus, uri: str, metadata: dict = {}):
        """Initializes the ImageToolResponse

        Args:
            status (ResponseStatus): A ResponseType enum value
            uri (str) The uri of the image. Must start with
                s3:// or file://
        """

        super().__init__(status, type=ResponseType.CONTENT)

        self.append_content(ImageContentBlock(uri=uri, metadata=metadata))


class NotFoundToolResponse(TextToolResponse):
    """Tool response for when a tool is not found"""

    def __init__(self):
        super().__init__(ResponseStatus.ERROR, "Error: Tool not found.")
