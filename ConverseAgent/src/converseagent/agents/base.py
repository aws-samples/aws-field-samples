import logging
import random
import string
from time import sleep
from typing import Annotated, Any, Callable, Dict, List, Union
from uuid import uuid4

from botocore.exceptions import ClientError, ReadTimeoutError  # type: ignore
from pydantic import BaseModel, Field, model_validator

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
from converseagent.messages import AssistantMessage, UserMessage
from converseagent.prompts.base import (
    CURRENT_PLAN_PROMPT_TEMPLATE,
    DEFAULT_SYSTEM_PROMPT_TEMPLATE,
    FINAL_RESPONSE_PROMPT,
    TOOL_GROUP_PROMPT_TEMPLATE,
)
from converseagent.tools.base import BaseTool
from converseagent.tools.tool_response import (
    NotFoundToolResponse,
    ResponseStatus,
    ResponseType,
    TextToolResponse,
)
from converseagent.utils.utils import get_max_tokens

logger = setup_logger(__name__)

Message = Annotated[Union[UserMessage, AssistantMessage], Field(discriminator="role")]


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

    model: Any = Field(description="The model to use")

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
    system_prompt_template: str = Field(
        default=DEFAULT_SYSTEM_PROMPT_TEMPLATE,
        description="The system prompt template to use",
    )
    requests_per_minute_limit: int = Field(
        default=None, description="The number of requests per minute to limit the agent"
    )
    tools: List[BaseTool] = Field(
        default_factory=list, description="The tools the agent has"
    )
    current_plan: str | None = Field(
        default=None, description="The current plan of the agent"
    )
    max_tokens: int | None = Field(
        default=None, description="The maximum output tokens"
    )

    return_final_response_only: bool = Field(
        default=True,
        description="Whether to reprompt the final response. Defaults to True.",
    )

    update_callback_function: Callable = Field(
        default=None,
        description="A callback function to update the UI. Defaults to None.",
    )

    @model_validator(mode="after")
    def validate_max_tokens(self):
        """Validator to get max tokens if not provided"""
        if self.max_tokens is None:
            self.max_tokens = get_max_tokens(self.model.bedrock_model_id)
        return self

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

    def get_invocation_history(self) -> List[BaseInvocationLog]:
        """Returns the invocation history of the agent."""
        return self.invocation_history.get_history()

    def get_cumulative_token_count(self) -> Dict[str, int]:
        """Returns the cumulative token count."""
        return self.invocation_history.get_cumulative_token_count()

    def append_memory(self, message: Message) -> None:
        """Appends to memory and saves to the memory store"""

        logger.info(f"Appending {message.role} message to memory")
        self.memory.append(message)

        logger.info("Saving to memory store")
        if self.session_id and self.memory_store:
            self.memory_store.save_memory(
                session_id=self.session_id, memory=self.memory
            )

    def get_converse_messages(self) -> List[Dict[str, Any]]:
        """Returns the messages in Converse format"""

        return self.memory.get_converse_messages()

    def get_messages(self) -> List[Message]:
        """Returns the messages as UserMessage and AssistantMessage list"""

        return self.memory.get_messages()

    def clear_memory(self) -> None:
        """Clears the memory of the agent."""
        self.memory.clear()

    def invoke(
        self,
        user_message: UserMessage | str,
        inference_config: Dict | None = None,
        update_callback_function: Callable | None = None,
        initial_plan: str | None = None,
        max_retries: int = 3,
        verbose: bool = False,
    ):
        """Invokes the agent

        Args:
            user_message (UserMessage | str): A UserMessage object or string.
                If string, it will be converted to a UserMessage object.
            inference_config (dict): The inference configuration to use for
                the agent. It must follow Converse API inference config format.
            initial_plan (str): Optional initial plan to use for the agent
            update_callback_function (callable): Optional callback function to send
                intermediate updates

        Returns:
            str: The response from the agent
        """

        # If verbose, set to logging level to info otherwise error
        if verbose:
            logger.setLevel(logging.INFO)
        else:
            logger.setLevel(logging.ERROR)

        if update_callback_function:
            self.update_callback_function = update_callback_function

        logger.info("Starting agent turn")

        # For convenience, convert string input to UserMessage
        if isinstance(user_message, str):
            user_message = UserMessage(text=user_message)

        # Append the provided UserMessage to the memory
        self.append_memory(message=user_message)

        # Sets current plan
        self.current_plan = initial_plan

        # Create the tool config
        logger.info("Building tool config")
        tool_config = self.get_tool_config()

        # Create the inference config
        logger.info("Building inference config")
        if inference_config is None:
            inference_config = {"maxTokens": self.max_tokens, "temperature": 0.0}

        # Initialize retry counter
        num_retries = 0
        max_retries = max_retries

        logger.info("Agent loop starting")
        while num_retries <= max_retries:
            # Initialize empty response
            response = {}

            ## Pre-invocation processing
            logger.info("Building current plan prompt")
            current_plan_prompt = CURRENT_PLAN_PROMPT_TEMPLATE.format(
                current_plan=self.current_plan
            )

            logger.info("Building system prompt")
            system_prompt = self.system_prompt_template.format(
                current_plan=current_plan_prompt
            )

            ## Converse Invocation
            try:
                # Common parameters for converse call

                logger.info("Building converse params")
                converse_params = {
                    "messages": self.get_converse_messages(),
                    "system": [{"text": system_prompt}],
                    "inference_config": inference_config,
                }

                # Add toolConfig if tools are present
                logger.info("Building tool config")
                if tool_config:
                    logger.info("Invoking Converse with tools")
                    converse_params.update({"tool_config": tool_config})
                else:
                    logger.info("Invoking Converse without tools")

                response = self.model.invoke(**converse_params)  # type: ignore

            # ClientError is raised by boto3 when AWS API calls fail
            except ClientError as e:
                logger.error("Error executing Converse API: %s", e)
                logger.error("Error code: %s", e.response["Error"]["Code"])
                error_code = e.response["Error"]["Code"]
                error_message = e.response["Error"]["Message"]

                if error_code in ["ThrottlingException", "ConnectionClosedError"]:
                    logger.error("Handling error")
                    # Handles rate limiting and connection issues from AWS
                    self.handle_exception_with_retry(
                        error_code=error_code, error_message=error_message
                    )

                    num_retries += 1

                    continue

                elif error_code == "ValidationException":
                    # TODO not capturing correctly
                    if "input is too long" in error_message:
                        # Handles when input exceeds model context window
                        self.handle_context_window_exceeded()

                    raise e

                else:
                    raise e

            # ReadTimeoutError is raised by urllib3 when request times out
            except ReadTimeoutError as e:
                self.handle_exception_with_retry(
                    error_code="ReadTimeoutError", error_message=str(e)
                )

                num_retries += 1

                continue

            # Catch any other unexpected exceptions
            except Exception as e:
                logger.error("Error executing Converse API: %s", e)
                raise e

            ## Post-invocation processing ##
            logger.info("Received Converse API response")

            # Parses the assistant message from the response
            logger.info("Parsing assistant message")
            assistant_message = AssistantMessage(message=response["output"]["message"])

            if assistant_message.update_message and update_callback_function:
                logger.info(f"Update message: {assistant_message.update_message}")
                update_callback_function(assistant_message.update_message)

            # Update the invocation history
            logger.info("Updating invocation history")
            invocation_log = BaseInvocationLog(
                response=response, input_messages=self.get_messages()
            )
            self.invocation_history.append(log=invocation_log)

            # Append the assistant message to the memory
            self.append_memory(assistant_message)

            # Sets the current plan
            logger.info("Setting current plan")
            if assistant_message.current_plan:
                self.current_plan = assistant_message.current_plan

            ## Stop Reason Handling ##
            logger.info("Handling stop reason: %s", response["stopReason"])

            match response["stopReason"]:
                case "tool_use":
                    logger.info("Handling tool use")
                    self.handle_tool_use(assistant_message=assistant_message)

                case "end_turn":
                    logger.info("Handling end turn")
                    result = self.handle_end_turn(assistant_message=assistant_message)

                    if result and result.get("status") == "success":
                        return result.get("body")
                    else:
                        num_retries += 1

                case "max_tokens":
                    logger.info("Handling max tokens exceeded")
                    self.handle_max_output_tokens_exceeed(response=response)

                case "stop_sequence":
                    logger.info("Handling stop sequence")
                    self.handle_stop_sequence(response=response)

                case "guardrail_intervened":
                    logger.info("Handling guardrail intervened")
                    self.handle_guardrail_intervened(response=response)

                case "content_filtered":
                    logger.info("Handling content filtered")
                    self.handle_content_filtered(response=response)

            # Sleep until next iteration
            logger.info("Completed agent iteration. Continuing loop...")
            if self.requests_per_minute_limit:
                sleep_time = 60 / self.requests_per_minute_limit
                logger.info(f"Sleeping for {sleep_time}")
                sleep(sleep_time)

        if num_retries > max_retries:
            logger.error("Max retries exceeded")
            raise Exception("Max retries exceeded")

    def add_tool(self, tool):
        """Adds a tool to the agent

        Args:
            tool (Tool): A Tool object
        """
        self.tools.append(tool)

    def add_tool_group(self, tool_group):
        """Adds tools from a tool group to the agent

        Args:
            tool_group (ToolGroup): A ToolGroup object
        """

        # Adds all of the tools under a tool group
        for tool in tool_group.tools:
            self.add_tool(tool)

        # Add the tool group instructions to system
        self.system_prompt_template += TOOL_GROUP_PROMPT_TEMPLATE.format(
            tool_group_name=tool_group.name,
            tool_group_instructions=tool_group.instructions,
            tool_names=tool_group.get_tool_names(),
        )

    def add_tool_groups(self, tool_groups):
        """Adds tool groups to the agent

        Args:
            tool_groups (List[ToolGroup]): A list of ToolGroup objects
        """
        for tool_group in tool_groups:
            self.add_tool_group(tool_group)

    def get_tool_config(self) -> Dict[str, List[Any]] | None:
        "Builds the tool_config for Converse"

        if len(self.tools) > 0:
            tool_list = []
            for tool in self.tools:
                tool_list.append(tool.get_tool_spec())

            return {"tools": tool_list}
        else:
            return None

    def handle_tool_use(self, assistant_message: AssistantMessage):
        """
        Handles tool use

        Args:
            message (dict): The assistant message from Converse API

        Returns:
            dict: The tool result message
        """

        # The message that will be returned
        tool_result_message = UserMessage()

        for block in assistant_message.content:
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
        self.append_memory(tool_result_message)

    def handle_exception_with_retry(self, error_code, error_message):
        """
        Handles the throttling exception by sleeping for a minute.
        """
        logger.error("%s: %s", error_code, error_message)

        if self.requests_per_minute_limit:
            sleep_time = 60 / self.requests_per_minute_limit
        else:
            sleep_time = 5

        logger.info(f"Retrying in {sleep_time}")
        sleep(sleep_time)

    def handle_end_turn(self, assistant_message: AssistantMessage):
        """
        Handles the end turn stop reason

        Args:
            message (dict): The assistant message from Converse API
        """

        logger.info("Checking for final response")

        # Return all of the text
        if self.return_final_response_only is False:
            logger.info(f"{self.name}: {assistant_message.text}")

            return {
                "status": "success",
                "body": {
                    "session_id": self.session_id,
                    "text": assistant_message.text,
                    "cumulative_usage": self.get_cumulative_token_count(),
                },
            }

        # Checks if final response if not re-prompt
        if assistant_message.final_response and self.return_final_response_only:
            logger.info(f"{self.name}: {assistant_message.final_response}")

            return {
                "status": "success",
                "body": {
                    "session_id": self.session_id,
                    "text": assistant_message.final_response,
                    "cumulative_usage": self.get_cumulative_token_count(),
                },
            }

        # Re-prompts the model to output final_response
        else:
            logger.info("Re-prompting to output final_response")
            self.append_memory(UserMessage(text=FINAL_RESPONSE_PROMPT))

            return {"status": "re-prompting"}

    def handle_context_window_exceeded(self) -> None:
        """
        Handles the context window exceeded exception by
        summarizing the conversation history and retrying.
        """
        # TODO
        raise NotImplementedError(
            """Context window exceeded handler \
                                  not implemented yet"""
        )

    def handle_max_output_tokens_exceeed(self, response: dict) -> None:
        """Handles the max output tokens exceeded stop reason"""
        # TODO
        raise NotImplementedError(
            """Max output tokens exceeded handler \
                                  not implemented yet"""
        )

    def handle_stop_sequence(self, response: dict) -> None:
        """Handles the stop sequence stop reason"""
        # TODO
        raise NotImplementedError(
            """Stop sequence handler \
                                  not implemented yet"""
        )

    def handle_guardrail_intervened(self, response: dict) -> None:
        """Handles the guardrail intervened stop reason"""
        # TODO
        raise NotImplementedError(
            """Guardrail intervened handler \
                                  not implemented yet"""
        )

    def handle_content_filtered(self, response: dict) -> None:
        """Handles the content filetered stop reason"""
        # TODO
        raise NotImplementedError(
            """Content filtered handler \
                                  not implemented yet"""
        )
