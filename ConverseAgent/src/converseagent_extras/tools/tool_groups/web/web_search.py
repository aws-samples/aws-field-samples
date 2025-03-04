import json
import os
from typing import Optional

import requests
from pydantic import Field, model_validator

from converseagent.tools.base import BaseTool, BaseToolGroup
from converseagent.tools.tool_response import ResponseStatus, TextToolResponse


class WebSearchToolGroup(BaseToolGroup):
    """Tools for searching the web

    Args:
        brave_api_key (str, optional): API key for Brave Search. You must
            specify a Brave API search key or specify BRAVE_API_KEY
            environment variable.

    """

    name: str = "web_search_tools"
    description: str = "Tools for searching the internet using Brave Search API"
    instructions: str = """
    Use this tool to search the internet using the Brave Search API.
    You can specify the search query and the number of results to return.
    Make sure to try and retrieve the actual content from the URLs returned by the search.
    
    
    Search operators are special commands you can use to filter search results. They help to find only the search results that you want by limiting and focusing your search. You can place them anywhere in your query, either before or after the search terms.

    ext: Returns web pages with a specific file extension. Example: to find the Honda GX120 Owner’s manual in PDF, type “Honda GX120 ownners manual ext:pdf”.
    filetype: Returns web pages created in the specified file type. Example: to find a web page created in PDF format about the evaluation of age-related cognitive changes, type “evaluation of age cognitive changes filetype:pdf”.
    inbody: Returns web pages containing the specified term in the body of the page. Example: to find information about the Nvidia GeForce GTX 1080 Ti, making sure the page contains the keywords “founders edition” in the body, type “nvidia 1080 ti inbody:“founders edition””.
    intitle: Returns webpages containing the specified term in the title of the page. Example: to find pages about SEO conferences making sure the results contain 2023 in the title, type “seo conference intitle:2023”.
    inpage: Returns webpages containing the specified term either in the title or in the body of the page. Example: to find pages about the 2024 Oscars containing the keywords “best costume design” in the page, type “oscars 2024 inpage:“best costume design””.
    lang or language: Returns web pages written in the specified language. The language code must be in the ISO 639-1 two-letter code format. Example: to find information on visas only in Spanish, type “visas lang:es”.
    loc or location: Returns web pages from the specified country or region. The country code must be in the ISO 3166-1 alpha-2 format. Example: to find web pages from Canada about the Niagara Falls, type “niagara falls loc:ca”.
    site: Returns web pages coming only from a specific web site. Example: to find information about Goggles only on Brave pages, type “goggles site:brave.com”.
    +: Returns web pages containing the specified term either in the title or the body of the page. Example: to find information about FreeSync GPU technology, making sure the keyword “FreeSync” appears in the result, type “gpu +freesync”.
    -: Returns web pages not containing the specified term neither in the title nor the body of the page. Example: to search web pages containing the keyword “office” while avoiding results with the term “Microsoft”, type “office -microsoft”.
    "": Returns web pages containing only exact matches to your query. Example: to find web pages about Harry Potter only containing the keywords “order of the phoenix” in that exact order, type “harry potter “order of the phoenix””.
    Additionally, you can use logical operators in your queries. They are special words that allow you to combine and refine the output of search operators.

    AND: Only returns web pages meeting all the conditions. Example: to search for information on visas in English in web pages from the United Kingdom, type “visa loc:gb AND lang:en”.
    OR: Returns web pages meeting any of the conditions. Example: to search for travelling requirements for Australia or New Zealand, type “travel requirements inpage:australia OR inpage:“new zealand””.
    NOT: Returns web pages which do not meet the specified condition(s). Example: to search for information on Brave Search, but you want to exclude results from brave.com, type “brave search NOT site:brave.com”.

    """

    brave_api_key: str | None = Field(
        default=None, description="The Brave API key to use"
    )

    @model_validator(mode="after")
    def validate_tools(self):
        """Check if tools are passed, otherwise add tools"""

        if self.brave_api_key is None:
            self.brave_api_key = os.environ.get("BRAVE_API_KEY")
            if not self.brave_api_key:
                raise ValueError(
                    "Brave API key is required. Set it in the environment variable BRAVE_API_KEY or pass it to the constructor."
                )

        if not self.tools:
            self.tools = [BraveSearchTool(brave_api_key=self.brave_api_key)]

        return self


class BraveSearchTool(BaseTool):
    """Uses the Brave Search engine"""

    name: str = "brave_search"
    description: str = "Use this tool to search the internet using the Brave Search API"
    brave_api_key: str | None = Field(
        default=None, description="The Brave API key to use"
    )

    @model_validator(mode="after")
    def validate_tool(self):
        """Check if tools are passed, otherwise add tools"""

        if self.brave_api_key is None:
            self.brave_api_key = os.environ.get("BRAVE_API_KEY")
            if not self.brave_api_key:
                raise ValueError(
                    "Brave API key is required. Set it in the environment variable BRAVE_API_KEY or pass it to the constructor."
                )
        return self

    def invoke(self, *args, **kwargs) -> TextToolResponse:
        """Invokes the tool logic"""

        return self.search(*args, **kwargs)

    def search(self, query: str, num_results: int = 10) -> TextToolResponse:
        """Searches using the Brave Search API and returns results

        Args:
            query (str): The search query
            num_results (int, optional): The number of search results to return.
                Defaults to 10.

        Returns:
            TextToolResponse: The response from the tool containing the search
                results
        """

        url = "https://api.search.brave.com/res/v1/web/search"
        headers = {
            "Accept": "application/json",
            "X-Subscription-Token": self.brave_api_key,
        }
        params = {"q": query, "count": num_results}

        try:
            response = requests.get(url, headers=headers, params=params, timeout=60)

            if response.status_code == 200:
                results = response.json().get("web", {}).get("results", [])

                parsed_results = [
                    {
                        "title": result["title"],
                        "url": result["url"],
                        "snippet": result["description"],
                    }
                    for result in results
                ]

                return TextToolResponse(
                    ResponseStatus.SUCCESS, json.dumps(parsed_results)
                )

            else:
                return TextToolResponse(
                    ResponseStatus.ERROR,
                    f"Search failed with status code {response.status_code}",
                )

        except Exception as e:
            return TextToolResponse(
                ResponseStatus.ERROR, f"Search encountered an error: {e}"
            )

    def get_tool_spec(self):
        return {
            "toolSpec": {
                "name": self.name,
                "description": self.description,
                "inputSchema": {
                    "json": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "The search query",
                            },
                            "num_results": {
                                "type": "integer",
                                "description": "The number of search results to return",
                                "default": 10,
                            },
                        },
                        "required": ["query"],
                    }
                },
            }
        }
