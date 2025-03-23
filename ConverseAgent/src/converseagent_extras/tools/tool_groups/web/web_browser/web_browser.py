import asyncio
import math
from io import BytesIO
from time import sleep
from typing import Any, Dict, List, Literal

from PIL import Image
from playwright.async_api import Browser, Page, Playwright, async_playwright
from pydantic import BaseModel, ConfigDict, Field, model_validator

from converseagent.content import ImageContentBlock, TextContentBlock
from converseagent.logging_utils.logger_config import setup_logger
from converseagent.tools.base import BaseTool, BaseToolGroup, BaseToolResponse
from converseagent.tools.tool_response import (
    ResponseStatus,
    ResponseType,
    TextToolResponse,
)

logger = setup_logger(__name__)


def bucket_elements(elements, bucket_size=50):
    """Orders the interactable elements by its y coordinate first then x while grouping
    them into the given bucket_size
    """

    # Function to round to nearest bucket_size
    def round_to_nearest(value, bucket_size):
        return round(value / bucket_size) * bucket_size

    # Create a dictionary to hold our buckets
    buckets = {}

    # Assign each element to a bucket based on rounded x,y coordinates
    for element in elements:
        # Get the center x,y coordinates from the bbox
        x = element["bbox"]["x"]
        y = element["bbox"]["y"]

        # Round to the nearest bucket_size
        bucket_x = round_to_nearest(x, bucket_size)
        bucket_y = round_to_nearest(y, bucket_size)

        # Create a bucket key - y first, then x for sorting
        bucket_key = (bucket_y, bucket_x)

        # Add to the appropriate bucket
        if bucket_key not in buckets:
            buckets[bucket_key] = []
        buckets[bucket_key].append(element)

    # Sort the buckets by y first and then by x
    sorted_keys = sorted(buckets.keys())

    # Create the final sorted list
    result = []
    for key in sorted_keys:
        result.extend(buckets[key])

    return result


