"""Contains Bedrock Agent specific responses."""

from typing import Any, Dict, List

from pydantic import Field

from converseagent.models.response import ModelResponse
from converseagent.tools.action_group.action_group import ReturnControlInvocation


class BedrockAgentModelResponse(ModelResponse):
    """Represents a Bedrock Agent model response."""

    return_control_invocation: ReturnControlInvocation | None = Field(
        default=None, description="Return control invocation"
    )
