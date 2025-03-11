from abc import ABC, abstractmethod
from typing import Dict, List

from pydantic import BaseModel, Field

from converseagent.content import TextContentBlock
from converseagent.tools.tool_response import (
    BaseToolResponse,
    ResponseStatus,
    ResponseType,
)


class BaseTool(BaseModel, ABC):
    """Base class for all tools."""

    name: str = Field(description="Name of the tool")
    description: str = Field(description="Comprehensive description of the tool")
    is_async: bool = Field(
        default=False, description="Whether the tool is asynchronous"
    )
    metadata: dict = Field(default_factory=dict, description="Metadata for the tool")

    def invoke(self, *args, **kwargs) -> BaseToolResponse:
        """Invoke the tool logic

        Override this method to provide synchronous implementation
        """
        return BaseToolResponse(
            status=ResponseStatus.SUCCESS,
            type=ResponseType.CONTENT,
            content=[TextContentBlock(text="Tool not implemented")],
        )

    async def ainvoke(self, *args, **kwargs) -> BaseToolResponse:
        """Invoke the tool logic asynchronously

        Default implementation that calls the synchronous invoke method.
        Override this method to provide true async implementation.
        """

        return self.invoke(*args, **kwargs)

    @abstractmethod
    def get_tool_spec(spec) -> Dict:
        """Returns the Converse toolSpec dictionary"""
        pass


class BaseToolGroup(BaseModel):
    """Base class for all tool groups."""

    name: str = Field(description="Name of the tool group")
    description: str = Field(description="Comprehensive description of the tool group")
    instructions: str = Field(
        description="Instructions for the agent on \
            how to use the tools in the group"
    )
    tools: List[BaseTool] | None = Field(
        default_factory=list, description="List of tools as part of the tool group"
    )

    metadata: dict = Field(default_factory=dict, description="Metadata for the tool")

    def add_tool(self, tool: BaseTool) -> None:
        """Add a tool to the group

        Args:
            tool (BaseTool): The tool to add
        """
        self.tools.append(tool)

    def add_tools(self, tools: List[BaseTool]) -> None:
        """Add multiple tools to the group

        Args:
            tools (List[BaseTool]): List of tools to add
        """
        for tool in tools:
            self.add_tool(tool)

    def get_tool_names(self) -> List[str]:
        """Returns a list of tool names in the group."""
        return [tool.name for tool in self.tools]

    def get_tool_specs(self) -> List[dict]:
        """Returns a list of tool specifications in the group."""
        return [tool.get_tool_spec() for tool in self.tools]
