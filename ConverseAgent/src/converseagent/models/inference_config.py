"""Contains model inference config classes."""

from typing import Any, Dict, List

from pydantic import BaseModel, Field


class InferenceConfig(BaseModel):
    """Represents the inference config."""

    max_tokens: int = Field(default=512, description="Max token parameter", ge=0)
    temperature: float = Field(default=0.5, description="Temperature", ge=0.0, le=1.0)
    top_p: float = Field(default=1.0, description="Top P", ge=0.0, le=1.0)
    top_k: int = Field(default=250, description="Top K", ge=0)
    stop_sequences: list[str] = Field(
        description="Stop sequences", default_factory=list
    )

    additonal_inference_config_fields: Dict[str, Any] = Field(
        default={},
        description="Any other inference config fields to pass to the model",
    )