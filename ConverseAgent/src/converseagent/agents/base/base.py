import asyncio

import logging
import random
import string
from time import sleep
from typing import Annotated, Any, Callable, Dict, List, Union
from uuid import uuid4
from pydantic import BaseModel, Field

from converseagent.content import (
    TextContentBlock,
    ToolResultContentBlock,
    ToolUseContentBlock,
)
from converseagent.explainability.invocation_history import (
    BaseInvocationHistory,
    BaseInvocationLog,
)
from converseagent.logging_utils.logger_config import setup_logger
from converseagent.memory import BaseMemory
from converseagent.memory_store import BaseMemoryStore
from converseagent.messages import AssistantMessage, UserMessage, SystemMessage
from converseagent.models.response import ModelResponse
from converseagent.models.request import ModelRequest
from converseagent.models.stop_reason import StopReason
from converseagent.prompts.base import (
    FINAL_RESPONSE_PROMPT,
    TOOL_GROUP_PROMPT_TEMPLATE,
)
from converseagent.tools.tool_response import (
    NotFoundToolResponse,
    ResponseStatus,
    ResponseType,
    TextToolResponse,
    BaseToolResponse,
)
from converseagent.tools.base import BaseToolGroup, BaseTool
from converseagent.models.base import BaseChatModel
from converseagent.utils.errors import ContextWindowExceeded, MaxIterationsExceeded
from converseagent.models.config import InferenceConfig
from asyncio import Task
from .base_prompts import DEFAULT_SYSTEM_MESSAGE
from enum import Enum

logger = setup_logger(__name__)

Message = Annotated[Union[UserMessage, AssistantMessage], Field(discriminator="role")]

DEFAULT_INFERENCE_CONFIG: InferenceConfig = InferenceConfig(
    max_tokens=4096, temperature=0.5
)


class HandleStopResult(Enum):
    CONTINUE = "continue"
    END_TURN = "end_turn"
    ERROR = "error"


