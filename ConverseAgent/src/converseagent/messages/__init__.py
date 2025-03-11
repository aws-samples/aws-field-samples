from typing import Annotated, Union

from pydantic import Field

from .assistant import AssistantMessage
from .base import BaseMessage
from .system import SystemMessage
from .user import UserMessage

Message = Annotated[Union[AssistantMessage, UserMessage], Field(discriminator="role")]