class BrowserContext(BaseModel):
    """Contains the Browser object and other state metadata required
    for the tools to function.
    """

    playwright: Playwright = Field(default=None)
    browser: Browser = Field(default=None, description="The Playwright Browser object")
    current_page: Page = Field(
        default=None, description="The current page in the browser"
    )
    interactable_elements: List[dict] = Field(
        default=[], description="The current interactable elements on the page"
    )
    page_screenshots: List[bytes] = Field(
        default=[], description="The current page screenshots"
    )

    browsing_strategy: Literal["full", "partial"] = Field(
        default="full", description="full for full-page, partial for viewport only"
    )

    viewport_width: int = Field(default=1280, description="The viewport width")
    viewport_height: int = Field(default=800, description="The viewport height")

    browsing_strategy_height_multiple_cutoff: int = Field(
        default=3,
        description="The threshold to switch between full and partial strategies",
    )

    current_page_height: float = Field(
        default=None, description="Scroll height of the current page"
    )

    viewport_position: dict = Field(
        default=None, description="The current viewport position"
    )

    model_config = ConfigDict(
        arbitrary_types_allowed=True,
    )

    headless: bool = Field(default=True, description="Whether to run in headless mode")

    browser_initialized: bool = Field(
        default=False, description="Whether the browser has been initialized"
    )

    async def start(self):
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(headless=self.headless)
        self.browser_initialized = True

    async def update(self):
        logger.info("Updating current browser context")

        # Wait for browser load
        await self.current_page.wait_for_load_state()

        sleep(1)
        # Get page height
        self.current_page_height = await self.current_page.evaluate(
            "document.body.scrollHeight"
        )

        # Get current scroll %
        self.viewport_position = await self.get_viewport_position()

        # Set browsing strategy
        if (
            self.viewport_height * self.browsing_strategy_height_multiple_cutoff
            < self.current_page_height
        ):
            self.browsing_strategy = "partial"
            logger.info("Using partial page browsing strategy")
        else:
            self.browsing_strategy = "full"
            logger.info("Using full page browsing strategy")

        if self.current_page:
            if self.browsing_strategy == "full":
                self.page_screenshots = await self.get_page_screenshots(full_page=True)
                self.interactable_elements = await self.get_interactable_elements(
                    only_viewport_elements=False
                )
            else:
                self.page_screenshots = await self.get_page_screenshots(full_page=False)
                self.interactable_elements = await self.get_interactable_elements(
                    only_viewport_elements=True
                )

    async def ensure_page(self):
        if not self.browser_initialized:
            await self.start()

        if not self.current_page:
            self.current_page = await self.browser.new_page()
            await self.current_page.set_viewport_size(
                {"width": self.viewport_width, "height": self.viewport_height}
            )

    async def close(self):
        if self.browser:
            await self.browser.close()

        if self.playwright:
            await self.playwright.stop()

    async def goto(self, url):
        await self.ensure_page()
        await self.current_page.goto(url=url, wait_until="domcontentloaded")

    async def click(self, element_id):
        for interactable_element in self.interactable_elements:
            if element_id == interactable_element["element_id"]:
                await interactable_element["element"].click()
                await self.current_page.wait_for_load_state("domcontentloaded")
                break

    async def fill(self, element_id, value):
        for interactable_element in self.interactable_elements:
            if element_id == interactable_element["element_id"]:
                await interactable_element["element"].fill(value)
                break

    async def scroll(self, direction, amount):
        if direction.lower() == "up":
            scroll_amount = -amount
        else:
            scroll_amount = amount

        await self.current_page.evaluate(f"window.scrollBy(0, {scroll_amount})")

    async def get_page_screenshots(
        self, max_height=6000, overlap_pixels=100, full_page=True
    ):
        logger.debug("Taking screenshot")
        screenshot = await self.current_page.screenshot(full_page=full_page)
        logger.debug("Successfully taken screenshot")
        image = Image.open(BytesIO(screenshot))
        width, height = image.size
        if height <= max_height:
            logger.debug("Returning one screenshot")
            return [screenshot]
        else:
            logger.debug("Processing screenshot sections")
            # Calculate effective height per section (considering overlap)
            effective_height = max_height - overlap_pixels
            # Calculate number of sections needed
            num_sections = math.ceil((height - overlap_pixels) / effective_height)

            sections = []
            for i in range(num_sections):
                # Calculate coordinates for current section with overlap
                top = max(0, i * effective_height)
                bottom = min(top + max_height, height)

                # Crop section
                section = image.crop((0, top, width, bottom))

                # Convert section back into bytes
                section_byte_arr = BytesIO()
                section.save(section_byte_arr, format=image.format or "PNG")
                section_byte_arr = section_byte_arr.getvalue()

                sections.append(section_byte_arr)

            return sections

    async def get_interactable_elements(
        self, only_visible_elements=True, only_viewport_elements=False
    ):
        """Retrieves interactable elements on the page concurrently
        """
        # roles = ["button", "link", "searchbox", ]
        roles = [
            # Clickable Primary Elements
            "button",
            "link",
            "menuitem",
            "menuitemcheckbox",
            "menuitemradio",
            "option",
            "tab",
            "treeitem",
            # Input/Fillable Elements
            "textbox",
            "searchbox",
            "combobox",
            "spinbutton",
            # Selection Elements
            "checkbox",
            "radio",
            "radiogroup",
            "switch",
            "listbox",
            # Range Elements
            "slider",
            "meter",
            "progressbar",
            # Container Elements with Interactive Parts
            "grid",
            "gridcell",
            "treegrid",
            "toolbar",
            "menu",
            "menubar",
            "tablist",
            "tree",
        ]

        # Gather elements for each role concurrently
        async def process_role(role: str) -> List[Dict[str, Any]]:
            logger.debug(f"Processing {role}")
            elements = await self.current_page.get_by_role(role=role).all()
            elements_text = await self.current_page.get_by_role(
                role=role
            ).all_text_contents()

            # Process each element in the role concurrently
            async def process_element(i: int, element) -> Dict[str, Any] | None:
                logger.debug(f"Processing {role}_{i}")

                if only_visible_elements:
                    try:
                        is_visible = await element.is_visible()

                        if not is_visible:
                            return None
                    except Exception:
                        return None

                try:
                    bbox = await element.bounding_box()
                except Exception:
                    bbox = None

                if bbox is None:
                    return None

                # Check if element is in viewport when using partial browsing strategy
                if self.browsing_strategy == "partial":
                    if bbox["y"] < 0 or bbox["y"] > self.viewport_height:
                        return None

                return {
                    "element_id": f"{role}_{i}",
                    "type": role,
                    "text": elements_text[i],
                    "element": element,
                    "bbox": bbox,
                }

            # Process all elements of this role concurrently
            element_tasks = [
                process_element(i, element) for i, element in enumerate(elements)
            ]
            element_results = await asyncio.gather(*element_tasks)

            # Filter out None results (elements that were skipped)
            return [result for result in element_results if result is not None]

        # Process all roles concurrently
        role_tasks = [process_role(role) for role in roles]
        role_results = await asyncio.gather(*role_tasks)

        # Flatten the results from all roles
        interactable_elements = [
            element for role_elements in role_results for element in role_elements
        ]

        return bucket_elements(interactable_elements)

    async def get_viewport_position(self):
        # Get the total scrollable height
        scroll_height = await self.current_page.evaluate(
            "document.documentElement.scrollHeight"
        )

        # Get the viewport height
        viewport_height = await self.current_page.evaluate("window.innerHeight")

        # Get the current scroll position
        scroll_top = await self.current_page.evaluate(
            "window.scrollY || document.documentElement.scrollTop"
        )

        # Calculate the bottom position of the viewport
        viewport_bottom = scroll_top + viewport_height

        # Calculate how far through the page you've scrolled (as a percentage)
        scroll_percentage = (
            (scroll_top / (scroll_height - viewport_height)) * 100
            if scroll_height > viewport_height
            else 0
        )

        return {
            "scroll_height": scroll_height,
            "viewport_height": viewport_height,
            "scroll_top": scroll_top,
            "viewport_bottom": viewport_bottom,
            "scroll_percentage": scroll_percentage,
        }

    async def format(self):
        """Formats the browser context to Converse Format"""
        current_url_prompt = f"Current URL: {self.current_page.url}"
        current_url_text_block = TextContentBlock(
            text=current_url_prompt, metadata={"retention": "after_next_turn"}
        )

        current_browsing_strategy_prompt = f"""Current browsing strategy: {self.browsing_strategy}
        Current scroll position: {self.viewport_position["scroll_percentage"]}%
        """
        current_browsing_strategy = TextContentBlock(
            text=current_browsing_strategy_prompt,
            metadata={"retention": "after_next_turn"},
        )

        interactable_elements_prompt = f"Available clickable elements: <elements>{self.interactable_elements}</elements>"
        interactable_elements_text_block = TextContentBlock(
            text=interactable_elements_prompt,
            metadata={"retention": "after_next_turn"},
        )

        screenshot_blocks = [
            ImageContentBlock(
                filename=f"screenshot_{i}",
                extension="png",
                content_bytes=content_bytes,
                metadata={"retention": "after_next_turn"},
            )
            for i, content_bytes in enumerate(self.page_screenshots)
        ]

        content = [
            current_url_text_block,
            current_browsing_strategy,
            interactable_elements_text_block,
        ] + screenshot_blocks

        return content


