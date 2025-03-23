import pytest

from converseagent.explainability.invocation_history import (
    BaseInvocationHistory,
    BaseInvocationLog,
)

from converseagent.messages import UserMessage, AssistantMessage


@pytest.fixture
def sample_log():
    log_dict = {
        "request_id": "id123",
        "input_messages": [UserMessage(text="Hi")],
        "output_message": AssistantMessage(text="I'm good, you?"),
        "input_tokens": 1,
        "output_tokens": 4,
        "total_tokens": 5,
        "update_message": "Update message here",
        "thinking": "Thinking here",
        "final_response": "Final response here",
        "current_plan": "current plan here",
    }

    log = BaseInvocationLog(**log_dict)

    return log


class TestBaseInvocationHistory:
    """Tests the BaseInvocationHistory class"""

    def test_append_retrieve(self, sample_log):
        """Tests the append method"""
        invocation_history = BaseInvocationHistory()
        invocation_history.append(log=sample_log)

        assert invocation_history.get_history() == [sample_log]

    def test_token_count(self, sample_log):
        invocation_history = BaseInvocationHistory()
        invocation_history.append(log=sample_log)

        usage = invocation_history.get_cumulative_token_count()

        assert usage["total_tokens"] == 5
