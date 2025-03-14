from typing import Any, Dict, List

from pydantic import BaseModel, Field

from converseagent.content import (
    DocumentContentBlock,
    ImageContentBlock,
    TextContentBlock,
)
from converseagent.memory import BaseMemory
from converseagent.tools.action_group.action_group import (
    ApiInvocationResult,
    FunctionInvocationResult,
)


class BedrockAgentSessionState(BaseModel):
    """Represents the agent session state.

    The session state memory must have complete UserMessage and AssistantMessage turns
    that are used for additional context for the agent. For exmaple,

    It must be composed of:
        UserMessage
        AssistantMessage
        UserMessage
        AssistantMessage
    """

    memory: BaseMemory = Field(
        default_factory=BaseMemory, description="The memory to use with the agent"
    )

    invocation_id: str | None = Field(default=None, description="The invocation id")

    prompt_session_attributes: Dict[str, str] = Field(
        default_factory=dict, description="The prompt session attributes"
    )

    return_control_invocation_results: List[
        ApiInvocationResult | FunctionInvocationResult
    ] = Field(
        default_factory=list, description="The return of control invocation results"
    )

    session_attributes: Dict[str, str] = Field(
        default_factory=dict, description="The session attributes"
    )

    def format(
        self, include_conversation_history: bool = False, include_files: bool = False
    ) -> Dict[str, Any]:
        """Format to boto3 request."""
        session_state_dict: Dict[str, Any] = {}

        # Format conversation history and files
        conversation_history: List[Dict[str, Any]] = []
        files: List[Dict[str, Any]] = []

        for message in self.memory.get_messages():
            # ConversationHistory only accepts text content blocks
            # So we need to remove AttachmentContentBlocks to files instead
            # Filter for text content blocks
            filtered_content_blocks = []

            for content_block in message.content:
                if isinstance(content_block, TextContentBlock):
                    filtered_content_blocks.append(content_block.format())

                if isinstance(content_block, DocumentContentBlock | ImageContentBlock):
                    files.append(
                        {
                            "name": content_block.filename,
                            "source": {
                                "byteContent": {
                                    "data": content_block.content_bytes,
                                    "mediaType": content_block.mime_type,
                                },
                                "sourceType": "BYTE_CONTENT",
                            },
                            "useCase": "CHAT",
                        }
                    )

            conversation_history.append(
                {"role": message.role, "content": filtered_content_blocks}
            )

        if (
            include_conversation_history
            and conversation_history
            and len(self.memory.get_messages()) % 2 == 0
        ):
            session_state_dict["conversationHistory"] = {
                "messages": conversation_history
            }

        if include_files and files:
            session_state_dict["files"] = files

        if self.invocation_id:
            session_state_dict["invocationId"] = self.invocation_id

        if self.prompt_session_attributes:
            session_state_dict["promptSessionAttributes"] = (
                self.prompt_session_attributes
            )

        if self.return_control_invocation_results:
            session_state_dict["returnControlInvocationResults"] = [
                result.to_boto3_format()
                for result in self.return_control_invocation_results
            ]

        if self.session_attributes:
            session_state_dict["sessionAttributes"] = self.session_attributes

        return session_state_dict
