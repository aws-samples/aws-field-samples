from typing import Dict

from pydantic import BaseModel, Field

from converseagent.memory import BaseMemory


class BaseMemoryStore(BaseModel):
    """Base memory store for saving and loading multiple memories in memory.

    By providing a session_id, you can retrieve BaseMemory objects to be used by
    agents or save the memory. The BaseMemoryStore will store memories in-memory.

    Attributes:
        memory_index (Dict[str, BaseMemory]): The dict containing the BaseMemory objects
    """

    memory_index: Dict[str, BaseMemory] = Field(default_factory=dict)

    def load_memory(self, session_id: str) -> BaseMemory:
        """Returns a memory based on session ID

        Args:
            session_id (str): The session id for the memory

        Returns:
            BaseMemory: the BaseMemory object
        """

        if session_id in self.memory_index:
            return self.memory_index[session_id]
        else:
            raise KeyError("Session id %s not found in memory story.", session_id)

    def save_memory(self, session_id: str, memory: BaseMemory):
        """Saves a memory to the memory store

        Args:
            session_id (str): The session id for the memory
            memory (BaseMemory): The memory to save
        """
        self.memory_index.update({session_id: memory})
