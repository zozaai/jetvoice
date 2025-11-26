import os
import pytest
from unittest.mock import MagicMock, patch
from jetvoice.tts.tts import JetVoiceTTS

@pytest.fixture
def mock_environment():
    """
    Forces offline mode for tests to ensure consistent path execution.
    """
    with patch.dict(os.environ, {"TTS_ONLINE": "false", "TTS_RATE": "150"}):
        yield

@pytest.fixture
def mock_pyttsx3_module():
    """
    Patches the entire pyttsx3 module import inside jetvoice.tts.tts.
    This prevents the real engine from ever initializing.
    """
    with patch("jetvoice.tts.tts.pyttsx3") as mock_module:
        # Setup the mock engine that init() returns
        mock_engine = MagicMock()
        mock_engine.getProperty.return_value = [] # Default voices list
        mock_module.init.return_value = mock_engine
        
        yield mock_module, mock_engine

@pytest.fixture
def mock_subprocess():
    """
    Prevents any actual shell commands (espeak/mpg123) from running.
    """
    with patch("jetvoice.tts.tts.subprocess.run") as mock_sub:
        yield mock_sub

def test_tts_init_configure(mock_environment, mock_pyttsx3_module):
    """
    Test that initializing the class sets up the engine properties.
    """
    mock_module, mock_engine = mock_pyttsx3_module
    
    # Act
    tts = JetVoiceTTS()

    # Assert
    assert tts.engine == mock_engine
    mock_module.init.assert_called_once()
    
    # Verify properties were set (checking for 'rate' and 'volume')
    calls = mock_engine.setProperty.call_args_list
    args_called = [c[0][0] for c in calls]
    
    assert 'rate' in args_called
    assert 'volume' in args_called

def test_tts_speak_success(mock_environment, mock_pyttsx3_module, mock_subprocess):
    """
    Test that calling speak() uses the engine's say/runAndWait methods.
    """
    mock_module, mock_engine = mock_pyttsx3_module
    
    # Arrange
    tts = JetVoiceTTS()
    text = "Hello AI"

    # Act
    tts.speak(text)

    # Assert
    mock_engine.say.assert_called_once_with(text)
    mock_engine.runAndWait.assert_called_once()
    
    # Ensure fallback subprocess was NOT called
    mock_subprocess.assert_not_called()

def test_tts_fallback_on_init_failure(mock_environment, mock_pyttsx3_module, mock_subprocess):
    """
    Test that if engine init fails, it falls back to subprocess espeak.
    """
    mock_module, _ = mock_pyttsx3_module
    # Simulate driver failure
    mock_module.init.side_effect = Exception("No audio driver found")

    # Act
    tts = JetVoiceTTS()
    tts.speak("Fallback test")

    # Assert
    assert tts.engine is None
    mock_subprocess.assert_called_once()
    # Check that espeak was used
    assert "espeak" in mock_subprocess.call_args[0][0]

def test_tts_fallback_on_runtime_failure(mock_environment, mock_pyttsx3_module, mock_subprocess):
    """
    Test that if runAndWait crashes (runtime error), it falls back to espeak.
    """
    _, mock_engine = mock_pyttsx3_module
    
    # Arrange
    tts = JetVoiceTTS()
    # Simulate crash during speech
    mock_engine.runAndWait.side_effect = RuntimeError("Audio device lost")

    # Act
    tts.speak("Crash test")

    # Assert
    # It tried to speak via engine
    mock_engine.say.assert_called()
    # It failed, so it called subprocess
    mock_subprocess.assert_called_once()

def test_online_mode_logic(mock_pyttsx3_module, mock_subprocess):
    """
    Test logic path for Online Mode (gTTS).
    """
    # 1. Force Online Mode
    with patch.dict(os.environ, {"TTS_ONLINE": "true"}):
        # 2. Patch gTTS specifically since it's instantiated in the method
        with patch("jetvoice.tts.tts.gTTS") as mock_gtts_cls:
            mock_gtts_instance = MagicMock()
            mock_gtts_cls.return_value = mock_gtts_instance
            
            tts = JetVoiceTTS()
            
            # Act
            tts.speak("Online test")
            
            # Assert
            # Should NOT have initialized pyttsx3
            mock_pyttsx3_module[0].init.assert_not_called()
            
            # Should have called gTTS
            mock_gtts_cls.assert_called_with("Online test", lang='en', tld='us')
            mock_gtts_instance.save.assert_called_once()
            
            # Should call mpg123 via subprocess
            mock_subprocess.assert_called_once()
            args = mock_subprocess.call_args[0][0]
            assert args[0] == "mpg123"