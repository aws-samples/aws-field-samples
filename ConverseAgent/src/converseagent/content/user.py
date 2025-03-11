from typing import Annotated, Union

from pydantic import Field

from converseagent.content.document import DocumentContentBlock
from converseagent.content.image import ImageContentBlock
from converseagent.content.text import TextContentBlock
from converseagent.content.tool import ToolResultContentBlock

UserContentBlock = Annotated[
    Union[
        DocumentContentBlock,
        ImageContentBlock,
        TextContentBlock,
        ToolResultContentBlock,
    ],
    Field(discriminator="type"),
]
