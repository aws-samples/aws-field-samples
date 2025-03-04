from typing import Any, Dict, List

import boto3  # type: ignore
from botocore.exceptions import ClientError
from pydantic import Field

from converseagent.logging_utils.logger_config import setup_logger
from converseagent.models.base import BaseChatModel

logger = setup_logger(__name__)


class BedrockModel(BaseChatModel):
    bedrock_model_id: str = Field(description="The Bedrock model to use")
    client: Any = Field(default=None, description="The boto3 bedrock-runtime client")

    def model_post_init(self, *args, **kwargs) -> None:
        # Initialize Bedrock runtime client
        self.client = boto3.client("bedrock-runtime")

    def invoke(
        self,
        messages: List[dict],
        system: List[Dict[str, str]] | None = None,
        inference_config: Dict[str, str | int] | None = None,
        tool_config: Dict[str, List[Any]] | None = None,
    ) -> Dict:
        # Build params
        params = {"modelId": self.bedrock_model_id, "messages": messages}

        # Add system if present
        if system:
            params.update({"system": system})

        # Add inferenceConfig if present
        if inference_config:
            params.update({"inferenceConfig": inference_config})

        # Add toolConfig if tools are present
        if tool_config:
            params.update({"toolConfig": tool_config})

        try:
            response = self.client.converse(**params)

        except ClientError as e:
            logger.error("Error executing Converse API: %s", e)
            logger.error("Error code: %s", e.response["Error"]["Code"])
            raise e

        return response