class BaseAgent(BaseModel):
    """Base class for agents

    Attributes:
        client (Boto3.client): Bedrock-runtime client
        session_id (str):
        bedrock_model_id (str): ID of the model to use
        memory (BaseMemory, optional): Memory object to store
            conversation history. Defaults to BaseMemory().
        invocation_history (InvocationHistory, optional): Object to
            track API invocations. Defaults to InvocationHistory().
        name (str, optional): Name for the agent. Defaults to None.
        system_prompt_template (str, optional): System prompt template.
            Defaults to None.
        requests_per_minute_limit (int, optional): Maximum requests per
            minute. Defaults to None.
    """

    model: BaseChatModel = Field(description="The model to use")

    session_id: str | None = Field(
        default=str(uuid4()), description="A unique session id for the memory"
    )

    memory: BaseMemory = Field(
        default_factory=BaseMemory, description="The memory to use with the agent"
    )

    memory_store: BaseMemoryStore = Field(
        default_factory=BaseMemoryStore,
        description="The memory store to use with the agent",
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
        default=DEFAULT_SYSTEM_MESSAGE, description="The system message for the agent"
    )

    requests_per_minute_limit: int | None = Field(
        default=None, description="The number of requests per minute to limit the agent"
    )

    tools: List[BaseTool] = Field(
        default_factory=list, description="The tools the agent has"
    )

    current_plan: str | None = Field(
        default=None, description="The current plan of the agent"
    )

    return_final_response_only: bool = Field(
        default=True,
        description="Whether to reprompt the final response. Defaults to True.",
    )

    update_callback: Callable | None = Field(
        default=None,
        description="A callback function to update the UI. Defaults to None.",
    )

    def model_post_init(self, *args, **kwargs) -> None:
        # Load from memory store, if not found in memory store
        if self.session_id and self.memory_store:
            try:
                self.memory = self.memory_store.load_memory(session_id=self.session_id)
            except KeyError:
                logger.info(
                    "Session id %s not found in memory store. Creating a new memory.",
                    self.session_id,
                )

    def invoke(
        self,
        user_message: UserMessage | str,
        system_message: SystemMessage | str = DEFAULT_SYSTEM_MESSAGE,
        inference_config: InferenceConfig = DEFAULT_INFERENCE_CONFIG,
        max_iterations: int = 10,
        additional_model_request_fields: Dict[str, Any] = {},
        update_callback: Callable | None = None,
        verbose: bool = False,
    ) -> Dict[str, Any]:
        """Invokes the agent

        Args:
            user_message (UserMessage | str): A UserMessage object or string.
                If string, it will be converted to a UserMessage object.
            system_message (System Message | str): A SystemMessage object or string.
                if string, it will be converted to a SystemMessage object.
            inference_config (InferenceConfig): An InferenceConfig object.
            max_iterations (int): Maximum number of iterations. Default=10
            additional_model_request_fields (Dict | None): Additional request fields
                sent to the model.
            update_callback (Callable): Optional callback function to send
                intermediate updates
            verbose (bool): If set to True, logging level is INFO otherwise ERROR
        Returns:
            Dict[str, any]: A dict containing the response
        """

        # Set logging level
        self._set_logging_level(verbose)

        # Set the callback
        self.update_callback = update_callback

        logger.info("Starting agent turn")

        # For convenience, convert string input to UserMessage
        if isinstance(user_message, str):
            user_message = UserMessage(text=user_message)

        if isinstance(system_message, str):
            system_message = SystemMessage(text=system_message)

        # Append the provided UserMessage to the memory
        self._append_memory(message=user_message)

        # Initialize retry counter
        current_iteration = 0
        logger.info("Agent loop starting")

        while current_iteration < max_iterations:
            logger.info(f"Current iteration: {current_iteration}")
            logger.info(f"Maximum iterations: {max_iterations}")

            # Build the model request
            logger.info("Building model request")

            # (Optional) Execute any pre-iteration processing
            self._pre_invocation_processing()

            model_request = ModelRequest(
                messages=self.get_messages(),
                system_message=system_message,
                inference_config=inference_config
                if inference_config
                else DEFAULT_INFERENCE_CONFIG,
                tools=self.get_tools(),
                additional_model_request_fields=additional_model_request_fields,
            )

            ## Model invocation
            model_response: ModelResponse = self._invoke_model(model_request)

            # Update the invocation history
            self._update_invocation_log(model_response=model_response)

            # Append the assistant message to the memory
            self._append_memory(model_response.assistant_message)

            # (Optional) Execute any post-invocation processing
            self._post_invocation_processing()

            ## Stop Reason Handling
            stop_result = self._handle_stop_reason(model_response=model_response)

            # (Optional) Execute any final processing
            self._final_processing()

            # Return if END_TURN or continue otherwise
            if stop_result["status"] == HandleStopResult.END_TURN:
                logger.info("Agent completed turn.")
                break
            elif stop_result["status"] == HandleStopResult.CONTINUE:
                # Sleep until next iteration
                self._handle_completed_iteration()

                # Increment iteration counter
                current_iteration += 1

                if current_iteration > max_iterations:
                    self._handle_max_iterations_exceeded
            else:
                logger.error(f"Agent stopped: {stop_result}")
                break

        return stop_result

    async def ainvoke(
        self,
        user_message: UserMessage | str,
        system_message: SystemMessage = DEFAULT_SYSTEM_MESSAGE,
        inference_config: InferenceConfig = DEFAULT_INFERENCE_CONFIG,
        max_iterations: int = 10,
        additional_model_request_fields: Dict[str, Any] = {},
        update_callback: Callable | None = None,
        verbose: bool = False,
    ) -> Dict[str, Any]:
        """Invokes the agent

        Args:
            user_message (UserMessage | str): A UserMessage object or string.
                If string, it will be converted to a UserMessage object.
            system_message (System Message | str): A SystemMessage object or string.
                if string, it will be converted to a SystemMessage object.
            inference_config (InferenceConfig): An InferenceConfig object.
            max_iterations (int): Maximum number of iterations. Default=10
            additional_model_request_fields (Dict | None): Additional request fields
                sent to the model.
            update_callback (Callable): Optional callback function to send
                intermediate updates
            verbose (bool): If set to True, logging level is INFO otherwise ERROR
        Returns:
            Dict[str, any]: A dict containing the response
        """

        # Set logging level
        self._set_logging_level(verbose)

        # Set the callback
        self.update_callback = update_callback

        logger.info("Starting agent turn")

        # For convenience, convert string input to UserMessage
        if isinstance(user_message, str):
            user_message = UserMessage(text=user_message)

        # Append the provided UserMessage to the memory
        self._append_memory(message=user_message)

        # Initialize retry counter
        current_iteration = 0
        logger.info("Agent loop starting")

        while current_iteration < max_iterations:
            logger.info(f"Current iteration: {current_iteration}")
            logger.info(f"Maximum iterations: {max_iterations}")

            # Build the model request
            logger.info("Building model request")

            # (Optional) Execute any pre-iteration processing
            await self._apre_invocation_processing()

            model_request = ModelRequest(
                messages=self.get_messages(),
                system_message=system_message,
                inference_config=inference_config
                if inference_config
                else DEFAULT_INFERENCE_CONFIG,
                tools=self.get_tools(),
                additional_model_request_fields=additional_model_request_fields,
            )

            ## Model invocation
            model_response: ModelResponse = await self._ainvoke_model(model_request)

            # Update the invocation history
            self._update_invocation_log(model_response=model_response)

            # Append the assistant message to the memory
            self._append_memory(model_response.assistant_message)

            # (Optional) Execute any post-invocation processing
            await self._apost_invocation_processing()

            ## Stop Reason Handling
            stop_result = await self._ahandle_stop_reason(model_response=model_response)

            # (Optional) Execute any final processing
            await self._afinal_processing()

            # Return if END_TURN or continue otherwise
            if stop_result["status"] == HandleStopResult.END_TURN:
                logger.info("Agent completed turn.")
                break
            elif stop_result["status"] == HandleStopResult.CONTINUE:
                # Handle the end of the iteration
                await self._ahandle_completed_iteration()

                # Increment iteration counter
                current_iteration += 1

                if current_iteration > max_iterations:
                    self._handle_max_iterations_exceeded()
            else:
                logger.error(f"Agent stopped: {stop_result}")
                break

        return stop_result

    def get_invocation_history(self) -> List[BaseInvocationLog]:
        """Returns the invocation history of the agent."""
        return self.invocation_history.get_history()

    def get_cumulative_token_count(self) -> Dict[str, int]:
        """Returns the cumulative token count."""
        return self.invocation_history.get_cumulative_token_count()

    def get_converse_messages(self) -> List[Dict[str, Any]]:
        """Returns the messages in Converse format"""

        return self.memory.get_converse_messages()

    def get_messages(self) -> List[Message]:
        """Returns the messages as UserMessage and AssistantMessage list"""

        return self.memory.get_messages()

    def set_messages(self, messages: List[Message]):
        """Sets the messages list of the agent"""
        self.memory.set_messages(messages)

    def get_tools(self) -> List[BaseTool]:
        """Returns the tools associated with the agent"""

        return self.tools

    def clear_memory(self) -> None:
        """Clears the memory of the agent."""
        self.memory.clear()

    def add_tool(self, tool: BaseTool):
        """Adds a tool to the agent

        Args:
            tool (BaseTool): A Tool object
        """
        self.tools.append(tool)

    def add_tool_group(self, tool_group: BaseToolGroup):
        """Adds tools from a tool group to the agent

        Args:
            tool_group (ToolGroup): A ToolGroup object
        """

        # Adds all of the tools under a tool group

        if tool_group.tools:
            for tool in tool_group.tools:
                self.add_tool(tool)

            # Add the tool group prompt ot the system message
            self.system_message.append_text_block(
                text=TOOL_GROUP_PROMPT_TEMPLATE.format(
                    tool_group_name=tool_group.name,
                    tool_group_instructions=tool_group.instructions,
                    tool_names=tool_group.get_tool_names(),
                )
            )
        else:
            raise Exception("Tool group has no tools.")

    def add_tool_groups(self, tool_groups):
        """Adds tool groups to the agent

        Args:
            tool_groups (List[ToolGroup]): A list of ToolGroup objects
        """
        for tool_group in tool_groups:
            self.add_tool_group(tool_group)

    def clear_tools(self):
        "Clears all tools associated"
        self.tools = []

    def _invoke_model(self, model_request: ModelRequest) -> ModelResponse:
        try:
            logger.info("Invoking model")
            model_response: ModelResponse = self.model.invoke(model_request)
            logger.info("Received model response")
            logger.debug("Model response: %s", model_response)
        except ContextWindowExceeded:
            logger.error("Context window exceeded.")
            self._handle_context_window_exceeded()

        return model_response

    async def _ainvoke_model(self, model_request: ModelRequest) -> ModelResponse:
        try:
            logger.info("Invoking model")
            model_response: ModelResponse = await self.model.ainvoke(
                model_request=model_request
            )
            logger.info("Received model response")
            logger.debug("Model response: %s", model_response)
        except ContextWindowExceeded:
            logger.error("Context window exceeded.")
            self._handle_context_window_exceeded()

        return model_response

    def _update_invocation_log(self, model_response: ModelResponse) -> None:
        """Appends an invocation log to the invocation history"""
        logger.info("Logging invocation to invocation history")
        invocation_log = BaseInvocationLog(
            response=model_response, input_messages=self.get_messages()
        )
        self.invocation_history.append(log=invocation_log)

    def _append_memory(self, message: Message) -> None:
        """Appends to memory and saves to the memory store"""

        logger.info(f"Appending {message.role} message to memory")
        self.memory.append(message)

        logger.info("Saving to memory store")
        if self.session_id and self.memory_store:
            self.memory_store.save_memory(
                session_id=self.session_id, memory=self.memory
            )

    def _handle_stop_reason(
        self,
        model_response: ModelResponse,
    ):
        logger.info("Handling stop reason: %s", model_response.stop_reason)
        match model_response.stop_reason:
            case StopReason.TOOL_USE:
                logger.info("Handling tool use")
                result = self._handle_tool_use(model_response=model_response)

            case StopReason.END_TURN:
                logger.info("Handling end turn")
                result = self._handle_end_turn(model_response=model_response)

            case StopReason.MAX_TOKENS:
                logger.info("Handling max tokens exceeded")
                result = self._handle_max_output_tokens_exceeed(
                    model_response=model_response
                )
            case StopReason.STOP_SEQUENCE:
                logger.info("Handling stop sequence")
                result = self._handle_stop_sequence(model_response=model_response)

            case StopReason.GUARDRAIL_INTERVENED:
                logger.info("Handling guardrail intervened")
                result = self._handle_guardrail_intervened(
                    model_response=model_response
                )

            case StopReason.CONTENT_FILTERED:
                logger.info("Handling content filtered")
                result = self._handle_content_filtered(model_response=model_response)

        logger.info(f"Stop reason handle result status: {result['status']}")
        return result

    async def _ahandle_stop_reason(
        self,
        model_response: ModelResponse,
    ):
        logger.info("Handling stop reason: %s", model_response.stop_reason)
        match model_response.stop_reason:
            case StopReason.TOOL_USE:
                logger.info("Handling tool use")
                result = await self._ahandle_tool_use(model_response=model_response)

            case StopReason.END_TURN:
                logger.info("Handling end turn")
                result = self._handle_end_turn(model_response=model_response)

            case StopReason.MAX_TOKENS:
                logger.info("Handling max tokens exceeded")
                result = self._handle_max_output_tokens_exceeed(
                    model_response=model_response
                )

            case StopReason.STOP_SEQUENCE:
                logger.info("Handling stop sequence")
                result = self._handle_stop_sequence(model_response=model_response)

            case StopReason.GUARDRAIL_INTERVENED:
                logger.info("Handling guardrail intervened")
                result = self._handle_guardrail_intervened(
                    model_response=model_response
                )

            case StopReason.CONTENT_FILTERED:
                logger.info("Handling content filtered")
                result = self._handle_content_filtered(model_response=model_response)

        logger.info(f"Stop reason handle result status: {result['status']}")
        return result

    def _get_tool_config(self) -> Dict[str, List[Any]] | None:
        "Builds the tool_config for Converse"

        if len(self.tools) > 0:
            tool_list = []
            for tool in self.tools:
                tool_list.append(tool.get_tool_spec())

            return {"tools": tool_list}
        else:
            return None

    def _set_logging_level(self, verbose: bool) -> None:
        # Set logging level
        log_level = logging.INFO if verbose else logging.ERROR
        root_logger = logging.getLogger()
        root_logger.setLevel(log_level)
        for handler in root_logger.handlers:
            handler.setLevel(log_level)

    def _handle_tool_use(self, model_response: ModelResponse):
        """
        Handles tool use

        Args:
            message (dict): The assistant message from Converse API

        Returns:
            dict: The tool result message
        """

        # The message that will be returned
        tool_result_message = UserMessage()

        for block in model_response.assistant_message.content:
            if isinstance(block, TextContentBlock):
                logger.debug(f"{self.name} Thought: {block.text}")

            if isinstance(block, ToolUseContentBlock):
                tool_use_id = block.tool_use_id
                tool_name = block.tool_name
                tool_input = block.tool_input

                logger.info(f"Tool Use: {tool_name}")
                logger.info(f"tool_input: {tool_input}")

                # Call the appropriate tool
                tool_found = False
                for tool in self.tools:
                    # Find the tool
                    if tool_name == tool.name:
                        tool_found = True

                        try:
                            # Execute the tool with the parameters
                            # tool_response is a list of BaseContentBlock
                            tool_response = tool.invoke(**tool_input)

                        except Exception as e:
                            logger.error(f"Error executing tool: {e}")
                            tool_response = TextToolResponse(
                                ResponseStatus.ERROR, f"Error executing tool: {e}"
                            )

                        break

                # Default response if not found
                if tool_found is False:
                    logger.error(f"Tool {tool_name} not found")
                    tool_response = NotFoundToolResponse()

                # Tool response handling
                tool_response_status = tool_response.get_status()
                tool_response_type = tool_response.get_type()

                # Handle success
                if tool_response_status == ResponseStatus.SUCCESS:
                    logger.info("Tool successfully executed.")

                    logger.debug(
                        "Tool response: %s",
                        [block.format() for block in tool_response.get_content()],
                    )
                    if tool_response_type == ResponseType.CONTENT:
                        tool_result_content = tool_response.get_content()

                # Handle error
                elif tool_response_status == ResponseStatus.ERROR:
                    logger.error(
                        "Tool encountered an error: %s",
                        [block.format() for block in tool_response.get_content()],
                    )
                    if tool_response_type == ResponseType.CONTENT:
                        tool_result_content = tool_response.get_content()

                # Append the tool result block
                tool_result_content_block = ToolResultContentBlock(
                    tool_use_id=tool_use_id, tool_result_content=tool_result_content
                )
                tool_result_message.append_content(tool_result_content_block)

        # Appends the tool result message to memory
        logger.info("Appending tool result message to memory")
        self._append_memory(tool_result_message)

        return {"status": HandleStopResult.CONTINUE}

    async def _ahandle_tool_use(self, model_response: ModelResponse):
        """
        Handles tool use

        Args:
            message (dict): The assistant message from Converse API

        Returns:
            dict: The tool result message
        """

        async def ainvoke_tool(
            tool_use_id: str, tool: BaseTool, tool_input: dict
        ) -> Dict[str, Any]:
            """Invokes the tool asynchronously"""
            try:
                tool_response = await tool.ainvoke(**tool_input)
                return {"tool_use_id": tool_use_id, "tool_response": tool_response}
            except Exception as e:
                raise e

        # The message that will be returned
        tool_result_message = UserMessage()

        # Tasks
        tasks: List[Task] = []
        task_results = []

        for block in model_response.assistant_message.content:
            if isinstance(block, TextContentBlock):
                logger.debug(f"{self.name} Thought: {block.text}")

            if isinstance(block, ToolUseContentBlock):
                tool_use_id: str = block.tool_use_id
                tool_name: str = block.tool_name
                tool_input: Dict[str, Any] = block.tool_input

                logger.info(f"Tool Use: {tool_name}")
                logger.info(f"tool_input: {tool_input}")

                # Call the appropriate tool
                tool_found = False
                for tool in self.tools:
                    # Find the tool
                    if tool_name == tool.name:
                        tool_found = True

                        task: Task = asyncio.create_task(
                            ainvoke_tool(tool_use_id, tool, tool_input)
                        )
                        tasks.append(task)
                        break

                if tool_found is False:
                    tool_result_message.append_content(
                        ToolResultContentBlock(
                            tool_use_id=tool_use_id,
                            tool_result_content=[
                                TextContentBlock(text=f"Tool {tool_name} not found")
                            ],
                        )
                    )

                # Execute all tools concurrently
                task_results = await asyncio.gather(*tasks)

                for task_result in task_results:
                    tool_use_id = task_result["tool_use_id"]
                    tool_response: BaseToolResponse = task_result["tool_response"]

                    # Tool response handling
                    tool_response_status = tool_response.get_status()
                    tool_response_type = tool_response.get_type()

                    # Handle success
                    if tool_response_status == ResponseStatus.SUCCESS:
                        logger.info("Tool successfully executed.")

                        logger.debug(
                            "Tool response: %s",
                            [block.format() for block in tool_response.get_content()],
                        )
                        if tool_response_type == ResponseType.CONTENT:
                            tool_result_content = tool_response.get_content()

                    # Handle error
                    elif tool_response_status == ResponseStatus.ERROR:
                        logger.error(
                            "Tool encountered an error: %s",
                            [block.format() for block in tool_response.get_content()],
                        )
                        if tool_response_type == ResponseType.CONTENT:
                            tool_result_content = tool_response.get_content()

                    # Append the tool result block
                    tool_result_content_block = ToolResultContentBlock(
                        tool_use_id=tool_use_id, tool_result_content=tool_result_content
                    )
                    tool_result_message.append_content(tool_result_content_block)

        # Appends the tool result message to memory
        logger.info("Appending tool result message to memory")
        self._append_memory(tool_result_message)

        return {"status": HandleStopResult.CONTINUE}

    def _handle_end_turn(self, model_response: ModelResponse):
        """
        Handles the end turn stop reason

        Args:
            message (dict): The assistant message from Converse API
        """

        logger.info("Checking for final response")

        # Return all of the text
        if self.return_final_response_only is False:
            logger.debug(f"{self.name}: {model_response.assistant_message.text}")

            return {
                "status": HandleStopResult.END_TURN,
                "body": {
                    "session_id": self.session_id,
                    "text": model_response.assistant_message.text,
                    "cumulative_usage": self.get_cumulative_token_count(),
                },
            }

        # Checks if final response if not re-prompt
        if (
            model_response.assistant_message.final_response
            and self.return_final_response_only
        ):
            logger.debug(
                f"{self.name}: {model_response.assistant_message.final_response}"
            )

            return {
                "status": HandleStopResult.END_TURN,
                "body": {
                    "session_id": self.session_id,
                    "text": model_response.assistant_message.final_response,
                    "cumulative_usage": self.get_cumulative_token_count(),
                },
            }

        # Re-prompts the model to output final_response
        else:
            logger.info("Re-prompting to output final_response")
            self._append_memory(UserMessage(text=FINAL_RESPONSE_PROMPT))

            return {"status": HandleStopResult.CONTINUE}

    def _handle_context_window_exceeded(self) -> Dict[str, Any]:
        """Handles the Input too long exception

        Override this function to handle this
        """
        return {
            "status": HandleStopResult.ERROR,
            "body": {"text": "Input is too long for the model"},
        }

    def _handle_max_output_tokens_exceeed(
        self, model_response: ModelResponse
    ) -> Dict[str, Any]:
        """Handles the max output tokens exceeded stop reason

        Override this funciton to handle this
        """
        return {
            "status": HandleStopResult.ERROR,
            "body": {"text": "Max output tokens exceeded for the model"},
        }

    def _handle_stop_sequence(self, model_response: ModelResponse) -> Dict[str, Any]:
        """Handles the stop sequence stop reason

        Override this function to handle this
        """
        return {
            "status": HandleStopResult.END_TURN,
            "body": {
                "session_id": self.session_id,
                "text": model_response.assistant_message.text,
                "cumulative_usage": self.get_cumulative_token_count(),
            },
        }

    def _handle_guardrail_intervened(
        self, model_response: ModelResponse
    ) -> Dict[str, Any]:
        """Handles the guardrail intervened stop reason

        Override this function to handle this
        """
        return {
            "status": HandleStopResult.END_TURN,
            "body": {"text": "Guardrail intervened"},
        }

    def _handle_content_filtered(self, model_response: ModelResponse) -> Dict[str, Any]:
        """Handles the content filetered stop reason

        Override this function to handle this
        """
        return {
            "status": HandleStopResult.ERROR,
            "body": {"text": "Content filtered by the model"},
        }

    def _handle_max_iterations_exceeded(self):
        """Handles when max iterations exceeded

        Override this function to handle this
        """
        logger.error("Max iterations exceeded")
        raise MaxIterationsExceeded()

    def _pre_invocation_processing(self):
        """Override this function to do any processing before an iteration"""
        logger.info("Executing pre-invocation steps")

        pass

    def _post_invocation_processing(self):
        """Override this function to do any processing after an iteration"""
        logger.info("Executing post-invocation steps")

        if self.update_callback:
            self.update_callback(self.get_messages()[-1].update_message)

    def _final_processing(self):
        """Override this funciton to do any processing after completing an iteration"""
        logger.info("Executing final steps")

        pass

    def _handle_completed_iteration(self):
        """Executes when an agent iteration is completed.
        By default, it will sleep if rate limited otherwise continue
        """
        logger.info("Executing completed iteration steps")
        if self.requests_per_minute_limit:
            logger.info(f"Rate limited: {self.requests_per_minute_limit}")
            sleep_time = 60 / self.requests_per_minute_limit
            logger.info(f"Sleeping for {sleep_time}")
            sleep(sleep_time)

    async def _apre_invocation_processing(self):
        """Executes any steps before invocation asynchronously

        Override this function to do any processing before an iteration"""
        logger.info("Executing pre-invocation steps")
        pass

    async def _apost_invocation_processing(self):
        """Executes any steps after invocation asynchronously
        Override this function to do any processing after an iteration"""
        logger.info("Executing post-invocation steps")

        if self.update_callback:
            self.update_callback(self.get_messages()[-1].update_message)

    async def _afinal_processing(self):
        """Executes any steps after all steps in the agent are completed asynchronously

        Override this funciton to do any processing after completing an iteration"""
        logger.info("Executing final steps")
        pass

    async def _ahandle_completed_iteration(self):
        """Executes when an agent iteration is completed.

        By default, it will sleep if rate limited otherwise continue
        """
        logger.info("Completed iteration. Continuing loop...")
        if self.requests_per_minute_limit:
            logger.info(f"Rate limited: {self.requests_per_minute_limit}")
            sleep_time = 60 / self.requests_per_minute_limit
            logger.info(f"Sleeping for {sleep_time}")
            await asyncio.sleep(sleep_time)
