"""Implementation of Bedrock Inline Agent."""

import random
import string
from enum import Enum
from typing import Any, Callable, Dict, List, Literal, cast
from uuid import uuid4
import uuid
import json

import boto3  # type: ignore
from pydantic import BaseModel, Field

from converseagent.agents.bedrock.session_state import BedrockAgentSessionState
from converseagent.guardrails.bedrock.bedrock_guardrails import GuardrailConfiguration
from converseagent.agents.bedrock.base_prompts import DEFAULT_SYSTEM_MESSAGE
from converseagent.explainability.invocation_history import (
    BaseInvocationHistory,
    BaseInvocationLog,
)
from converseagent.knowledge_base.bedrock.bedrock_knowledge_base import (
    BedrockKnowledgeBase,
)
from converseagent.logging_utils.logger_config import set_logging_level, setup_logger
from converseagent.memory_store import BaseMemoryStore
from converseagent.messages import AssistantMessage, Message, SystemMessage, UserMessage
from converseagent.models.bedrock import BedrockModel
from converseagent.models.bedrock.response import BedrockAgentModelResponse
from converseagent.models.stop_reason import StopReason
from converseagent.tools.action_group import ActionGroup
from converseagent.tools.action_group.action_group import (
    ReturnControlInvocation,
    FunctionInvocationInput,
    FunctionInvocationResult,
    InvocationResponseBody,
    InputParam,
    FunctionSchema,
    ApiInvocationInput,
    ApiSchema,
    ApiInvocationResult,
)
from converseagent.guardrails.bedrock.bedrock_guardrails import GuardrailConfiguration
from .session_state import BedrockAgentSessionState
from .prompt_config import PromptOverrideConfiguration


logger = setup_logger(__name__)


class HandleStopResult(str, Enum):
    """Stop result enum."""

    CONTINUE = "continue"
    END_TURN = "end_turn"
    ERROR = "error"


class CollaborationMode(str, Enum):
    """Collaboration mode enum."""

    SUPERVISOR = "SUPERVISOR"
    SUPERVISOR_ROUTER = "SUPERVISOR_ROUTER"
    DISABLED = "DISABLED"


class BedrockModelConfiguration(BaseModel):
    """Represents the configuration for a Bedrock model."""

    performance_config: Literal["standard", "optimized"] = Field(
        default="standard",
        description="Performance configuraiton of the model either standard or optimized",
    )

    def to_boto3_format(self):
        """Format to Boto3 request."""
        return {"performanceConfig": {"latency": self.performance_config}}


class CollaboratorConfig(BaseModel):
    """Represents a collaborator agent."""

    agent_alias_arn: str | None = Field(
        default=None,
        description="The alias ARN of the collaborator agent",
    )

    instruction: str = Field(
        description="The instruction for using the collaborator agent"
    )

    name: str = Field(
        description="The name of the collaborator agent",
    )

    relay_conversation_history: Literal["TO_COLLABORATOR", "DISABLED"] = Field(
        default="DISABLED",
        description="Whether to relay the conversation history to the collaborator agent",
    )

    def to_boto3_format(self):
        """Format to Boto3 request."""
        config_dict = {
            "collaboratorInstruction": self.instruction,
            "collaboratorName": self.name,
            "relayConversationHistory": self.relay_conversation_history,
        }

        if self.agent_alias_arn:
            config_dict["agentAliasArn"] = self.agent_alias_arn

        return config_dict


class StopResult(BaseModel):
    """Represents the handle_stop_reason result."""

    status: HandleStopResult = Field(
        description="The result of handling the stop reason."
    )
    body: Dict[str, Any] = Field(description="The body of the response.")

    def to_response_dict(self):
        """Format to a dictionary."""
        return {
            "status": self.status.value,
            "body": self.body,
        }


