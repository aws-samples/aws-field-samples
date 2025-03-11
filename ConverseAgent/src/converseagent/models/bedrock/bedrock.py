from typing import Any, Dict, List

import boto3  # type: ignore
from botocore.config import Config  # type: ignore
from botocore.exceptions import ClientError  # type: ignore
from pydantic import Field

from converseagent.content import (
    ReasoningContentBlock,
    TextContentBlock,
    ToolUseContentBlock,
)
from converseagent.content.assistant import AssistantContentBlock
from converseagent.logging_utils.logger_config import setup_logger
from converseagent.messages import AssistantMessage
from converseagent.models.base import BaseChatModel
from converseagent.models.request import ModelRequest
from converseagent.models.response import ModelResponse
from converseagent.models.stop_reason import StopReason
from converseagent.utils.errors import ContextWindowExceeded
from converseagent.utils.retry import with_exponential_backoff

logger = setup_logger(__name__)


class BedrockModel(BaseChatModel):
    bedrock_model_id: str = Field(description="The Bedrock model to use")
    client: Any = Field(default=None, description="The boto3 bedrock-runtime client")
    timeout: int = Field(
        default=60,
        description="The timeout for the model invocation in seconds",
    )

    def model_post_init(self, *args, **kwargs) -> None:
        # Initialize Bedrock runtime client
        config = Config(read_timeout=self.timeout)
        self.client = boto3.client("bedrock-runtime", config=config)

    def invoke(self, model_request: ModelRequest) -> ModelResponse:
        # Build params
        model_request_dict = self._convert_model_request(model_request)

        response = self._invoke(**model_request_dict)

        return self._parse_model_response(response)

    def _convert_model_request(self, model_request: ModelRequest) -> Dict[str, Any]:
        """Format the ModelRequest to the model-specific request format"""

        # Base model request dict
        model_request_dict: Dict[str, Any] = {
            "modelId": self.bedrock_model_id,
            "messages": [message.format() for message in model_request.messages],
        }

        if model_request.system_message:
            model_request_dict["system"] = [
                content_block.format()
                for content_block in model_request.system_message.content
            ]

        if model_request.inference_config:
            model_request_dict["inferenceConfig"] = {
                "maxTokens": model_request.inference_config.max_tokens,
                "temperature": model_request.inference_config.temperature,
            }

        if model_request.tools:
            model_request_dict["toolConfig"] = {
                "tools": [tool.get_tool_spec() for tool in model_request.tools]
            }

        if model_request.additional_model_request_fields:
            model_request_dict["additionalModelRequestFields"] = (
                model_request.additional_model_request_fields
            )

        return model_request_dict

    @with_exponential_backoff()
    def _invoke(self, **kwargs) -> Dict[str, Any]:
        try:
            response = self.client.converse(**kwargs)

        except ClientError as e:
            logger.error("Error during model invocation: %s", e)
            logger.error("Error code: %s", e.response["Error"]["Code"])
            error_code = e.response["Error"]["Code"]
            error_message = e.response["Error"]["Message"]

            if error_code == "ValidationException":
                if "Input is too long" in error_message:
                    raise ContextWindowExceeded()

            else:
                raise e

        # Catch any other unexpected exceptions
        except Exception as e:
            logger.error("Error encountered during model invocation: %s", e)
            raise e

        return response

    def _parse_model_response(self, response: Dict) -> ModelResponse:
        """Parses the Converse API response into ModelResponse"""
        content: List[AssistantContentBlock] = []
        stop_reason = response["stopReason"]

        for block in response["output"]["message"]["content"]:
            if "text" in block:
                content.append(TextContentBlock(text=block["text"]))

            if "toolUse" in block:
                tool = block["toolUse"]
                tool_use_id = tool["toolUseId"]
                tool_name = tool["name"]
                tool_input = tool["input"]

                content.append(
                    ToolUseContentBlock(
                        tool_use_id=tool_use_id,
                        tool_name=tool_name,
                        tool_input=tool_input,
                    )
                )

            if "reasoningContent" in block:
                content.append(
                    ReasoningContentBlock(
                        reasoning_text=block["reasoningContent"]["reasoningText"][
                            "text"
                        ],
                        signature=block["reasoningContent"]["reasoningText"][
                            "signature"
                        ],
                    )
                )

        model_response_dict = {
            "assistant_message": AssistantMessage(content=content),
            "request_id": response["ResponseMetadata"]["RequestId"],
            "input_tokens": response["usage"]["inputTokens"],
            "output_tokens": response["usage"]["outputTokens"],
            "total_tokens": response["usage"]["totalTokens"],
            "stop_reason": StopReason(stop_reason),
        }

        return ModelResponse(**model_response_dict)
