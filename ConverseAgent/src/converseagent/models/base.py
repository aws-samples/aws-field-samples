import asyncio
from abc import ABC, abstractmethod

from pydantic import BaseModel

from converseagent.models.request import ModelRequest
from converseagent.models.response import ModelResponse


class BaseChatModel(BaseModel, ABC):
    """The base chat model abstract class.

    Child classes must implement the converse method.
    """

    @abstractmethod
    def invoke(
        self,
        model_request: ModelRequest,
    ) -> ModelResponse:
        """Invokes the model

        Args:
            model_request (ModelRequest): The request to the model

        Returns:
            ModelResponse: The response from the model

        """
        pass

    async def ainvoke(
        self,
        model_request: ModelRequest,
    ) -> ModelResponse:
        """Invokes the model asynchronously.

        Override this to provide an async implementation.
        Otherwise this will run invoke in an ThreadPoolExecutor

        Args:
            model_request (ModelRequest): The request to the model

        Returns:
            ModelResponse: The response from the model

        """
        loop = asyncio.get_running_loop()
        model_response = await loop.run_in_executor(None, self.invoke, model_request)

        return model_response
