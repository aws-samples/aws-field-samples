"""Contains Amazon Bedrock Agents prompt override configuration classes."""

from enum import Enum
from typing import Any, Dict, List

from pydantic import BaseModel, Field

from converseagent.models.bedrock import BedrockModel
from converseagent.models.inference_config import InferenceConfig


class ParserMode(str, Enum):
    """Represents the parser mode for Amazon Bedrock Agents."""

    DEFAULT = "DEFAULT"
    OVERRIDDEN = "OVERRIDDEN"


class PromptCreationMode(str, Enum):
    """Represents the prompt creation mode for Amazon Bedrock Agents."""

    DEFAULT = "DEFAULT"
    OVERRIDDEN = "OVERRIDDEN"


class PromptState(str, Enum):
    """Represents the prompt state for Amazon Bedrock Agents."""

    ENABLED = "ENABLED"
    DISABLED = "DISABLED"


class PromptType(str, Enum):
    """Represents the prompt type for Amazon Bedrock Agents."""

    PRE_PROCESSING = "PRE_PROCESSING"
    ORCHESTRATION = "ORCHESTRATION"
    KNOWLEDGE_BASE_RESPONSE_GENERATION = "KNOWLEDGE_BASE_RESPONSE_GENERATION"
    POST_PROCESSING = "POST_PROCESSING"
    ROUTING_CLASSIFIER = "ROUTING_CLASSIFIER"


class PromptConfiguration(BaseModel):
    """Represents a prompt configuration for Amazon Bedrock Agents."""

    additional_model_request_fields: Dict[str, Any] = Field(
        default_factory=dict,
        description="The additional model request fields to use for prompt override.",
    )

    base_prompt_template: str = Field(
        description="The base prompt template to use for prompt override.",
    )

    foundation_model: BedrockModel = Field(
        description="The foundation model id to use for prompt override.",
    )

    inference_configuration: InferenceConfig = Field(
        description="The inference configuration to use for prompt override.",
    )

    parser_mode: ParserMode = Field(
        default=ParserMode.DEFAULT,
        description="The parser mode to use for prompt override.",
    )

    prompt_creation_mode: PromptCreationMode = Field(
        default=PromptCreationMode.DEFAULT,
        description="The prompt creation mode to use for prompt override.",
    )

    prompt_state: PromptState = Field(
        default=PromptState.ENABLED,
        description="The prompt state to use for prompt override.",
    )

    prompt_type: PromptType = Field(
        description="The prompt type to use for prompt override.",
    )

    def to_boto3_format(self):
        """Format to Boto3 request dict."""
        formatted_dict = {
            "additionalModelRequestFields": self.additional_model_request_fields,
            "basePromptTemplate": self.base_prompt_template,
            "foundationModel": self.foundation_model.bedrock_model_id,
            "inferenceConfiguration": {
                "maximumLength": self.inference_configuration.max_tokens,
                "temperature": self.inference_configuration.temperature,
                "topP": self.inference_configuration.top_p,
                "topK": self.inference_configuration.top_k,
                "stopSequences": self.inference_configuration.stop_sequences,
            },
            "parserMode": self.parser_mode.value,
            "promptCreationMode": self.prompt_creation_mode.value,
            "promptState": self.prompt_state.value,
            "promptType": self.prompt_type.value,
        }
        return formatted_dict


class PromptOverrideConfiguration(BaseModel):
    """Represents the prompt override configuration for Amazon Bedrock."""

    override_lambda: str | None = Field(
        default=None,
        description="The ARN of the Lambda function to use for prompt override.",
    )
    prompt_configurations: List[PromptConfiguration] = Field(
        default_factory=list,
        description="The prompt configurations to use for prompt override.",
    )

    def to_boto3_format(self):
        """Format to Boto3 request dict."""
        formatted_dict = {
            "promptConfigurations": [
                prompt_configuration.to_boto3_format()
                for prompt_configuration in self.prompt_configurations
            ]
        }

        if self.override_lambda:
            formatted_dict["overrideLambda"] = self.override_lambda

        return formatted_dict