class BedrockInlineAgent(BaseModel):
    """Represents a Bedrock Inline Agent."""

    model: BedrockModel = Field(
        description="The model for the agent",
    )

    session_id: str | None = Field(
        default=str(uuid4()), description="A unique session id for the memory"
    )

    session_state: BedrockAgentSessionState = Field(
        default=BedrockAgentSessionState(),
        description="The session state for the agent",
    )

    memory_store: BaseMemoryStore = Field(
        default_factory=BaseMemoryStore,
        description="The memory store to use with the agent",
    )

    bedrock_model_configuration: BedrockModelConfiguration = Field(
        default=BedrockModelConfiguration(),
        description="The configuration for the Bedrock model",
    )

    invocation_history: BaseInvocationHistory = Field(
        default_factory=BaseInvocationHistory,
        description="The invocation history to use with the agent.",
    )

    name: str = Field(
        default="agent-"
        + "".join(random.choices(string.ascii_lowercase + string.digits, k=5)),
        description="A unique name for the agent. \
                If not specified, a randomly generated name will be created.",
    )

    system_message: SystemMessage = Field(
        default=DEFAULT_SYSTEM_MESSAGE,
        description="The system message for the agent.",
    )

    action_groups: List[ActionGroup] = Field(
        default_factory=list, description="The action groups this agent has access to"
    )

    knowledge_bases: List[BedrockKnowledgeBase] = Field(
        default_factory=list, description="The knowledge bases this agent has access to"
    )

    update_callback: Callable | None = Field(
        default=None,
        description="A callback function to update the UI. Defaults to None.",
    )

    collaboration_mode: CollaborationMode = Field(
        default=CollaborationMode.DISABLED,
        description="Collaboration mode of the agent",
    )

    collaborator_configurations: List[CollaboratorConfig] = Field(
        default_factory=list, description="The collaborator configurations"
    )

    collaborators: List["BedrockInlineAgent"] = Field(
        default_factory=list, description="The collaborators"
    )

    prompt_override_configuration: PromptOverrideConfiguration | None = Field(
        default=None, description="The prompt override configuration"
    )

    customer_encryption_key_arn: str | None = Field(
        default=None,
        description="The ARN of the customer encryption key",
    )

    enable_trace: bool = Field(
        default=True,
        description="Whether to enable trace for the agent",
    )

    idle_session_ttl_in_seconds: int = Field(
        default=300,
        description="The idle session TTL in seconds",
    )

    guardrail_configuration: GuardrailConfiguration | None = Field(
        default=None,
        description="The guardrail configuration for the agent",
    )

    apply_guardrail_interval: int | None = Field(
        default=None, description="The interval for applying the guardrail"
    )

    client: boto3.Session.client = Field(
        default=boto3.client("bedrock-agent-runtime"),
        description="The Bedrock Agent client",
    )

    model_config = {"arbitrary_types_allowed": True}

    def invoke(
        self,
        user_message: UserMessage | str,
        system_message: SystemMessage | str = DEFAULT_SYSTEM_MESSAGE,
        action_groups: List[ActionGroup] = [],
        include_conversation_history: bool = False,
        include_files: bool = True,
        end_session: bool = False,
        # stream_response: bool = False, # TODO: Need to implement this
        knowledge_bases: List[BedrockKnowledgeBase] = [],
        prompt_override_configuration: PromptOverrideConfiguration | None = None,
        verbose: bool = False,
        max_iterations: int = 10,
    ) -> Dict[str, Any]:
        """Invoke the agent.

        user_message (UserMessage): The UserMessage
        system_message (SystemMessage | str): The SystemMessage to use. If providing
            a string, a SystemMessage is created for you. If not provided, the
            default system message is used.
        action_groups (List[ActionGroup]): The action groups of the agent
        include_conversation_history (bool): If set to True, the conversation history
            is included in the request. Defaults to False.
        include_files (bool): If set to True, files are included in the request. Defaults
            to True.
        end_session (bool): If set to True, the session is ended. Defaults to False.
        knowledge_bases (List[KnowledgeBase] | None): The knowledge bases the agent has access to.
        prompt_override_configuration (PromptOverrideConfiguration):
            The prompt override configuration
        verbose (bool): If set to True, logging level is INFO otherwise ERROR
        max_iterations (int): The maximum number of agent interations
        """
        # Set logging level
        set_logging_level(verbose=verbose)

        # Print session id
        logger.info(f"Session ID: {self.session_id}")

        # For convenience, convert string input to UserMessage
        if isinstance(user_message, str):
            user_message = UserMessage(text=user_message)

        if isinstance(system_message, str):
            system_message = SystemMessage(text=system_message)

        # Set the agent system message
        self.system_message = system_message

        # Append the provided UserMessage to the memory
        self._append_memory(message=user_message)

        # Set action groups
        self.action_groups = action_groups

        ### Build the model request
        model_request: Dict[str, Any] = {}

        model_request["sessionId"] = self.session_id
        model_request["inputText"] = user_message.get_text()
        model_request["foundationModel"] = self.model.bedrock_model_id
        model_request["instruction"] = self.system_message.get_text()

        # TODO: need to implement
        # if stream_response:
        #     model_request["streamResponse"] = stream_response

        if action_groups:
            model_request["actionGroups"] = [
                action_group.to_boto3_format() for action_group in action_groups
            ]

        model_request["agentCollaboration"] = self.collaboration_mode
        model_request["bedrockModelConfigurations"] = (
            self.bedrock_model_configuration.to_boto3_format()
        )

        # If multi-agent collaboration is enabled
        if self.collaboration_mode != "DISABLED":
            model_request["agentCollaboration"] = self.collaboration_mode

            if self.collaborator_configurations:
                model_request["collaboratorConfigurations"] = [
                    collaborator_config.to_boto3_format()
                    for collaborator_config in self.collaborator_configurations
                ]
            else:
                raise ValueError(
                    "Collaborator configurations must be provided if collaboration mode is not disabled"
                )

            if self.collaborators:
                model_request["collaborators"] = [
                    collaborator.to_boto3_format()
                    for collaborator in self.collaborators
                ]

        if self.customer_encryption_key_arn:
            model_request["customerEncryptionKeyArn"] = self.customer_encryption_key_arn

        if self.enable_trace:
            model_request["enableTrace"] = self.enable_trace

        if end_session:
            model_request["endSession"] = end_session

        if self.guardrail_configuration:
            model_request["guardrailConfiguration"] = (
                self.guardrail_configuration.to_boto3_format()
            )

        if self.idle_session_ttl_in_seconds:
            model_request["idleSessionTTLInSeconds"] = self.idle_session_ttl_in_seconds

        if knowledge_bases:
            model_request["knowledgeBases"] = [
                knowledge_base.to_boto3_format() for knowledge_base in knowledge_bases
            ]

        if prompt_override_configuration:
            model_request["promptOverrideConfiguration"] = (
                prompt_override_configuration.to_boto3_format()
            )

        if self.apply_guardrail_interval:
            model_request["applyGuardrailInterval"] = self.apply_guardrail_interval

        ### Completed model request build
        current_iteration = 0

        while current_iteration < max_iterations:
            # Update the session state
            if self.session_state:
                # If inline session state for conversation history is provided,
                # It must include complete User and Assistant turns
                model_request["inlineSessionState"] = self.session_state.format(
                    include_conversation_history=include_conversation_history,
                    include_files=include_files,
                )

            # Model Invocation
            model_response: BedrockAgentModelResponse = self._invoke_model(
                model_request
            )

            # Update the invocation log
            self._update_invocation_log(model_response=model_response)

            # Append the assistant message to the memory
            if model_response.assistant_message.text != "":
                self._append_memory(model_response.assistant_message)

            # Stop reason handling
            stop_result = self._handle_stop_reason(model_response=model_response)

            # Return if END_TURN or continue otherwise
            if stop_result.status == HandleStopResult.END_TURN:
                logger.info("Agent completed turn.")

                logger.info("Cleaning up session state")
                # Clean up session state
                self.session_state.return_control_invocation_results = []
                self.session_state.invocation_id = None

                break

            elif stop_result.status == HandleStopResult.CONTINUE:
                logger.info("Completed iteration. Continuing...")
                current_iteration += 1
                self.session_state.return_control_invocation_results = stop_result.body[
                    "invocation_results"
                ]

        return stop_result.to_response_dict()

    def _invoke_model(self, model_request: Dict[str, Any]) -> BedrockAgentModelResponse:
        """Invoke the model with the request."""
        response = self.client.invoke_inline_agent(**model_request)

        return self._parse_model_response(response)

    def _parse_model_response(self, response: Dict) -> BedrockAgentModelResponse:
        """Parse the response from the agent."""
        traces: List[Dict[str, Any]] = []
        texts: List[str] = []

        # Default stop_reason
        stop_reason = StopReason.END_TURN

        # Parse the completion response
        chunks = response["completion"]

        return_control_invocation = None

        for chunk in chunks:
            if "trace" in chunk:
                # print(f"Trace: {chunk['trace']}")
                traces.append(chunk["trace"])

            if "chunk" in chunk:
                # print(f"Chunk: {chunk['chunk']['bytes']}")
                texts.append(chunk["chunk"]["bytes"].decode("utf-8"))

            if "returnControl" in chunk:
                # Update the session state invocation_id for return of control
                invocation_id = chunk["returnControl"]["invocationId"]
                self.session_state.invocation_id = invocation_id
                invocation_inputs: List[
                    ApiInvocationInput | FunctionInvocationInput
                ] = []

                # Loop through the invocation inputs - can be function or api input
                for invocation_input in chunk["returnControl"]["invocationInputs"]:
                    # Process function invocation input
                    if "functionInvocationInput" in invocation_input:
                        function_invocation_input = FunctionInvocationInput(
                            action_group_name=invocation_input[
                                "functionInvocationInput"
                            ]["actionGroup"],
                            action_invocation_type=invocation_input[
                                "functionInvocationInput"
                            ]["actionInvocationType"],
                            agent_id=invocation_input["functionInvocationInput"][
                                "agentId"
                            ],
                            function_name=invocation_input["functionInvocationInput"][
                                "function"
                            ],
                            parameters=[
                                InputParam(
                                    name=parameter["name"],
                                    type=parameter["type"],
                                    value=parameter["value"],
                                )
                                for parameter in invocation_input[
                                    "functionInvocationInput"
                                ]["parameters"]
                            ],
                        )

                        invocation_inputs.append(function_invocation_input)

                    # Process api invocation input
                    elif "apiInvocationInput" in invocation_input:
                        api_invocation_input = ApiInvocationInput(
                            action_group_name=invocation_input["apiInvocationInput"][
                                "actionGroup"
                            ],
                            action_invocation_type=invocation_input[
                                "apiInvocationInput"
                            ]["actionInvocationType"],
                            agent_id=invocation_input["apiInvocationInput"]["agentId"],
                            api_path=invocation_input["apiInvocationInput"]["apiPath"],
                            http_method=invocation_input["apiInvocationInput"][
                                "httpMethod"
                            ],
                            parameters=[
                                InputParam(
                                    name=parameter["name"],
                                    type=parameter["type"],
                                    value=parameter["value"],
                                )
                                for parameter in invocation_input["apiInvocationInput"][
                                    "parameters"
                                ]
                            ],
                        )

                        invocation_inputs.append(api_invocation_input)

                    else:
                        raise ValueError(
                            f"Unknown invocation input type: {invocation_input}"
                        )

                return_control_invocation = ReturnControlInvocation(
                    invocation_id=invocation_id, invocation_inputs=invocation_inputs
                )
                stop_reason = StopReason.TOOL_USE

        text = "".join(texts)
        assistant_message = AssistantMessage(text=text)
        model_response = BedrockAgentModelResponse(
            assistant_message=assistant_message,
            stop_reason=stop_reason,
            return_control_invocation=return_control_invocation,
        )

        return model_response

    def _append_memory(self, message: Message) -> None:
        """Append to memory and save to the memory store."""
        logger.info(f"Appending {message.role} message to memory")
        self.session_state.memory.append(message)

        logger.info("Saving to memory store")
        if self.session_id and self.memory_store:
            self.memory_store.save_memory(
                session_id=self.session_id, memory=self.session_state.memory
            )

    def _update_invocation_log(self, model_response: BedrockAgentModelResponse) -> None:
        """Append invocation log to the invocation history."""
        logger.info("Logging invocation to invocation history")
        invocation_log = BaseInvocationLog(
            response=model_response, input_messages=self.get_messages()
        )
        self.invocation_history.append(log=invocation_log)

    def _handle_stop_reason(
        self,
        model_response: BedrockAgentModelResponse,
    ) -> StopResult:
        """Handle the stop reason from the model response."""
        logger.info("Handling stop reason: %s", model_response.stop_reason)
        match model_response.stop_reason:
            case StopReason.TOOL_USE:
                logger.info("Handling tool use")
                result = self._handle_tool_use(model_response=model_response)

            case StopReason.END_TURN:
                logger.info("Handling end turn")
                result = self._handle_end_turn(model_response=model_response)

        return result

    def _handle_tool_use(self, model_response: BedrockAgentModelResponse) -> StopResult:
        """Handle tool use.

        Args:
            model_response (BedrockAgentModelResponse): The model response.

        Returns:
            StepResult: The tool result

        """
        # The message that will be returned
        invocation_results: List[ApiInvocationResult | FunctionInvocationResult] = []

        if self.action_groups and model_response.return_control_invocation:
            for (
                invocation_input
            ) in model_response.return_control_invocation.invocation_inputs:
                # Match for the action group
                for action_group in self.action_groups:
                    # Function schema found
                    if (
                        action_group.name == invocation_input.action_group_name
                        and action_group.action_group_schema
                        and isinstance(action_group.action_group_schema, FunctionSchema)
                        and action_group.action_group_schema.functions
                        and isinstance(invocation_input, FunctionInvocationInput)
                    ):
                        # Match for the function
                        for function in action_group.action_group_schema.functions:
                            # Function found
                            if function.name == invocation_input.function_name:
                                # Invoke the function
                                function_result = function.invoke(
                                    **invocation_input.param_dict
                                )

                                function_invocation_result = FunctionInvocationResult(
                                    action_group=action_group.name,
                                    agent_id=invocation_input.agent_id,
                                    confirmation_state="CONFIRM",
                                    response_body=InvocationResponseBody(
                                        body=function_result,
                                    ),
                                    response_state="REPROMPT",
                                    function_name=invocation_input.function_name,
                                )

                                invocation_results.append(function_invocation_result)

                                break

                        break
                    elif (
                        action_group.name == invocation_input.action_group_name
                        and action_group.action_group_schema
                        and isinstance(action_group.action_group_schema, ApiSchema)
                        and action_group.action_group_schema.payload
                        and isinstance(invocation_input, ApiInvocationInput)
                        and action_group.action_group_schema.callable_function
                    ):
                        # Parse the payload
                        open_api_schema = json.loads(
                            action_group.action_group_schema.payload
                        )

                        # Check if the invocation input function is in the OpenAPI schema
                        if invocation_input.api_path in open_api_schema["paths"]:
                            # Build the event to pass to the function
                            event = invocation_input.to_event_dict()

                            # Invoke the function
                            api_result = (
                                action_group.action_group_schema.callable_function(
                                    event, None
                                )
                            )

                            response = api_result["response"]
                            response_text = response["functionResponse"][
                                "responseBody"
                            ]["TEXT"]["body"]
                            api_invocation_result = ApiInvocationResult(
                                action_group=action_group.name,
                                agent_id=invocation_input.agent_id,
                                confirmation_state="CONFIRM",
                                response_body=InvocationResponseBody(
                                    body=response_text,
                                ),
                                response_state="REPROMPT",
                                api_path=invocation_input.api_path,
                                http_method=invocation_input.http_method,
                            )

                            invocation_results.append(api_invocation_result)

                            break
                    else:
                        raise ValueError(f"No valid action group found.")

        else:
            raise ValueError("Action group must be provided")

        return StopResult(
            status=HandleStopResult.CONTINUE,
            body={"invocation_results": invocation_results},
        )

    def _handle_end_turn(self, model_response: BedrockAgentModelResponse) -> StopResult:
        """Handle end turn.

        Args:
            model_response (BedrockAgentModelResponse): The model response.

        Returns:
            StopResult: The result of handling end turn

        """
        return StopResult(
            status=HandleStopResult.END_TURN,
            body={
                "session_id": self.session_id,
                "text": model_response.assistant_message.text,
            },
        )

    def get_messages(self) -> List[Message]:
        """Return messages as UserMessage and AssistantMessage list."""
        return self.session_state.memory.get_messages()

    def new_session(self, session_id: str | None = None) -> None:
        """Create a new session.

        Args:
            session_id (str): The session id. Defaults to uuid4.

        """
        self.session_id = str(uuid.uuid4()) if not session_id else session_id
        self.session_state = BedrockAgentSessionState()
        self.invocation_history = BaseInvocationHistory()
        # self.update_callback = None
        # self.collaboration_mode = "DISABLED"
        # self.collaborators = []
        # self.action_groups = []
        # self.guardrail_configuration = None
        # self.apply_guardrail_interval = None
        # self.knowledge_bases = []

    def add_collaborator(
        self,
        collaborator_agent: "BedrockInlineAgent",
        collaborator_config: CollaboratorConfig,
    ) -> None:
        """Add a collaborator to the agent."""
        self.collaborators.append(collaborator_agent)
        self.collaborator_configurations.append(collaborator_config)

    def add_collaborators(self, collaborators: List[Dict[str, Any]]) -> None:
        """Add multiple collaborators to the agent.

        Args:
            collaborators (List[Dict[str, Any]): Contains a list of collaborators
                agent (BedrockInlineAgent): The agent collaborator
                config (CollaboratorConfig): The collaborator config
        """
        for collaborator in collaborators:
            agent: "BedrockInlineAgent" = collaborator["agent"]
            config: CollaboratorConfig = collaborator["config"]
            self.add_collaborator(agent, config)

    def set_collaboration_mode(self, mode: CollaborationMode) -> None:
        """Set the collaboration mode."""
        self.collaboration_mode = mode

    def to_boto3_format(self) -> Dict[str, Any]:
        """Output the collaborator dict for use with multi-agent collaboration."""
        # TODO: need to implement for nested inline agents

        formatted_dict: Dict[str, Any] = {}

        if self.action_groups:
            formatted_dict["actionGroups"] = [
                action_group.to_boto3_format() for action_group in self.action_groups
            ]

        if self.collaboration_mode:
            formatted_dict["agentCollaboration"] = self.collaboration_mode

        if self.name:
            formatted_dict["agentName"] = self.name

        if self.collaborator_configurations:
            formatted_dict["collaboratorConfigurations"] = [
                collaborator_config.to_boto3_format()
                for collaborator_config in self.collaborator_configurations
            ]

        if self.customer_encryption_key_arn:
            formatted_dict["customerEncryptionArn"] = self.customer_encryption_key_arn

        if self.model:
            formatted_dict["foundationModel"] = self.model.bedrock_model_id

        if self.guardrail_configuration:
            formatted_dict["guardrailConfiguration"] = (
                self.guardrail_configuration.to_boto3_format()
            )

        if self.idle_session_ttl_in_seconds:
            formatted_dict["idleSessionTTLInSeconds"] = self.idle_session_ttl_in_seconds

        if self.system_message:
            formatted_dict["instruction"] = self.system_message.get_text()

        if self.knowledge_bases:
            formatted_dict["knowledgeBases"] = [
                knowledge_base.to_boto3_format()
                for knowledge_base in self.knowledge_bases
            ]
        if self.prompt_override_configuration:
            formatted_dict["promptOverrideConfiguration"] = (
                self.prompt_override_configuration.to_boto3_format()
            )

        return formatted_dict
