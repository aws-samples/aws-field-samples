# TODO: Currently this delegate tool needs refactoring and testing
# This currently does not work

from typing import List, Literal

from pydantic import Field, model_validator

from converseagent.agents.base.base import BaseAgent
from converseagent.content import TextContentBlock
from converseagent.messages import UserMessage
from converseagent.models.bedrock import BedrockModel
from converseagent.tools.base import BaseTool, BaseToolGroup
from converseagent.tools.tool_response import (
    BaseToolResponse,
    ResponseStatus,
    ResponseType,
)

DELEGATE_PROMPT_TEMPLATE = """
You have been delegated the following task. Ensure that you complete the task.

Your objective is:
<objective>
{objective}
</objective>

Additional context to the task:
<context>
{context}
</context>

"""


class DelegateToolGroup(BaseToolGroup):
    """Enables the delegation of tasks to other agents"""

    name: str = "delegate_tools"
    description: str = "Use this tool to delegate tasks to other agents"
    instructions: str = """
    Use this tool to delegate tasks to other agents. 
    Make sure to provide very detailed objective for the agent to follow.
    """

    simple_model_id: str = Field(
        default="us.anthropic.claude-3-5-haiku-20241022-v1:0",
        description="Model ID to use for simple requsets",
    )
    complex_model_id: str = Field(
        default="us.anthropic.claude-3-5-sonnet-20241022-v2:0",
        description="Model ID to use for complex requsets",
    )

    delegate_agent_tool_groups: List = Field(default_factory=list)

    model_type: Literal["bedrock", "jumpstart"] = Field(default="bedrock")
    sagemaker_endpoint_name: str = Field(default=None)

    @model_validator(mode="after")
    def validate_tools(self):
        """Check if tools are passed, otherwise add tools"""
        if not self.tools:
            self.tools = [
                DelegateTool(
                    simple_model_id=self.simple_model_id,
                    complex_model_id=self.complex_model_id,
                    delegate_agent_tool_groups=self.delegate_agent_tool_groups,
                    model_type=self.model_type,
                    sagemaker_endpoint_name=self.sagemaker_endpoint_name,
                )
            ]
        return self


class DelegateTool(BaseTool):
    """Delegates tasks to other agents"""

    name: str = "delegate_to_agents"
    description: str = """Use this tool to delegate to one or more agents
    by providing each agent a very detailed description of its objective
    including your expectation of the output in the objective.
    The agent will be responsible for completing the task and reporting the result.
    
    Provide the complexity for the task. If it's simple like summarization, input simple.
    If it needs reasoning, multi-step execution, or complex data processing, input complex.
    """

    simple_model_id: str = Field(
        default="us.anthropic.claude-3-5-haiku-20241022-v1:0",
        description="Model ID to use for simple requsets",
    )
    complex_model_id: str = Field(
        default="us.anthropic.claude-3-5-sonnet-20241022-v2:0",
        description="Model ID to use for complex requsets",
    )

    delegate_agent_tool_groups: List = Field(default_factory=list)

    model_type: Literal["bedrock", "jumpstart"] = Field(default="bedrock")
    sagemaker_endpoint_name: str = Field(default=None)
    model: BedrockModel = Field(default=None)

    def invoke(self, delegations: List[dict]) -> BaseToolResponse:
        """Invokes the tool logic

        Args:
            delegations (List[dict]): The list of delegations to be performed

        """
        results = []
        for delegation in delegations:
            result = self.invoke_delegate(
                complexity=delegation["complexity"],
                initial_plan=delegation["initial_plan"],
                objective=delegation["objective"],
                context=delegation["context"],
            )
            results.append(result)

        tool_response = BaseToolResponse(
            status=ResponseStatus.SUCCESS, type=ResponseType.CONTENT, content=results
        )

        return tool_response

    def invoke_delegate(
        self, complexity, initial_plan, objective, context
    ) -> TextContentBlock:
        """Invokes the delegate tool logic

        Args:
            complexity (str): The complexity of the task.
            initial_plan (str): The detailed initial step-by-step plan for the agent to follow
            objective (str): The very detailed objective description for the agent to follow
            context (str): Provide additional detailed context to the agent.

        Returns:
            The response from the agent

        """
        if complexity == "simple":
            bedrock_model_id = self.simple_model_id
        elif complexity == "complex":
            bedrock_model_id = self.complex_model_id
        else:
            return TextContentBlock(
                text="Error: Invalid complexity value. Must provide one of: simple, complex",
            )

        self.model = BedrockModel(bedrock_model_id=bedrock_model_id)

        agent = BaseAgent(model=self.model)
        agent.add_tool_groups(self.delegate_agent_tool_groups)

        prompt = DELEGATE_PROMPT_TEMPLATE.format(objective=objective, context=context)

        user_message = UserMessage(text=prompt)
        try:
            response = agent.invoke(
                user_message=user_message, initial_plan=initial_plan
            )
            return TextContentBlock(text=response["text"])

        except Exception as e:
            return TextContentBlock(text=f"Error: {e}")

    def get_tool_spec(self):
        return {
            "toolSpec": {
                "name": self.name,
                "description": self.description,
                "inputSchema": {
                    "json": {
                        "type": "object",
                        "properties": {
                            "delegations": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "objective": {
                                            "type": "string",
                                            "description": "The very detailed objective description for the agent to follow",
                                        },
                                        "initial_plan": {
                                            "type": "string",
                                            "description": "The detailed initial step-by-step plan for the agent to follow",
                                        },
                                        "context": {
                                            "type": "string",
                                            "description": "Provide additional detailed context to the agent.",
                                        },
                                        "complexity": {
                                            "type": "string",
                                            "description": "The complexity of the task.",
                                            "enum": ["simple", "complex"],
                                        },
                                    },
                                    "required": [
                                        "objective",
                                        "initial_plan",
                                        "context",
                                        "complexity",
                                    ],
                                },
                            }
                        },
                        "required": ["delegations"],
                    }
                },
            }
        }
