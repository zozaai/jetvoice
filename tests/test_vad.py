import os
import wave

import pytest

from jetvoice.vad.vad import WebRTCVAD


ASSETS_DIR = os.path.join(os.path.dirname(__file__), "assets")
TEST_WAV = os.path.join(ASSETS_DIR, "test_speech.wav")


def test_vad_invalid_sample_rate_raises():
    """VAD should reject unsupported sample rates."""
    with pytest.raises(ValueError):
        WebRTCVAD(sample_rate=12345, frame_duration_ms=20, aggressiveness=2)


def test_vad_invalid_frame_duration_raises():
    """VAD should reject unsupported frame durations."""
    with pytest.raises(ValueError):
        WebRTCVAD(sample_rate=16000, frame_duration_ms=25, aggressiveness=2)


def test_vad_detects_speech_in_test_audio():
    """
    VAD should detect at least some speech frames
    in the provided test_speech.wav.
    """
    assert os.path.exists(TEST_WAV), f"Missing test asset: {TEST_WAV}"

    with wave.open(TEST_WAV, "rb") as wf:
        sample_rate = wf.getframerate()
        n_channels = wf.getnchannels()
        sampwidth = wf.getsampwidth()

        # Basic sanity check on test file format
        assert n_channels == 1, "test_speech.wav must be mono"
        assert sampwidth == 2, "test_speech.wav must be 16-bit PCM"

        vad = WebRTCVAD(
            sample_rate=sample_rate,
            frame_duration_ms=20,
            aggressiveness=2,
        )

        # Read whole file into memory for a simple end-to-end check
        frames = wf.readframes(wf.getnframes())
        has_speech = vad.has_speech(frames)
        speech_frames = vad.count_speech_frames(frames)

        assert has_speech, "VAD did not detect speech in test_speech.wav"
        assert speech_frames > 0, "VAD counted zero speech frames in test_speech.wav"


def test_vad_does_not_flag_pure_silence():
    """
    VAD should not flag pure zero-valued PCM as speech.
    """
    vad = WebRTCVAD(sample_rate=16000, frame_duration_ms=20, aggressiveness=2)

    # 5 frames of absolute silence (all zeros)
    silence = b"\x00" * (vad.frame_size_bytes * 5)

    assert not vad.has_speech(silence)
    assert vad.count_speech_frames(silence) == 0
