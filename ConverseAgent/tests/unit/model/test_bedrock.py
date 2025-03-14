"""Tests the Bedrock model."""

from converseagent.messages import SystemMessage, UserMessage
from converseagent.models.bedrock import BedrockModel  # type: ignore
from converseagent.models.inference_config import InferenceConfig
from converseagent.models.request import ModelRequest


class TestBedrockModel:
    """Test the BedrockModel class."""

    def test_invoke(self, text_model_id):
        """Test the converse method of the BedrockModel class."""
        model = BedrockModel(bedrock_model_id=text_model_id)

        user_message = UserMessage(text="Hi, how are you?")
        system_message = SystemMessage(text="You are a helpful AI agent")
        inference_config = InferenceConfig(max_tokens=1024, temperature=0.5)

        model_request = ModelRequest(
            messages=[user_message],
            system_message=system_message,
            inference_config=inference_config,
        )

        response = model.invoke(model_request)

        assert response is not None
