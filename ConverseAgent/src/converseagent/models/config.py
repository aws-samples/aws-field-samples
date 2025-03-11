from typing import Any, Dict

from pydantic import BaseModel, Field


class InferenceConfig(BaseModel):
    """Represents the inference config"""

    max_tokens: int = Field(description="Max token parameter", ge=0)
    temperature: float = Field(description="Temperature", ge=0.0, le=1.0)

    additonal_inference_config_fields: Dict[str, Any] = Field(
        default={},
        description="Any other inference config fields to pass to the model",
    )
