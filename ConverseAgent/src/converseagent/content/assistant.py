from typing import Annotated, Union

from pydantic import Field

from converseagent.content.document import DocumentContentBlock
from converseagent.content.image import ImageContentBlock
from converseagent.content.reasoning import ReasoningContentBlock
from converseagent.content.text import TextContentBlock
from converseagent.content.tool import ToolUseContentBlock

AssistantContentBlock = Annotated[
    Union[
        DocumentContentBlock,
        ImageContentBlock,
        TextContentBlock,
        ToolUseContentBlock,
        ReasoningContentBlock,
    ],
    Field(discriminator="type"),
]
