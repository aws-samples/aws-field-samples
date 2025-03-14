"""Contains the model request classes."""

from typing import Any, Dict, List

from pydantic import BaseModel, Field

from converseagent.messages import Message, SystemMessage
from converseagent.models.inference_config import InferenceConfig
from converseagent.tools.base import BaseTool


class ModelRequest(BaseModel):
    """Represents a standard request to models."""

    messages: List[Message]
    system_message: SystemMessage | None = Field(default=None)
    inference_config: InferenceConfig | None = Field(default=None)
    tools: List[BaseTool] = Field(default_factory=list)
    additional_model_request_fields: Dict[str, Any] = Field(default_factory=dict)
