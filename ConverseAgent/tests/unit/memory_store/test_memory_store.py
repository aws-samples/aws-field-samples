from converseagent.memory import BaseMemory
from converseagent.memory_store import BaseMemoryStore
from converseagent.messages import UserMessage


class TestBaseMemoryStore:
    """Tests the BaseMemoryStore"""

    def test_save_load_memory(self):
        """Tests the load_memory method"""
        memory_store = BaseMemoryStore()
        memory = BaseMemory()
        session_id = "test"

        user_message = UserMessage(text="Hi")
        memory.append(message=user_message)

        memory_store.save_memory(session_id=session_id, memory=memory)

        assert memory_store.load_memory(session_id=session_id) == memory
