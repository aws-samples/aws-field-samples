from typing import Annotated, Dict, List, Union

from pydantic import BaseModel, Field, model_validator

from converseagent.messages import AssistantMessage, UserMessage
from converseagent.models.response import ModelResponse

Message = Annotated[Union[UserMessage, AssistantMessage], Field(discriminator="role")]


class BaseInvocationLog(BaseModel):
    """A class that represents a single invocation to Converse"""

    response: ModelResponse | None = Field(
        default=None,
        description="The Converse API response. If provided, it will \
            automatically be parsed",
    )

    request_id: str | None = Field(
        default=None, description="The invocation request id"
    )
    input_messages: List[Message] | None = Field(
        default_factory=list, description="The list of messages used in the invocation"
    )
    output_message: AssistantMessage | None = Field(
        default=None, description="The output assistant message"
    )
    input_tokens: int | None = Field(default=None, description="Number of input tokens")
    output_tokens: int | None = Field(
        default=None, description="Number of output tokens"
    )
    total_tokens: int | None = Field(default=None, description="Number of total tokens")
    update_message: str | None = Field(
        default=None, description="An update message from the agent"
    )
    thinking: str | None = Field(default=None, description="The thinking of the agent")
    final_response: str | None = Field(
        default=None, description="The final response of the agent"
    )
    current_plan: str | None = Field(
        default=None, description="The current plan of the agent"
    )

    @model_validator(mode="after")
    def parse_response(self):
        if self.response:
            assistant_message = self.response.assistant_message

            self.request_id = (
                self.response.request_id
                if self.response.request_id is not None
                else None
            )
            self.output_message = assistant_message
            self.input_tokens = self.response.input_tokens
            self.output_tokens = self.response.output_tokens
            self.total_tokens = self.response.total_tokens
            self.update_message = assistant_message.update_message
            self.current_plan = assistant_message.current_plan
            self.thinking = assistant_message.thinking
            self.final_response = assistant_message.final_response

        return self


class BaseInvocationHistory(BaseModel):
    """
    Tracks and manages the invocation history for agents.
    """

    history: List[BaseInvocationLog] = Field(
        default_factory=list, description="A list of invocation logs"
    )

    def append(self, log: BaseInvocationLog) -> None:
        """
        Appends the invocation history to the history list.

        Args:
            log (BaseInvocationLog): A BaseInvocationLog object
        """
        self.history.append(log)

    def get_history(self) -> List[BaseInvocationLog]:
        """
        Returns the invocation history.

        Returns:
            list: The invocation history.
        """
        return self.history

    def get_cumulative_token_count(self) -> Dict[str, int]:
        """
        Calculates the total token usage based on the invocation history.

        Returns:
            dict: A dictionary of the total token counts
        """
        total_input_tokens = 0
        total_output_tokens = 0

        for invocation in self.history:
            total_input_tokens += invocation.input_tokens
            total_output_tokens += invocation.output_tokens

        return {
            "total_input_tokens": total_input_tokens,
            "total_output_tokens": total_output_tokens,
            "total_tokens": total_input_tokens + total_output_tokens,
        }