class WebBrowserToolGroup(BaseToolGroup):
    name: str = "web_browser_tools"
    description: str = "Tools for browsering the web using a web browser"
    instructions: str = """Use these tools to browser the web using a web browser
    It is very important that you optimize your interactions with the web page.
    Whenever possible, you should click on multiple elements in one go rather than
    doing one click at a time. If you can sequence multiple actions, call multiple
    tools in one go (for example, fill and submit).
    """
    browser_context: BrowserContext = Field(default=None)
    headless: bool = Field(default=True, description="Whether to run in headless mode")

    model_config = ConfigDict(
        arbitrary_types_allowed=True,
    )

    def __init__(self, **data):
        super().__init__(**data)

    @classmethod
    async def create(cls, **data):
        """Async factory method to create and initialize the tool group"""
        instance = cls(**data)
        await instance.launch_browser()
        return instance

    async def launch_browser(self):
        """Ensure browser is initialized"""
        if not self.browser_context:
            self.browser_context = BrowserContext(headless=self.headless)
            await self.browser_context.start()

            #  browser reference in tools
            for tool in self.tools:
                tool.browser_context = self.browser_context

    @model_validator(mode="after")
    def initialize_validate_tools(self):
        if not self.tools:
            self.tools = [
                NavigateToUrl(),
                ClickOnElements(),
                FillElement(),
                Scroll(),
                # ClickMouseCoordinatesTool(),
            ]
        return self

    @classmethod
    def get_tool_group_spec(cls):
        return {
            "toolGroupSpec": {
                "name": cls.model_fields["name"].default,
                "description": cls.model_fields["description"].default,
                "inputSchema": {},
            }
        }


