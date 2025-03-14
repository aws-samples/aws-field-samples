"""Tests for prompt_config.py."""

import pytest
from pydantic import ValidationError

from converseagent.agents.bedrock.prompt_config import (
    BedrockModel,
    InferenceConfig,
    ParserMode,
    PromptConfiguration,
    PromptCreationMode,
    PromptOverrideConfiguration,
    PromptState,
    PromptType,
)


class TestPromptConfig:
    """Tests the prompt config class."""

    def test_prompt_configuration(self, text_model_id):
        """Test the to_boto3_format method with all required fields."""
        inference_config = InferenceConfig(
            temperature=0.7, stop_sequences=["stop1", "stop2"]
        )

        prompt_config = PromptConfiguration(
            additional_model_request_fields={"key": "value"},
            base_prompt_template="Test template",
            foundation_model=BedrockModel(bedrock_model_id=text_model_id),
            inference_configuration=inference_config,
            parser_mode=ParserMode.OVERRIDDEN,
            prompt_creation_mode=PromptCreationMode.OVERRIDDEN,
            prompt_state=PromptState.ENABLED,
            prompt_type=PromptType.PRE_PROCESSING,
        )

        result = prompt_config.to_boto3_format()

        assert result == {
            "additionalModelRequestFields": {"key": "value"},
            "basePromptTemplate": "Test template",
            "foundationModel": text_model_id,
            "inferenceConfiguration": {
                "temperature": 0.7,
                "topP": 1.0,
                "topK": 250,
                "maximumLength": 512,
                "stopSequences": ["stop1", "stop2"],
            },
            "parserMode": "OVERRIDDEN",
            "promptCreationMode": "OVERRIDDEN",
            "promptState": "ENABLED",
            "promptType": "PRE_PROCESSING",
        }

    def test_prompt_configuration_missing_required_field(self):
        """Test that initialization fails when required fields are missing."""
        with pytest.raises(ValidationError):
            PromptConfiguration(
                additional_model_request_fields={"key": "value"},
                # Missing other required fields
            )

    def test_prompt_override_configuration(self, text_model_id):
        """Test the to_boto3_format method for PromptOverrideConfiguration."""
        inference_config = InferenceConfig(
            temperature=0.7, stop_sequences=["stop1", "stop2"]
        )

        prompt_config = PromptConfiguration(
            additional_model_request_fields={"key": "value"},
            base_prompt_template="Test template",
            foundation_model=BedrockModel(bedrock_model_id=text_model_id),
            inference_configuration=inference_config,
            parser_mode=ParserMode.OVERRIDDEN,
            prompt_creation_mode=PromptCreationMode.OVERRIDDEN,
            prompt_state=PromptState.ENABLED,
            prompt_type=PromptType.PRE_PROCESSING,
        )

        override_lambda = "arn:aws:lambda:us-west-2:123456789012:function:my-function"
        prompt_override_config = PromptOverrideConfiguration(
            override_lambda=override_lambda, prompt_configurations=[prompt_config]
        )

        result = prompt_override_config.to_boto3_format()

        expected = {
            "overrideLambda": override_lambda,
            "promptConfigurations": [prompt_config.to_boto3_format()],
        }
        assert result == expected
