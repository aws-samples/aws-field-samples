from datetime import datetime
from io import BytesIO
from time import sleep
from typing import Any, Dict, List, Union

import pyautogui
from PIL import ImageDraw
from pydantic import Field, model_validator

from converseagent.content import ImageContentBlock
from converseagent.logging_utils.logger_config import setup_logger
from converseagent.tools.base import BaseTool, BaseToolGroup, BaseToolResponse
from converseagent.tools.tool_response import (
    ResponseStatus,
    ResponseType,
    TextToolResponse,
)

logger = setup_logger(__name__)


class ComputerToolGroup(BaseToolGroup):
    """Tools for controlling computer and taking screenshots"""

    name: str = "computer_tools"
    description: str = "Tools for controlling the computer and taking screenshots"
    instructions: str = """
    Use this tool group to control the computer mouse and take screenshots.
    You can move the cursor to specific coordinates, perform different types of clicks, and capture screenshots.
    """
    scale_factor: float = Field(
        default=1.0, description="Scaling factor to scale the screenshot and mouse"
    )

    @model_validator(mode="after")
    def _validate_tools(self):
        """Check if tools are passed, otherwise add tools"""
        if not self.tools:
            self.tools = [
                MouseMoveTool(scale_factor=self.scale_factor, metadata=self.metadata),
                ClickTool(scale_factor=self.scale_factor, metadata=self.metadata),
                # ScreenshotTool(scale_factor=self.scale_factor, metadata=self.metadata),
                TypeTool(scale_factor=self.scale_factor, metadata=self.metadata),
                ScrollTool(scale_factor=self.scale_factor, metadata=self.metadata),
            ]
        return self

    @classmethod
    def get_tool_group_spec(cls):
        return {
            "toolSpec": {
                "name": cls.name,
                "description": cls.description,
            }
        }


class MouseMoveTool(BaseTool):
    """Tool to move the mouse cursor to specific coordinates"""

    name: str = "mouse_move"
    description: str = "Move the mouse cursor to the specified x, y coordinates"
    scale_factor: float = Field(
        default=1.0, description="Scaling factor to scale the screenshot and mouse"
    )

    def invoke(self, *args, **kwargs) -> TextToolResponse:
        """Invokes the tool logic"""
        return self.mouse_move(*args, **kwargs)

    def mouse_move(self, coordinate: tuple[int, int]) -> TextToolResponse:
        """Moves the mouse cursor to the specified coordinates

        Args:
            coordinates (tuple[int,int]): The x,y coordinates to move the mouse to

        Returns:
            TextToolResponse: Success or error message
        """
        try:
            # Use pyautogui to move the mouse cursor to the specified coordinates
            # Need to be divided by 2 and also divided by the scale factor due to
            # image resizing for Claude
            x = coordinate[0]
            y = coordinate[1]
            pyautogui.moveTo(x / 2 / self.scale_factor, y / 2 / self.scale_factor)
            logger.info(f"Moving mouse to coordinates: ({x}, {y})")

            return TextToolResponse(
                ResponseStatus.SUCCESS,
                f"Mouse moved to coordinates: ({x}, {y})",
                metadata=self.metadata,
            )
        except Exception as e:
            logger.error(f"Failed to move mouse: {str(e)}")
            return TextToolResponse(
                ResponseStatus.ERROR, f"Failed to move mouse: {str(e)}"
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
                            "coordinate": {
                                "type": "array",
                                "description": "(x, y): The x (pixels from the left edge) and y (pixels from the top edge) coordinates to move the mouse to.",
                                "items": {
                                    "type": "integer",
                                },
                            },
                        },
                        "required": ["coordinate"],
                    }
                },
            }
        }


