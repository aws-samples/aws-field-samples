from typing import List, Union

from converseagent.content import AssistantContentBlock, UserContentBlock
from converseagent.messages import Message

ContentBlock = Union[UserContentBlock, AssistantContentBlock]


def delete_tool_result_blocks_after_next_turn(messages: List[Message]) -> List[Message]:
    """Deletes content blocks in ToolResultContentBlock that has a retention of "after_next_turn"

    The ContentBlock must have metadata with "retention": "after_next_turn"

    Args:
        messages (List[Message]): The messages list

    Returns
        List[Message]: The messages list with the content blocks removed
    """
    processed_messages = []

    for message in messages:
        # Create deep copy of the message
        processed_message = message.model_copy(deep=True)

        processed_content = []
        # Loop through each content block in the content
        for content_block in processed_message.content:
            # Check if retention is set to "after_next_turn"
            if not (
                "retention" in content_block.metadata
                and content_block.metadata["retention"] == "after_next_turn"
            ):
                # Process any tool result content blocks

                if content_block.type == "tool_result":
                    # Create new filtered list
                    content_block.tool_result_content = [
                        block
                        for block in content_block.tool_result_content
                        if not (
                            "retention" in block.metadata
                            and block.metadata["retention"] == "after_next_turn"
                        )
                    ]
                processed_content.append(content_block)
        processed_message.content = processed_content  # type: ignore
        processed_messages.append(processed_message)
    return processed_messages
