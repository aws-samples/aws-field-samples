from datetime import datetime
from io import BytesIO
from time import sleep

import pyautogui  # type: ignore
from PIL import ImageDraw
from pydantic import Field

from converseagent.agents import BaseAgent
from converseagent.content import ImageContentBlock, TextContentBlock
from converseagent.context.management.retention import (
    delete_tool_result_blocks_after_next_turn,
)
from converseagent.logging_utils.logger_config import setup_logger
from converseagent_extras.tools.tool_groups.computer import ComputerToolGroup

logger = setup_logger(__name__)


class ComputerAgent(BaseAgent):
    """Specialized agent for computer use"""

    scale_factor: float = Field(
        default=1.0, description="Scaling factor to scale the screenshot and mouse"
    )

    def model_post_init(self, *args, **kwargs):
        super().model_post_init(*args, **kwargs)

        # Determine scale factor
        # Take the screenshot using pyautogui
        screenshot_img = pyautogui.screenshot()
        logger.info(f"Screen size: {screenshot_img.size}")
        self.scale_factor = calculate_scale_factor(
            screenshot_img.width, screenshot_img.height
        )
        logger.info(f"Scale factor: {self.scale_factor:0.2f}")

        # Add tools
        self.add_tool_groups([ComputerToolGroup(scale_factor=self.scale_factor)])

    def _post_invocation_processing(self):
        logger.info("Executing post-invocation steps")
        self.set_messages(
            delete_tool_result_blocks_after_next_turn(self.get_messages())
        )

        self.update_callback(self.get_messages()[-1].update_message)

    def _final_processing(self):
        # Adds the screenshot of the page to the last message
        logger.info("Adding screenshot to last message")

        # Get scaled mouse position
        mouse_x, mouse_y = pyautogui.position()
        mouse_x_scaled = int(mouse_x * 2 * self.scale_factor)
        mouse_y_scaled = int(mouse_y * 2 * self.scale_factor)

        # Provide some time for any screen action to complete after click
        sleep(1)

        self.get_messages()[-1].append_content(self._get_screenshot())
        self.get_messages()[-1].append_content(
            TextContentBlock(
                text=f"Current Mouse position: ({mouse_x_scaled}, {mouse_y_scaled})",
                metadata={"retention": "after_next_turn"},
            )
        )

    def _get_screenshot(self) -> ImageContentBlock:
        # Generate a timestamp-based filename if none is provided
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"screenshot_{timestamp}"

        # Take the screenshot using pyautogui
        screenshot_img = pyautogui.screenshot()

        logger.info(f"Screen size: {screenshot_img.size}")
        logger.info(f"Scale factor: {self.scale_factor:0.2f}")

        # Get the current mouse position
        mouse_x, mouse_y = pyautogui.position()

        # # TODO bug in pyautogui, need to multiply by 2 get position correct
        mouse_x *= 2
        mouse_y *= 2

        logger.info(f"Current mouse position: {mouse_x},{mouse_y}")

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

        # Scale the image by the scale factor
        new_width = int(screenshot_img.width * self.scale_factor)
        new_height = int(screenshot_img.height * self.scale_factor)
        screenshot_img = screenshot_img.resize((new_width, new_height))
        logger.info(f"New image size: {screenshot_img.size}")

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

        return screenshot_block


def calculate_scale_factor(width: int, height: int, max_dimension: int = 1366) -> float:
    """
    Calculate the scaling factor needed to resize an image proportionally
    so its longest edge equals max_dimension.

    Args:
        width: Original image width in pixels
        height: Original image height in pixels
        max_dimension: Maximum allowed dimension (default 1568)

    Returns:
        float: Scaling factor to apply to both dimensions
    """
    # Find the longer edge
    longest_edge = max(width, height)

    # If the image is already smaller than max_dimension, return 1
    if longest_edge <= max_dimension:
        return 1.0

    # Calculate the scale factor
    scale_factor = max_dimension / longest_edge

    return scale_factor
