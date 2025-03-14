"""Contains Amazon Bedrock Guardrail classes."""

from pydantic import BaseModel, Field


class GuardrailConfiguration(BaseModel):
    """Represents the the guardrail configuration."""

    guardrail_identifier: str = Field(
        description="The identifier of the guardrail",
    )

    guardrail_version: str = Field(
        description="The version of the guardrail",
    )

    def to_boto3_format(self):
        """Format to Boto3 request."""
        return {
            "guardrailIdentifier": self.guardrail_identifier,
            "guardrailVersion": self.guardrail_version,
        }