class NavigateToUrl(BaseTool):
    name: str = "navigate_to_url"
    description: str = "Navigates to a URL. You must include http:// or https://"
    browser_context: BrowserContext = Field(default=None)
    is_async: bool = True

    model_config = ConfigDict(
        arbitrary_types_allowed=True,
    )

    async def ainvoke(self, *args, **kwargs) -> BaseToolResponse:
        return await self.navigate_to_url(*args, **kwargs)

    async def navigate_to_url(self, url: str) -> BaseToolResponse:
        await self.browser_context.goto(url)

        # Build response content
        content = [
            TextContentBlock(
                text="Navigation executed successfully.",
            )
        ]  # + await self.browser_context.format()

        return BaseToolResponse(
            status=ResponseStatus.SUCCESS, type=ResponseType.CONTENT, content=content
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
                            "url": {
                                "type": "string",
                                "description": "The URL to navigate to",
                            },
                        },
                        "required": ["url"],
                    }
                },
            }
        }


class ClickOnElement(BaseTool):
    name: str = "click_on_element"
    description: str = "Clicks on an element on the page by id with PlayWright"
    browser_context: BrowserContext = Field(default=None)
    is_async: bool = True

    model_config = ConfigDict(
        arbitrary_types_allowed=True,
    )

    async def ainvoke(self, *args, **kwargs) -> BaseToolResponse:
        return await self.click_on_element(*args, **kwargs)

    async def click_on_element(self, element_id: str) -> BaseToolResponse:
        await self.browser_context.click(element_id=element_id)

        return TextToolResponse(
            status=ResponseStatus.SUCCESS,
            text=f"Click executed successfully. Element ID: {element_id}",
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
                            "element_id": {
                                "type": "string",
                                "description": "The id of the element to click such as button_0 and link_0",
                            },
                        },
                        "required": ["element_id"],
                    }
                },
            }
        }


