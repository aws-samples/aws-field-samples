"""Contains Amazon Bedrock Knowledge Base classes."""

from typing import Any, Dict

from pydantic import BaseModel, Field


class BedrockKnowledgeBase(BaseModel):
    """Represents a Bedrock Knowledge Base."""

    description: str = Field(
        default="", description="The description of the knowledge base"
    )

    knowledge_base_id: str = Field(description="The knowledge base ID")

    retrieval_configuration: Dict[str, Any] = Field(
        default_factory=dict, description="The retrieval configuration"
    )

    def to_boto3_format(self):
        """Format to Boto3 request."""
        knowledge_base_dict = {
            "description": self.description,
            "knowledgeBaseId": self.knowledge_base_id,
        }

        if self.retrieval_configuration:
            knowledge_base_dict["retrievalConfiguration"] = self.retrieval_configuration

        return knowledge_base_dict