class ClickTool(BaseTool):
    """Tool to perform different types of mouse clicks at the current or specified coordinates"""

    name: str = "click"
    description: str = (
        "Perform different types of mouse clicks (left, right, or double left) "
        "at the current cursor position or specified coordinates"
    )
    scale_factor: float = Field(
        default=1.0, description="Scaling factor to scale the screenshot and mouse"
    )

    def invoke(self, *args, **kwargs) -> TextToolResponse:
        """Invokes the tool logic"""
        return self.click(*args, **kwargs)

    def click(
        self, click_type: str = "left", coordinate: tuple[int, int] | None = None
    ) -> TextToolResponse:
        """Performs the specified type of click at current position or given coordinates
        Args:
            click_type (str): Type of click to perform ('left_click', 'right_click', 'double_click')
            coordinate (tuple[int, int]: The coordinate to move the mouse to and click

        Returns:
            TextToolResponse: Success or error message
        """
        valid_click_types = ["left_click", "right_click", "double_click"]

        if click_type not in valid_click_types:
            return TextToolResponse(
                ResponseStatus.ERROR,
                f"Invalid click type. Must be one of: {', '.join(valid_click_types)}",
            )

        try:
            # Move to specified coordinates if both x and y are provided
            if coordinate:
                x = coordinate[0]
                y = coordinate[1]
                x_scaled = x / 2.0 / self.scale_factor
                y_scaled = y / 2.0 / self.scale_factor
                pyautogui.moveTo(x_scaled, y_scaled)
                location_msg = f" at coordinates ({x_scaled}, {y_scaled})"
            else:
                location_msg = " at current cursor position"

            # Use appropriate pyautogui function based on click type
            if click_type == "left_click":
                pyautogui.click()
            elif click_type == "right_click":
                pyautogui.rightClick()
            elif click_type == "double_click":
                pyautogui.doubleClick()

            logger.info(f"Performed {click_type} click{location_msg}")

            return TextToolResponse(
                ResponseStatus.SUCCESS,
                f"Performed {click_type} click{location_msg} successfully",
                metadata=self.metadata,
            )
        except Exception as e:
            logger.error(f"Failed to perform {click_type} click: {str(e)}")
            return TextToolResponse(
                ResponseStatus.ERROR, f"Failed to perform {click_type} click: {str(e)}"
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
                            "click_type": {
                                "type": "string",
                                "description": "Type of click to perform",
                                "enum": ["left_click", "right_click", "double_click"],
                                "default": "left_click",
                            },
                            "coordinate": {
                                "type": "array",
                                "description": "(x, y): The x (pixels from the left edge) and y (pixels from the top edge) coordinates to move the mouse to.",
                                "optional": True,
                            },
                        },
                        "required": ["click_type"],
                    }
                },
            }
        }


class ScreenshotTool(BaseTool):
    """Tool to take full page screenshots"""

    name: str = "screenshot"
    description: str = "Take a full page screenshot of the entire screen. The red circle indicates current mouse position."
    scale_factor: float = Field(
        default=1.0, description="Scaling factor to scale the screenshot and mouse"
    )

    def invoke(self, *args, **kwargs) -> BaseToolResponse:
        """Invokes the tool logic"""
        return self.take_screenshot(*args, **kwargs)

    def take_screenshot(self) -> BaseToolResponse:
        """Takes a screenshot of the entire screen and draws a red circle at the current mouse position

        Args:
            filename (str, optional): Optional filename for the screenshot.
                                     If not provided, a timestamp-based name will be used.

        Returns:
            BaseToolResponse: Response containing an ImageContentBlock with the screenshot
        """
        try:
            # Generate a timestamp-based filename if none is provided
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"screenshot_{timestamp}"

            # Take the screenshot using pyautogui
            screenshot_img = pyautogui.screenshot()

            # Get the current mouse position
            mouse_x, mouse_y = pyautogui.position()

            # TODO bug in pyautogui, need to be multiplied by 2
            mouse_x *= 2
            mouse_y *= 2

            # Draw a small red circle at the mouse cursor position

            draw = ImageDraw.Draw(screenshot_img)
            circle_radius = 10
            draw.ellipse(
                (
                    mouse_x - circle_radius,
                    mouse_y - circle_radius,
                    mouse_x + circle_radius,
                    mouse_y + circle_radius,
                ),
                fill="red",
                outline="red",
            )

            # Scale so that the long edge is no more than 1568 px

            # Given some screen resolution (e.g., 2880*1800), determine the scaling
            # factor to scale the image proportionately so that the long edge
            # is no more than 1568 px

            # max_size = 1568
            # if screenshot_img.width > max_size or screenshot_img.height > max_size:
            #     scale_factor = min(
            #         max_size / screenshot_img.width, max_size / screenshot_img.height
            #     )
            #     new_width = int(screenshot_img.width * scale_factor)
            #     new_height = int(screenshot_img.height * scale_factor)
            #     screenshot_img = screenshot_img.resize((new_width, new_height))

            # Convert the PIL Image to bytes
            img_byte_arr = BytesIO()
            screenshot_img.save(img_byte_arr, format="PNG")
            screenshot_bytes = img_byte_arr.getvalue()

            # Create an ImageContentBlock with the screenshot bytes
            screenshot_block = ImageContentBlock(
                filename=filename,
                extension="png",
                content_bytes=screenshot_bytes,
                metadata={"retention": "after_next_turn"},
            )

            logger.info("Screenshot taken successfully")

            return BaseToolResponse(
                status=ResponseStatus.SUCCESS,
                type=ResponseType.CONTENT,
                content=[screenshot_block],
                metadata=self.metadata,
            )
        except Exception as e:
            logger.error(f"Failed to take screenshot: {str(e)}")
            return TextToolResponse(
                ResponseStatus.ERROR, f"Failed to take screenshot: {str(e)}"
            )

    def get_tool_spec(self):
        return {
            "toolSpec": {
                "name": self.name,
                "description": self.description,
                "inputSchema": {
                    "json": {
                        "type": "object",
                        "properties": {},
                    }
                },
            }
        }