class ClickOnElements(BaseTool):
    name: str = "click_on_elements"
    description: str = (
        "Clicks on one or more elements on the page by id with PlayWright"
    )
    browser_context: BrowserContext = Field(default=None)
    is_async: bool = True

    model_config = ConfigDict(
        arbitrary_types_allowed=True,
    )

    async def ainvoke(self, *args, **kwargs) -> BaseToolResponse:
        return await self.click_on_elements(*args, **kwargs)

    async def click_on_elements(self, element_ids: List[str]) -> BaseToolResponse:
        click_results = []
        for element_id in element_ids:
            try:
                await self.browser_context.click(element_id=element_id)
                click_results.append(
                    TextContentBlock(
                        text=f"Successfully clicked on element ID: {element_id}"
                    )
                )

            except Exception as e:
                click_results.append(
                    TextContentBlock(
                        text=f"Failed to click on element ID: {element_id}. Error: {str(e)}"
                    )
                )

        return BaseToolResponse(
            status=ResponseStatus.SUCCESS,
            type=ResponseType.CONTENT,
            content=click_results,
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
                            "element_ids": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "A list element IDs to click, such as button_0, link_0, etc.",
                            },
                        },
                        "required": ["element_ids"],
                    }
                },
            }
        }


class FillElement(BaseTool):
    name: str = "fill_element"
    description: str = "Fills an element on the page by text with PlayWright"
    browser_context: BrowserContext = Field(default=None)
    is_async: bool = True

    model_config = ConfigDict(
        arbitrary_types_allowed=True,
    )

    async def ainvoke(self, *args, **kwargs) -> BaseToolResponse:
        return await self.fill_element(*args, **kwargs)

    async def fill_element(self, element_id: str, value: str) -> BaseToolResponse:
        await self.browser_context.fill(element_id=element_id, value=value)

        return TextToolResponse(
            status=ResponseStatus.SUCCESS,
            text=f"Fill executed successfully. Element ID: {element_id}",
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
                            "element_id": {
                                "type": "string",
                                "description": "The element_id of the element to fill",
                            },
                            "value": {
                                "type": "string",
                                "description": "The value to fill into the element",
                            },
                        },
                        "required": ["element_id", "value"],
                    }
                },
            }
        }


class ClickMouseCoordinatesTool(BaseTool):
    name: str = "click_mouse_coordinates"
    description: str = "Clicks at specific x,y coordinates on the page"
    browser_context: BrowserContext = Field(default=None)
    is_async: bool = True

    model_config = ConfigDict(
        arbitrary_types_allowed=True,
    )

    async def ainvoke(self, *args, **kwargs) -> BaseToolResponse:
        return await self.click_mouse_coordinates(*args, **kwargs)

    async def click_mouse_coordinates(self, x: int, y: int) -> BaseToolResponse:
        # Access the page's mouse object and click at the specified coordinates
        await self.browser_context.current_page.mouse.click(x, y)

        return TextToolResponse(
            status=ResponseStatus.SUCCESS,
            text=f"Successfully clicked at coordinates x: {x}, y: {y}",
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
                            "x": {
                                "type": "integer",
                                "description": "The x coordinate to click (in pixels)",
                            },
                            "y": {
                                "type": "integer",
                                "description": "The y coordinate to click (in pixels)",
                            },
                        },
                        "required": ["x", "y"],
                    }
                },
            }
        }


class Scroll(BaseTool):
    name: str = "Scroll"
    description: str = "Scrolls the page up or down"
    browser_context: BrowserContext = Field(default=None)
    is_async: bool = True

    model_config = ConfigDict(
        arbitrary_types_allowed=True,
    )

    async def ainvoke(self, *args, **kwargs) -> BaseToolResponse:
        return await self.scroll_page(*args, **kwargs)

    async def scroll_page(self, direction: str, amount: int = 0) -> BaseToolResponse:
        amount = self.browser_context.viewport_height if amount == 0 else amount
        await self.browser_context.scroll(direction=direction, amount=amount)

        return TextToolResponse(
            status=ResponseStatus.SUCCESS,
            text=f"Successfully scrolled {direction} by {amount} pixels.",
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
                            "direction": {
                                "type": "string",
                                "description": "The direction to scroll (up or down)",
                                "enum": ["up", "down"],
                            },
                            "amount": {
                                "type": "integer",
                                "description": "The number of pixels to scroll. Defaults to the height of the current page.",
                            },
                        },
                        "required": ["direction"],
                    }
                },
            }
        }
