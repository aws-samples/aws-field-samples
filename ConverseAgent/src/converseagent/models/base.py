from abc import ABC, abstractmethod
from typing import Any, Dict, List

from pydantic import BaseModel


class BaseChatModel(BaseModel, ABC):
    """The base chat model abstract class.

    Child classes must implement the converse method.
    """

    @abstractmethod
    def invoke(
        self,
        messages: List[dict],
        system: List[Dict[str, str]],
        inference_config: Dict[str, str | int],
        tool_config: Dict[str, List[Any]],
    ) -> Dict:
        """Invokes the model

        Attributes:
            messages (List[dict]): The list of alternating User and Assistant
                messages in Converse format.
            system (List[Dict[str, str]): A list of ContentBlock with text content
                for the system prompt.
            inference_config (Dict[str, str | int]): The inferenceConfig following
                Converse API inferenceConfig format.
            tool_config (Dict[str, List[Any]]): The toolConfig following
                Converse API toolConfig format.
        """
        pass
