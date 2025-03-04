from enum import Enum
from typing import Dict, List, Optional

from converseagent.content import (
    DocumentContentBlock,
    ImageContentBlock,
    TextContentBlock,
)


class ResponseStatus(Enum):
    SUCCESS = "SUCCESS"
    ERROR = "ERROR"


class ResponseType(Enum):
    CONTENT = "content"


class BaseToolResponse:
    def __init__(self, status: ResponseStatus, type: ResponseType, content=None):
        """
        Initializes the tool response

        Args:
            status (ResponseStatus): The status of the tool response
            type (RespnoseType): The type of the tool response
            content (Optional[List[Dict]]): The content of the tool response.
                Defaults to None.
        """
        self.status = status
        self.type = type
        self.content = []
        if content:
            self.content = content

    def get_status(self):
        return self.status

    def get_type(self):
        return self.type

    def get_content(self):
        return self.content

    def append_content(self, content):
        self.content.append(content)


class TextToolResponse(BaseToolResponse):
    """Tool response for text responses"""

    def __init__(self, status: ResponseStatus, text: str):
        """Initializes the TextToolResponse object

        Args:
            status (ResponseStatus): A ResponseType enum value
            text (str): The text value
        """
        super().__init__(status, type=ResponseType.CONTENT)

        self.append_content(TextContentBlock(text=text))


class DocumentToolResponse(BaseToolResponse):
    """Tool response for document responses"""

    def __init__(self, status: ResponseStatus, uri: str):
        """Initializes the DocumentToolResponse

        Args:
            status (ResponseStatus): A ResponseType enum value
            uri (str): The uri of the document. Must start with
                s3:// or file://
        """

        super().__init__(status, type=ResponseType.CONTENT)

        self.append_content(DocumentContentBlock(uri=uri))


class ImageToolResponse(BaseToolResponse):
    """Tool response for image responses"""

    def __init__(self, status: ResponseStatus, uri: str):
        """Initializes the ImageToolResponse

        Args:
            status (ResponseStatus): A ResponseType enum value
            uri (str) The uri of the image. Must start with
                s3:// or file://
        """

        super().__init__(status, type=ResponseType.CONTENT)

        self.append_content(ImageContentBlock(uri=uri))


class NotFoundToolResponse(TextToolResponse):
    def __init__(self):
        super().__init__(ResponseStatus.ERROR, "Error: Tool not found.")
