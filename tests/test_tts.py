import os
import pytest
from unittest.mock import MagicMock, patch
from jetvoice.tts.tts import JetVoiceTTS

@pytest.fixture
def mock_pyttsx3_init():
    """
    Patches pyttsx3.init BEFORE the class is instantiated.
    """
    with patch("jetvoice.tts.tts.pyttsx3.init") as mock_init:
        yield mock_init

@pytest.fixture
def mock_engine(mock_pyttsx3_init):
    """
    Returns the mock engine object created by pyttsx3.init().
    """
    mock_engine_instance = MagicMock()
    # Mock voices property to return an empty list by default to avoid iteration errors
    mock_engine_instance.getProperty.return_value = []
    mock_pyttsx3_init.return_value = mock_engine_instance
    return mock_engine_instance

def test_tts_init_configure(mock_engine):
    """
    Test that initializing the class sets up the engine properties exactly once.
    """
    # Act
    tts = JetVoiceTTS()

    # Assert
    # 1. Engine was initialized
    assert tts.engine == mock_engine
    
    # 2. Properties were set (checking for 'rate' and 'volume')
    # We inspect the calls to setProperty
    calls = mock_engine.setProperty.call_args_list
    args_called = [c[0][0] for c in calls]  # Extract first arg of each call
    
    assert 'rate' in args_called
    assert 'volume' in args_called

def test_tts_speak_success(mock_engine):
    """
    Test that calling speak() uses the existing engine instance.
    """
    # Arrange
    tts = JetVoiceTTS()
    text = "Hello AI"

    # Act
    tts.speak(text)

    # Assert
    mock_engine.say.assert_called_once_with(text)
    mock_engine.runAndWait.assert_called_once()

@patch("jetvoice.tts.tts.subprocess.run")
def test_tts_init_failure_fallback(mock_subprocess, mock_pyttsx3_init):
    """
    Test that if pyttsx3.init fails, the class handles it and defaults to fallback.
    """
    # Arrange: Simulate init failure
    mock_pyttsx3_init.side_effect = Exception("Driver not found")

    # Act
    tts = JetVoiceTTS()
    tts.speak("Testing fallback")

    # Assert
    assert tts.engine is None
    # Verify subprocess was called (espeak fallback)
    mock_subprocess.assert_called_once()
    assert "espeak" in mock_subprocess.call_args[0][0]

@patch("jetvoice.tts.tts.subprocess.run")
def test_tts_runtime_failure_fallback(mock_subprocess, mock_engine):
    """
    Test that if engine.runAndWait fails during speak(), it switches to fallback.
    """
    # Arrange
    tts = JetVoiceTTS()
    # Simulate a crash during the speech loop
    mock_engine.runAndWait.side_effect = RuntimeError("Loop error")

    # Act
    tts.speak("Crash test")

    # Assert
    # pyttsx3 tried to speak
    mock_engine.say.assert_called()
    # But it crashed, so fallback should be triggered
    mock_subprocess.assert_called_once()

def test_voice_selection_preference(mock_engine):
    """
    Test that the class attempts to select an English voice.
    """
    # Arrange: Mock available voices
    voice_us = MagicMock(); voice_us.id = "english-us"
    voice_fr = MagicMock(); voice_fr.id = "french"
    
    mock_engine.getProperty.return_value = [voice_fr, voice_us]
    
    # Act
    JetVoiceTTS()

    # Assert
    # Check if setProperty was called with the preferred voice ID
    mock_engine.setProperty.assert_any_call('voice', 'english-us')