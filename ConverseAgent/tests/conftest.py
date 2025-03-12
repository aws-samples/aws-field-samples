import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

from unittest.mock import Mock

import pytest


@pytest.fixture
def data_dir():
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")


@pytest.fixture
def sample_text():
    return {"text": "This is a sample text."}


@pytest.fixture
def sample_image(data_dir):
    return {
        "uri": f"file://{data_dir}/sample_image.png",
        "extension": "png",
        "filename": "sample_image.png",
        "name": "sample_image.png",
    }


@pytest.fixture
def sample_pdf(data_dir):
    return {
        "uri": f"file://{data_dir}/sample_pdf_doc.pdf",
        "extension": "pdf",
        "filename": "sample_pdf_doc.pdf",
        "name": "sample_pdf_doc.pdf",
    }


@pytest.fixture
def sample_tool_use():
    return {
        "tool_use_id": "some_id",
        "tool_name": "some_tool",
        "tool_input": {"key1": "value1", "key2": "value2"},
    }


@pytest.fixture
def sample_assistant_text():
    sample_current_plan = """
    <current_plan>
    1. Step 1
    2. Step 2
    </current_plan>
    """

    sample_update_message = """
    <update_message>
    <headline>Update headline</headline>
    <body>This is a test</body>
    </update_message>
    """

    sample_final_response = """
    <final_response>
    Successful test
    </final_response>
    """

    sample_thinking = """
    <thinking>
    This is a test
    </thinking>
    """

    text = (
        sample_current_plan
        + sample_update_message
        + sample_final_response
        + sample_thinking
    )

    return text


@pytest.fixture
def mock_client(mock_converse_response_simple_text):
    client = Mock()
    client.converse.return_value = mock_converse_response_simple_text

    return client


@pytest.fixture
def mock_converse_response_simple_text(sample_assistant_text):
    converse_response = {
        "output": {"message": {"content": [{"text": sample_assistant_text}]}},
        "stopReason": "end_turn",
        "ResponseMetadata": {"RequestId": "request123"},
        "usage": {"inputTokens": 1000, "outputTokens": 50, "totalTokens": 50},
    }

    return converse_response


@pytest.fixture
def embedding_model_id():
    return "amazon.titan-embed-text-v2:0"


@pytest.fixture
def text_model_id():
    return "anthropic.claude-3-haiku-20240307-v1:0"
