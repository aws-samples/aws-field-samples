from converseagent.models.bedrock import BedrockModel  # type: ignore


class TestBedrockModel:
    """Tests the BedrockModel class"""

    def test_invoke(self, text_model_id):
        """Tests the converse method of the BedrockModel class"""
        model = BedrockModel(bedrock_model_id=text_model_id)

        messages = [{"role": "user", "content": [{"text": "Hi, how are you?"}]}]
        system = [{"text": "You are a helpful AI agent"}]
        inference_config = {"temperature": 0.0}

        response = model.invoke(
            messages=messages, system=system, inference_config=inference_config
        )

        assert response is not None
