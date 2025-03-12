import requests
from html2text import HTML2Text
from pydantic import model_validator

from converseagent.content import TextContentBlock
from converseagent.logging_utils.logger_config import setup_logger
from converseagent.tools.base import BaseTool, BaseToolGroup
from converseagent.tools.tool_response import (
    BaseToolResponse,
    ResponseStatus,
    ResponseType,
)

logger = setup_logger(__name__)


class WebRetrieverToolGroup(BaseToolGroup):
    """A group of tools for retrieving web based content"""

    name: str = "web_retriever_tools"
    description: str = (
        "Tools for retrieving information from the web and testing endpoints"
    )
    instructions: str = """
    When you use the web_tools, if you have multiple URLs to retrieve,
    pass all of the URLs in one request into the retrieve_urls tool.
    You can specify whether to return the content as markdown or raw HTML.
    Use the test_endpoint tool to make HTTP requests to specific endpoints.
    """

    @model_validator(mode="after")
    def validate_tools(self):
        """Check if tools are passed, otherwise add tools"""

        if not self.tools:
            self.tools = [RetrieveUrlTool(metadata=self.metadata)]

        return self

    @classmethod
    def get_tool_group_spec(cls):
        """Returns the tool group spec"""

        return {
            "toolGroupSpec": {
                "name": cls.model_fields["name"].default,
                "description": cls.model_fields["description"].default,
                "inputSchema": {},
            }
        }


class RetrieveUrlTool(BaseTool):
    """Retrieves the given Url"""

    name: str = "retrieve_urls"
    description: str = "Use this tool to retrieve the contents of one or more URLs"

    def invoke(self, *args, **kwargs) -> BaseToolResponse:
        """Invokes the tool logic"""

        return self.retrieve_urls(*args, **kwargs)

    def retrieve_url(self, url, markdown=True) -> TextContentBlock:
        """Retrieves the given url"""

        # Common headers to avoid HTTP errors and mimic a real browser request
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "DNT": "1",  # Do Not Track
            "Upgrade-Insecure-Requests": "1",
        }

        try:
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            if markdown:
                h = HTML2Text()
                h.ignore_links = False
                h.ignore_images = False
                return TextContentBlock(
                    text=h.handle(response.text), metadata=self.metadata
                )
            else:
                return TextContentBlock(text=response.text, metadata=self.metadata)

        except Exception as e:
            logger.error(f"Error retrieving URL {url}: {e}")
            return TextContentBlock(text=f"Error retrieving URL {url}: {e}")

    def retrieve_urls(self, urls, markdown=True):
        """Retrieves the given urls

        Args:
            urls (list): A list of URLs to retrieve
        """
        contents = []
        for url in urls:
            contents.append(self.retrieve_url(url))

        tool_response = BaseToolResponse(
            status=ResponseStatus.SUCCESS,
            type=ResponseType.CONTENT,
            content=contents,
            metadata=self.metadata,
        )

        return tool_response

    def get_tool_spec(self):
        return {
            "toolSpec": {
                "name": self.name,
                "description": self.description,
                "inputSchema": {
                    "json": {
                        "type": "object",
                        "properties": {
                            "urls": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "A list of URLs to retrieve",
                            },
                            "markdown": {
                                "type": "boolean",
                                "description": "Whether to return the content as markdown (True) or raw HTML (False)",
                                "default": True,
                            },
                        },
                        "required": ["urls"],
                    }
                },
            }
        }
