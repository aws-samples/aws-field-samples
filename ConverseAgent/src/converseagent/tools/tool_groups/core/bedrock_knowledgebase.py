from typing import Dict, List

import boto3
import yaml
from botocore.exceptions import ClientError
from pydantic import Field, model_validator

from converseagent.content import TextContentBlock
from converseagent.tools.base import BaseTool, BaseToolGroup, BaseToolResponse
from converseagent.tools.tool_response import (
    ResponseStatus,
    ResponseType,
    TextToolResponse,
)


class BedrockKnowledgeBaseToolGroup(BaseToolGroup):
    name: str = "br_kb_tools"
    description: str = "Tools for interacting with Bedrock KB"
    instructions: str = """
    Use these tools to retrieve relevant documents.
    When passing in a query, hybrid search (vector search + full-text search)
    will be performed with your query and the documents within the knoledge base.
    Your search query should be detailed enough in order to make a good 
    search.
    
    Whenever possible, always use metadata filters to improve search results.
    """

    knowledge_bases: List[Dict[str, str]] = Field(
        default_factory=list,
        description="List of knowledge bases that the agent has access to.",
    )

    @model_validator(mode="after")
    def validate_tools(self):
        """Check if tools are passed, otherwise add tools"""
        if not self.tools:
            self.tools = [RetrieveFromBedrockKb()]
        return self

    def add_knowledge_base(
        self, knowledge_base_id: str, instructions: str, metadata: Dict[str, str] = None
    ):
        """Adds a Bedrock Knowledge Base to the agent

        Args:
            knowledge_base_id (str): The Bedrock Knowledge Base Id
            instructions (str): The instructions to use when retrieving from the KB
            metadata (Dict[str,str], optional): Additional metadata to include
                in the instructions for metadata filtering.
        """

        self.knowledge_bases.append(
            {"knowledge_base_id": knowledge_base_id, "instructions": instructions}
        )

        # Update instructions
        self.instructions += f"""
        <knowledgebase id={knowledge_base_id}>
        <instructions>
        {instructions}
        </instructions>
        <additional_metadata>
        {yaml.dump(metadata)}
        </additional_metadata>
        </knowledgebase>
        """

        return self


