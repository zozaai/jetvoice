# jetvoice/main.py

import os
import sys
import queue

import sounddevice as sd
from loguru import logger

from jetvoice.vad.vad import WebRTCVAD


def main():
    """
    VAD-only main loop with hysteresis:

    - Uses 20 ms frames.
    - To switch from "no voice" -> "voice":
        needs n_streak consecutive speech frames.
    - To switch from "voice" -> "no voice":
        needs n_silence consecutive non-speech frames.

    While in "voice" state, prints an increasing counter
    for each speech frame. When transitioning to "no voice",
    prints: "no voice detected, waiting for voice".
    """

    # ------- Logging -------
    logger.remove()
    logger.add(
        sys.stderr,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
               "<level>{level: <8}</level> | "
               "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
               "<level>{message}</level>"
    )

    logger.info("Starting JetVoice in VAD-only mode (with hysteresis)...")

    # ------- Config -------
    sample_rate = int(os.getenv("SAMPLE_RATE", "16000"))
    frame_duration_ms = 20  # as requested

    aggressiveness = int(os.getenv("VAD_AGGRESSIVENESS", "2"))  # 0–3
    # Number of consecutive speech frames to confirm "voice"
    n_streak = int(os.getenv("VAD_N_STREAK_FRAMES", "3"))
    # Number of consecutive silence frames to confirm "no voice"
    n_silence = int(os.getenv("VAD_N_SILENCE_FRAMES", "5"))
    print(n_silence)

    logger.info(
        f"Config: sample_rate={sample_rate}, frame_duration_ms={frame_duration_ms}, "
        f"aggressiveness={aggressiveness}, n_streak={n_streak}, n_silence={n_silence}"
    )

    # ------- VAD -------
    vad = WebRTCVAD(
        sample_rate=sample_rate,
        frame_duration_ms=frame_duration_ms,
        aggressiveness=aggressiveness,
    )

    # Audio device (force int index, as you tested)
    audio_device = int(os.getenv("AUDIO_DEVICE", 0))

    audio_queue: "queue.Queue[bytes]" = queue.Queue()

    def audio_callback(indata, frames, time_info, status):
        if status:
            logger.warning(f"Audio callback status: {status}")
        audio_queue.put(bytes(indata))

    # blocksize in samples for 20 ms
    blocksize = int(sample_rate * frame_duration_ms / 1000)

    # ------- State for hysteresis -------
    counter = 0
    in_speech = False
    speech_streak = 0
    silence_streak = 0

    buffer = b""
    frame_bytes = vad.frame_size_bytes

    try:
        logger.info("no voice detected, waiting for voice")

        with sd.RawInputStream(
            samplerate=sample_rate,
            blocksize=blocksize,
            dtype="int16",
            channels=1,
            callback=audio_callback,
            device=audio_device,
        ):
            while True:
                chunk = audio_queue.get()
                buffer += chunk

                # Process buffer in fixed frame sizes
                while len(buffer) >= frame_bytes:
                    frame = buffer[:frame_bytes]
                    buffer = buffer[frame_bytes:]

                    has_speech = vad.has_speech(frame)

                    if has_speech:
                        speech_streak += 1
                        silence_streak = 0

                        if not in_speech:
                            # Only enter voice state after n_streak frames
                            if speech_streak >= n_streak:
                                in_speech = True
                                counter += 1
                                print(counter)
                        else:
                            # Already in speech, keep counting
                            counter += 1
                            print(counter)

                    else:
                        silence_streak += 1
                        speech_streak = 0

                        if in_speech and silence_streak >= n_silence:
                            in_speech = False
                            print("no voice detected, waiting for voice")

    except KeyboardInterrupt:
        logger.info("Gracefully shutting down VAD loop.")
    except Exception as e:
        logger.error(f"Unexpected error in VAD main loop: {e}")
        logger.exception("Traceback:")


if __name__ == "__main__":
    main()
