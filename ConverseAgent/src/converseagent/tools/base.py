from abc import ABC, abstractmethod
from typing import List, Dict
from converseagent.tools.tool_response import BaseToolResponse

from pydantic import BaseModel, Field


class BaseTool(BaseModel, ABC):
    """Base class for all tools."""

    name: str = Field(description="Name of the tool")
    description: str = Field(description="Comprehensive description of the tool")

    @abstractmethod
    def invoke(self, *args, **kwargs) -> BaseToolResponse:
        """Invoke the tool logic"""
        pass

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
