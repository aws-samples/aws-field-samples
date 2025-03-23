"""Contains tests for Bedrock inline agents."""

from converseagent.agents.bedrock.inline_agent import (
    BedrockInlineAgent,
    CollaborationMode,
    CollaboratorConfig,
)
from converseagent.messages import SystemMessage, UserMessage
from converseagent.models.bedrock import BedrockModel


class TestInlineAgent:
    """Tests Inline Agent."""

    def test_output_format(self, text_model_id):
        """Test the output format of the inline agent."""
        model = BedrockModel(bedrock_model_id=text_model_id)
        agent = BedrockInlineAgent(model=model)

        formatted_dict = agent.to_boto3_format()

        assert formatted_dict is not None  # TODO: need to properly compare

    def test_multi_agent_collaboration_supervisor(self, text_model_id):
        """Test a supervisor multi-agent collaboration."""
        model = BedrockModel(bedrock_model_id=text_model_id)

        super_system_message = SystemMessage(
            text="You work with other agents. You must work with other agents to fulfill requests."
        )

        collaborator_name = "ai-fact-agent"
        collab_system_message = SystemMessage(
            text="You are an expert on AI facts and will respond in a concise manner."
        )
        collab_config = CollaboratorConfig(
            instruction="This agent is specialized in AI facts.",
            name=collaborator_name,
        )

        supervisor = BedrockInlineAgent(
            model=model, system_message=super_system_message
        )
        collaborator = BedrockInlineAgent(
            name=collaborator_name, model=model, system_message=collab_system_message
        )

        supervisor.add_collaborator(collaborator, collab_config)
        supervisor.set_collaboration_mode(mode=CollaborationMode.SUPERVISOR)

        prompt = "Write a 10 word story about an AI agent."
        user_message = UserMessage(text=prompt)

        response = supervisor.invoke(
            user_message=user_message,
        )

        assert response is not None  # TODO: need to propery compare
