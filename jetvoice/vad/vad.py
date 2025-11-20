import webrtcvad
from typing import Optional


class WebRTCVAD:
    """
    Simple wrapper around WebRTC VAD for 16-bit mono PCM audio.

    Usage:
        vad = WebRTCVAD(sample_rate=16000, frame_duration_ms=20, aggressiveness=2)
        if vad.has_speech(chunk_bytes):
            ...
    """

    def __init__(
        self,
        sample_rate: int = 16000,
        frame_duration_ms: int = 20,
        aggressiveness: int = 2,
    ) -> None:
        """
        Args:
            sample_rate: Audio sample rate in Hz (must be 8000, 16000, 32000, or 48000).
            frame_duration_ms: Frame length in milliseconds (10, 20, or 30).
            aggressiveness: VAD aggressiveness, 0-3 (3 = most aggressive).
        """
        if sample_rate not in (8000, 16000, 32000, 48000):
            raise ValueError("sample_rate must be one of 8000, 16000, 32000, 48000")
        if frame_duration_ms not in (10, 20, 30):
            raise ValueError("frame_duration_ms must be 10, 20, or 30")

        self.sample_rate = sample_rate
        self.frame_duration_ms = frame_duration_ms
        self.frame_size_bytes = int(sample_rate * frame_duration_ms / 1000) * 2  # 16-bit mono
        self._vad = webrtcvad.Vad(aggressiveness)

    def _iter_frames(self, audio: bytes):
        """
        Yield consecutive frames of size frame_size_bytes from the chunk.
        Discards any trailing bytes that don't fit a full frame.
        """
        length = len(audio)
        step = self.frame_size_bytes
        for start in range(0, length - step + 1, step):
            yield audio[start:start + step]

    def has_speech(self, audio: bytes) -> bool:
        """
        Return True if any frame in the chunk is classified as speech.

        Args:
            audio: Raw PCM16 mono data (bytes).

        Returns:
            bool: True if at least one frame contains speech.
        """
        if len(audio) < self.frame_size_bytes:
            return False

        for frame in self._iter_frames(audio):
            if self._vad.is_speech(frame, self.sample_rate):
                return True
        return False

    def count_speech_frames(self, audio: bytes) -> int:
        """
        Count how many frames in the chunk are classified as speech.
        Useful for thresholds like '>= N frames with speech'.

        Args:
            audio: Raw PCM16 mono data (bytes).

        Returns:
            int: Number of frames detected as speech.
        """
        if len(audio) < self.frame_size_bytes:
            return 0

        count = 0
        for frame in self._iter_frames(audio):
            if self._vad.is_speech(frame, self.sample_rate):
                count += 1
        return count