class RetrieveFromBedrockKb(BaseTool):
    """Tool for using the Retrieve API"""

    name: str = "retrieve_from_bedrock_kb"
    description: str = (
        "Use this tool to retrieve relevant chunks of "
        "information from the knowledge base"
    )

    def invoke(self, *args, **kwargs) -> BaseToolResponse:
        """Invokes the tool logic"""
        return self.retrieve_from_bedrock_kb(*args, **kwargs)

    def retrieve_from_bedrock_kb(
        self,
        knowledge_base_id: str,
        query: str,
        filter: dict | None = None,
        num_results: int = 10,
    ) -> BaseToolResponse:
        """Retrieves relevant chunks from the knowledge base"""
        bedrock = boto3.client(service_name="bedrock-agent-runtime")

        retrieval_config = {
            "vectorSearchConfiguration": {
                "numberOfResults": num_results,
                "overrideSearchType": "HYBRID",
            }
        }

        if filter:
            retrieval_config["vectorSearchConfiguration"].update({"filter": filter})

        try:
            response = bedrock.retrieve(
                knowledgeBaseId=knowledge_base_id,
                retrievalQuery={"text": query},
                retrievalConfiguration=retrieval_config,
            )

            retrieval_results = response["retrievalResults"]

            return BaseToolResponse(
                status=ResponseStatus.SUCCESS,
                type=ResponseType.CONTENT,
                content=[
                    TextContentBlock(text=str(result)) for result in retrieval_results
                ],
            )

        except ClientError as e:
            return TextToolResponse(
                status=ResponseStatus.ERROR,
                text=f"Error retrieving from knowledge base: {e}",
            )

    def get_tool_spec(self) -> Dict:
        """Returns the tool spec

        Returns:
            dict: The tool spec for the tool
        """

        return {
            "toolSpec": {
                "name": self.name,
                "description": self.description,
                "inputSchema": {
                    "json": {
                        "type": "object",
                        "properties": {
                            "knowledge_base_id": {
                                "type": "string",
                                "description": "ID of the Bedrock knowledge \
                                base to query",
                            },
                            "query": {
                                "type": "string",
                                "description": "The text query to search \
                                for in the knowledge base",
                            },
                            "filter": {
                                "type": "object",
                                "description": "Optional filter criteria \
                                for the search",
                                "properties": {
                                    "andAll": {"type": "array", "items": {"$ref": "#"}},
                                    "equals": {
                                        "type": "object",
                                        "properties": {
                                            "key": {"type": "string"},
                                            "value": {
                                                "oneOf": [
                                                    {"type": "object"},
                                                    {"type": "array"},
                                                    {"type": "number"},
                                                    {"type": "string"},
                                                    {"type": "boolean"},
                                                    {"type": "null"},
                                                ]
                                            },
                                        },
                                        "required": ["key", "value"],
                                    },
                                    "greaterThan": {
                                        "type": "object",
                                        "properties": {
                                            "key": {"type": "string"},
                                            "value": {
                                                "oneOf": [
                                                    {"type": "object"},
                                                    {"type": "array"},
                                                    {"type": "number"},
                                                    {"type": "string"},
                                                    {"type": "boolean"},
                                                    {"type": "null"},
                                                ]
                                            },
                                        },
                                        "required": ["key", "value"],
                                    },
                                    "greaterThanOrEquals": {
                                        "type": "object",
                                        "properties": {
                                            "key": {"type": "string"},
                                            "value": {
                                                "oneOf": [
                                                    {"type": "object"},
                                                    {"type": "array"},
                                                    {"type": "number"},
                                                    {"type": "string"},
                                                    {"type": "boolean"},
                                                    {"type": "null"},
                                                ]
                                            },
                                        },
                                        "required": ["key", "value"],
                                    },
                                    "in": {
                                        "type": "object",
                                        "properties": {
                                            "key": {"type": "string"},
                                            "value": {
                                                "oneOf": [
                                                    {"type": "object"},
                                                    {"type": "array"},
                                                    {"type": "number"},
                                                    {"type": "string"},
                                                    {"type": "boolean"},
                                                    {"type": "null"},
                                                ]
                                            },
                                        },
                                        "required": ["key", "value"],
                                    },
                                    "lessThan": {
                                        "type": "object",
                                        "properties": {
                                            "key": {"type": "string"},
                                            "value": {
                                                "oneOf": [
                                                    {"type": "object"},
                                                    {"type": "array"},
                                                    {"type": "number"},
                                                    {"type": "string"},
                                                    {"type": "boolean"},
                                                    {"type": "null"},
                                                ]
                                            },
                                        },
                                        "required": ["key", "value"],
                                    },
                                    "lessThanOrEquals": {
                                        "type": "object",
                                        "properties": {
                                            "key": {"type": "string"},
                                            "value": {
                                                "oneOf": [
                                                    {"type": "object"},
                                                    {"type": "array"},
                                                    {"type": "number"},
                                                    {"type": "string"},
                                                    {"type": "boolean"},
                                                    {"type": "null"},
                                                ]
                                            },
                                        },
                                        "required": ["key", "value"],
                                    },
                                    "listContains": {
                                        "type": "object",
                                        "properties": {
                                            "key": {"type": "string"},
                                            "value": {
                                                "oneOf": [
                                                    {"type": "object"},
                                                    {"type": "array"},
                                                    {"type": "number"},
                                                    {"type": "string"},
                                                    {"type": "boolean"},
                                                    {"type": "null"},
                                                ]
                                            },
                                        },
                                        "required": ["key", "value"],
                                    },
                                    "notEquals": {
                                        "type": "object",
                                        "properties": {
                                            "key": {"type": "string"},
                                            "value": {
                                                "oneOf": [
                                                    {"type": "object"},
                                                    {"type": "array"},
                                                    {"type": "number"},
                                                    {"type": "string"},
                                                    {"type": "boolean"},
                                                    {"type": "null"},
                                                ]
                                            },
                                        },
                                        "required": ["key", "value"],
                                    },
                                    "notIn": {
                                        "type": "object",
                                        "properties": {
                                            "key": {"type": "string"},
                                            "value": {
                                                "oneOf": [
                                                    {"type": "object"},
                                                    {"type": "array"},
                                                    {"type": "number"},
                                                    {"type": "string"},
                                                    {"type": "boolean"},
                                                    {"type": "null"},
                                                ]
                                            },
                                        },
                                        "required": ["key", "value"],
                                    },
                                    "orAll": {"type": "array", "items": {"$ref": "#"}},
                                    "startsWith": {
                                        "type": "object",
                                        "properties": {
                                            "key": {"type": "string"},
                                            "value": {
                                                "oneOf": [
                                                    {"type": "object"},
                                                    {"type": "array"},
                                                    {"type": "number"},
                                                    {"type": "string"},
                                                    {"type": "boolean"},
                                                    {"type": "null"},
                                                ]
                                            },
                                        },
                                        "required": ["key", "value"],
                                    },
                                    "stringContains": {
                                        "type": "object",
                                        "properties": {
                                            "key": {"type": "string"},
                                            "value": {
                                                "oneOf": [
                                                    {"type": "object"},
                                                    {"type": "array"},
                                                    {"type": "number"},
                                                    {"type": "string"},
                                                    {"type": "boolean"},
                                                    {"type": "null"},
                                                ]
                                            },
                                        },
                                        "required": ["key", "value"],
                                    },
                                },
                            },
                            "num_results": {
                                "type": "integer",
                                "description": "Number of results to return \
                                (default: 10)",
                                "default": 10,
                            },
                        },
                        "required": ["knowledge_base_id", "query"],
                    }
                },
            }
        }
