import os
import sys
import queue

import sounddevice as sd
from loguru import logger

from jetvoice.vad.vad import WebRTCVAD
from jetvoice.stt.stt import transcribe_bytes
from jetvoice.llm.llm import JetVoiceLLM
from jetvoice.tts.tts import JetVoiceTTS


def main():
    """
    Main loop: VAD -> STT -> LLM -> TTS -> Loop
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

    logger.info("Starting JetVoice VAD + STT + LLM + TTS loop...")

    # ------- Config -------
    sample_rate = int(os.getenv("SAMPLE_RATE", "16000"))
    frame_duration_ms = 20

    aggressiveness = int(os.getenv("VAD_AGGRESSIVENESS", "2"))
    n_streak = int(os.getenv("VAD_N_STREAK_FRAMES", "3"))
    n_silence = int(os.getenv("VAD_N_SILENCE_FRAMES", "5"))

    logger.info(
        f"Config: sample_rate={sample_rate}, frame_duration_ms={frame_duration_ms}, "
        f"aggressiveness={aggressiveness}, n_streak={n_streak}, n_silence={n_silence}"
    )

    # ------- Init Modules -------
    vad = WebRTCVAD(
        sample_rate=sample_rate,
        frame_duration_ms=frame_duration_ms,
        aggressiveness=aggressiveness,
    )
    
    llm = JetVoiceLLM()
    tts = JetVoiceTTS()

    audio_device = int(os.getenv("AUDIO_DEVICE", "0"))
    audio_queue: "queue.Queue[bytes]" = queue.Queue()

    def audio_callback(indata, frames, time_info, status):
        if status:
            pass 
        audio_queue.put(bytes(indata))

    blocksize = int(sample_rate * frame_duration_ms / 1000)

    # ------- State -------
    in_speech = False
    speech_streak = 0
    silence_streak = 0

    buffer = b""
    frame_bytes = vad.frame_size_bytes
    current_segment = bytearray()

    logger.info("[STATE] listening (no voice, waiting for activity)")

    try:
        # We assign the stream to a variable 'stream' so we can stop/start it
        with sd.RawInputStream(
            samplerate=sample_rate,
            blocksize=blocksize,
            dtype="int16",
            channels=1,
            callback=audio_callback,
            device=audio_device,
        ) as stream:
            while True:
                chunk = audio_queue.get()
                buffer += chunk

                # Process fixed-size frames
                while len(buffer) >= frame_bytes:
                    frame = buffer[:frame_bytes]
                    buffer = buffer[frame_bytes:]

                    has_speech = vad.has_speech(frame)

                    if has_speech:
                        current_segment.extend(frame)
                        speech_streak += 1
                        silence_streak = 0

                        # --- TRANSITION: LISTENING -> CAPTURING ---
                        if not in_speech and speech_streak >= n_streak:
                            in_speech = True
                            logger.info("Capturing ...")

                    else:
                        # Silence frame
                        if in_speech:
                            silence_streak += 1
                            speech_streak = 0
                            current_segment.extend(frame)

                            # --- TRANSITION: CAPTURING -> TRANSCRIBING ---
                            if silence_streak >= n_silence:
                                in_speech = False
                                
                                logger.info("[STATE] transcribing...")

                                audio_bytes = bytes(current_segment)
                                current_segment.clear()
                                speech_streak = 0
                                silence_streak = 0

                                if audio_bytes:
                                    text = transcribe_bytes(audio_bytes, sample_rate=sample_rate)
                                    if text:
                                        print(f"\n[Transcript] {text}")
                                        
                                        logger.info("Querying LLM...")
                                        response = llm.ask(text)
                                        
                                        if response:
                                            print(f"[AI] {response}")
                                            
                                            # --- TTS BLOCKING SECTION ---
                                            logger.info("Pausing microphone for playback...")
                                            
                                            # 1. Stop capturing to prevent feedback loop
                                            stream.stop()
                                            
                                            # 2. Speak the response (Blocking)
                                            tts.speak(response)
                                            
                                            # 3. Clear any audio buffered during the stop process
                                            #    (This prevents processing 'echoes' captured just before stopping)
                                            with audio_queue.mutex:
                                                audio_queue.queue.clear()
                                            buffer = b""
                                            
                                            # 4. Resume capturing
                                            logger.info("Resuming listening...")
                                            stream.start()
                                            
                                        else:
                                            logger.warning("LLM returned no response.")
                                    else:
                                        print("\n[Transcript] (no text recognized)")

                                logger.info("[STATE] listening")

                        else:
                            # Still silent, not in a speech segment
                            speech_streak = 0

    except KeyboardInterrupt:
        logger.info("Gracefully shutting down VAD + STT loop.")
    except Exception as e:
        logger.error(f"Unexpected error in main loop: {e}")
        logger.exception("Traceback:")


if __name__ == "__main__":
    main()