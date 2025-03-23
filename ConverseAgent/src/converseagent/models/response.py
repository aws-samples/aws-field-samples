from typing import Dict

from pydantic import BaseModel, Field

from converseagent.messages import AssistantMessage
from converseagent.models.stop_reason import StopReason


class ModelResponse(BaseModel):
    """Represents the standard invocation response that needs to be implemented."""

    assistant_message: AssistantMessage = Field(description="The assistant message")
    stop_reason: StopReason = Field(description="The stop reason")
    request_id: str | None = Field(
        default=None, description="Unique identifier for the request"
    )
    input_tokens: int | None = Field(
        default=None, description="The number of input tokens"
    )
    output_tokens: int | None = Field(
        default=None, description="The number of output tokens"
    )
    total_tokens: int | None = Field(
        default=None, description="The total number of tokens"
    )
    metadata: Dict = Field(
        default_factory=dict,
        description="Additional metadata to be included in the response",
    )