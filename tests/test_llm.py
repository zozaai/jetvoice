import pytest
from unittest.mock import MagicMock, patch
from jetvoice.llm import JetVoiceLLM

@patch('jetvoice.llm.llm.openai')
def test_llm_class_success(mock_openai):
    """
    Test that JetVoiceLLM.ask returns text when OpenAI responds successfully.
    """
    # 1. Setup Mock Response
    mock_response = MagicMock()
    mock_response.choices = [MagicMock(message={"content": "Hello human"})]
    
    mock_chat_completion = MagicMock()
    mock_chat_completion.create.return_value = mock_response
    mock_openai.ChatCompletion = mock_chat_completion

    # 2. Instantiate Class with a fake key
    with patch('jetvoice.llm.llm.os.getenv', return_value="sk-fake-key"):
        llm = JetVoiceLLM(system_prompt="You are a test bot")
        
        # 3. Call method
        result = llm.ask("Hi")

    # 4. Assertions
    assert result == "Hello human"
    
    # Verify the parameters sent to OpenAI
    call_args = mock_chat_completion.create.call_args[1]
    assert call_args['model'] == "gpt-5.1"
    assert call_args['messages'][0]['content'] == "You are a test bot"
    assert call_args['messages'][1]['content'] == "Hi"

@patch('jetvoice.llm.llm.openai')
def test_llm_class_api_failure(mock_openai):
    """
    Test graceful failure handling in the class.
    """
    mock_chat_completion = MagicMock()
    mock_chat_completion.create.side_effect = Exception("API Error")
    mock_openai.ChatCompletion = mock_chat_completion

    with patch('jetvoice.llm.llm.os.getenv', return_value="sk-fake-key"):
        llm = JetVoiceLLM()
        result = llm.ask("Hi")

    assert result is None

def test_llm_class_missing_key():
    """
    Test that the class handles missing keys immediately.
    """
    with patch('jetvoice.llm.llm.os.getenv', return_value=None):
        llm = JetVoiceLLM()
        result = llm.ask("Hi")
        assert result is None