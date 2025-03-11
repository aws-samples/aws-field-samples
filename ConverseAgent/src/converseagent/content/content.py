from typing import Annotated, Union

from pydantic import Field

from converseagent.content.document import DocumentContentBlock
from converseagent.content.image import ImageContentBlock
from converseagent.content.text import TextContentBlock

BasicContentBlock = Annotated[
    Union[
        DocumentContentBlock,
        ImageContentBlock,
        TextContentBlock,
    ],
    Field(discriminator="type"),
]