class TypeTool(BaseTool):
    """Tool to perform keyboard inputs"""

    name: str = "type"
    description: str = "Type text or press specific keyboard keys"

    def invoke(self, *args, **kwargs) -> TextToolResponse:
        """Invokes the tool logic"""
        return self.keyboard_input(*args, **kwargs)

    def keyboard_input(self, text: str = None, key: str = None) -> TextToolResponse:
        """Types text or presses a specific key

        Args:
            text (str, optional): Text to type out
            key (str, optional): Specific key to press (e.g. 'enter', 'tab', 'esc')

        Returns:
            TextToolResponse: Success or error message
        """
        try:
            if text:
                # Type out the provided text
                pyautogui.write(text)
                logger.info(f"Typed text: {text}")
                return TextToolResponse(
                    ResponseStatus.SUCCESS,
                    f"Successfully typed text: {text}",
                    metadata=self.metadata,
                )
            elif key:
                # Press the specified key
                pyautogui.press(key)
                logger.info(f"Pressed key: {key}")
                return TextToolResponse(
                    ResponseStatus.SUCCESS,
                    f"Successfully pressed key: {key}",
                    metadata=self.metadata,
                )
            else:
                return TextToolResponse(
                    ResponseStatus.ERROR,
                    "Must provide either text to type or key to press",
                )
        except Exception as e:
            logger.error(f"Failed to perform keyboard input: {str(e)}")
            return TextToolResponse(
                ResponseStatus.ERROR, f"Failed to perform keyboard input: {str(e)}"
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
                            "text": {
                                "type": "string",
                                "description": "Text to type out",
                            },
                            "key": {
                                "type": "string",
                                "description": "Specific key to press (e.g. 'enter', 'tab', 'esc')",
                            },
                        },
                    }
                },
            }
        }


class ScrollTool(BaseTool):
    """Tool to scroll the screen in different directions"""

    name: str = "scroll"
    description: str = (
        "Scroll the screen up, down, left, or right by a specified amount"
    )

    def invoke(self, *args, **kwargs) -> TextToolResponse:
        """Invokes the tool logic"""
        return self.scroll(*args, **kwargs)

    def scroll(self, direction: str, amount: int = 100) -> TextToolResponse:
        """Scrolls the screen in the specified direction

        Args:
            direction (str): Direction to scroll ('up', 'down', 'left', 'right')
            amount (int): Number of pixels to scroll, default 100

        Returns:
            TextToolResponse: Success or error message
        """
        valid_directions = ["up", "down", "left", "right"]

        if direction not in valid_directions:
            return TextToolResponse(
                ResponseStatus.ERROR,
                f"Invalid scroll direction. Must be one of: {', '.join(valid_directions)}",
            )

        try:
            if direction == "up":
                pyautogui.scroll(amount)  # Positive for up
            elif direction == "down":
                pyautogui.scroll(-amount)  # Negative for down
            elif direction == "left":
                pyautogui.hscroll(-amount)  # Negative for left
            elif direction == "right":
                pyautogui.hscroll(amount)  # Positive for right

            logger.info(f"Scrolled {direction} by {amount} pixels")

            return TextToolResponse(
                ResponseStatus.SUCCESS,
                f"Successfully scrolled {direction} by {amount} pixels",
                metadata=self.metadata,
            )
        except Exception as e:
            logger.error(f"Failed to scroll {direction}: {str(e)}")
            return TextToolResponse(
                ResponseStatus.ERROR, f"Failed to scroll {direction}: {str(e)}"
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
                                "description": "Direction to scroll - up, down, left, or right",
                                "enum": ["up", "down", "left", "right"],
                            },
                            "amount": {
                                "type": "integer",
                                "description": "Number of pixels to scroll",
                                "default": 100,
                            },
                        },
                        "required": ["direction"],
                    }
                },
            }
        }
