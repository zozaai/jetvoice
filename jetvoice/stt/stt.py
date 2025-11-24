import os
import queue
import sounddevice as sd
import vosk
import json
import time
import wave


# Path to the Vosk speech recognition model (configurable)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
VOSK_MODEL = os.getenv("VOSK_MODEL", "vosk-model-small-en-us-0.15")
MODEL_PATH = os.path.join(BASE_DIR, "models", VOSK_MODEL)
AUDIO_DEVICE = os.getenv("AUDIO_DEVICE", None)
SAMPLE_RATE = int(os.getenv("SAMPLE_RATE", 16000))

# Load Vosk model once
try:
    print("#---------- List of audio devices ------------------")
    for i, dev in enumerate(sd.query_devices()):
        print(f"{i}: {dev['name']} - ({dev['max_input_channels']} in, {dev['max_output_channels']} out)")
    print("----------------------------------------------------")

    model = vosk.Model(MODEL_PATH)
except Exception as e:
    raise RuntimeError(f"Vosk model not found at {MODEL_PATH}. Error: {e}")

# Create audio queue
q = queue.Queue()

# Callback function for streaming audio data
def callback(indata, frames, time, status):
    q.put(bytes(indata))


def transcribe_bytes(audio_bytes: bytes, sample_rate: int = SAMPLE_RATE) -> str:
    """
    Transcribes a chunk of raw PCM16 mono audio bytes using the already loaded Vosk model.

    Args:
        audio_bytes: Raw 16-bit PCM mono audio bytes.
        sample_rate: Sample rate of the audio (Hz), must match how it was recorded.

    Returns:
        Transcribed text (may be empty string if nothing recognized).
    """
    try:
        if not audio_bytes:
            return ""

        recognizer = vosk.KaldiRecognizer(model, sample_rate)

        # Feed audio to recognizer in chunks
        chunk_size = 4000  # bytes per chunk; doesn't need to match exactly anything
        offset = 0
        length = len(audio_bytes)

        while offset < length:
            chunk = audio_bytes[offset:offset + chunk_size]
            offset += chunk_size
            recognizer.AcceptWaveform(chunk)

        result = json.loads(recognizer.FinalResult())
        return result.get("text", "").strip()

    except Exception as e:
        print(f"[STT Bytes Error]: {e}")
        return ""


# Main transcription function
def transcribe(timeout=100, silence_timeout=3):
    """
    Transcribe speech with timeout and silence detection
    """
    try:
        print(sd.query_devices())
        with sd.RawInputStream(samplerate=SAMPLE_RATE, blocksize=8000, dtype='int16', 
                               channels=1, device=5, callback=callback):
            recognizer = vosk.KaldiRecognizer(model, SAMPLE_RATE)
            print("🎤 Listening... (speak now)")

            start_time = time.time()
            last_speech_time = None
            partial_result = ""
            
            while True:
                current_time = time.time()
                
                # Check timeout
                if current_time - start_time > timeout:
                    print("⏰ Timeout reached")
                    break
                
                # Check silence timeout after speech detected
                print("last_speech_time", last_speech_time)
                if last_speech_time:
                    silence_time = current_time - last_speech_time
                    print("silence_time", silence_time)
                if last_speech_time and (silence_time > silence_timeout):
                    print("🔇 Silence detected, processing...")
                    break
                
                try:
                    data = q.get(timeout=0.1)
                    
                    if recognizer.AcceptWaveform(data):
                        # Complete phrase detected
                        result = json.loads(recognizer.Result())
                        text = result.get("text", "").strip()
                        if text:
                            print(f"Complete: '{text}'")
                            return text
                    else:
                        # Check for partial results
                        partial = json.loads(recognizer.PartialResult())
                        current_partial = partial.get("partial", "").strip()
                        
                        if current_partial and current_partial != partial_result:
                            partial_result = current_partial
                            last_speech_time = current_time
                            print(f"Partial: '{current_partial}'")
                            
                except queue.Empty:
                    continue
            
            # Get final result if we have partial speech
            if partial_result:
                final_result = json.loads(recognizer.FinalResult())
                final_text = final_result.get("text", "").strip()
                if final_text:
                    print(f"Final: '{final_text}'")
                    return final_text
                elif partial_result:
                    print(f"Using partial: '{partial_result}'")
                    return partial_result
            
            print("❌ No speech detected")
            return ""
            
    except Exception as e:
        print(f"[STT Error]: {e}")
        return ""



# Add this new function at the end of the file
def transcribe_file(file_path: str) -> str:
    """
    Transcribes a local audio file.

    This function is primarily for testing the Vosk model with a consistent
    input. The audio file must be in WAV format with the correct properties.

    Args:
        file_path: The path to the .wav file.

    Returns:
        The transcribed text as a string.
    """
    try:
        # Check if the file is in the required format
        wf = wave.open(file_path, "rb")
        expected_framerate = int(SAMPLE_RATE)
        if (wf.getnchannels() != 1 or wf.getsampwidth() != 2 or
                wf.getcomptype() != "NONE" or wf.getframerate() != expected_framerate):
            raise TypeError(
                f"Audio file must be WAV format, mono, 16-bit, {expected_framerate} Hz. "
                f"File provided has {wf.getnchannels()} channels, "
                f"{wf.getsampwidth()*8}-bit, {wf.getframerate()} Hz."
            )

        recognizer = vosk.KaldiRecognizer(model, wf.getframerate())
        
        while True:
            data = wf.readframes(4000)  # Read audio in chunks
            if len(data) == 0:
                break
            recognizer.AcceptWaveform(data)

        # Get the final recognized text
        result = json.loads(recognizer.FinalResult())
        return result.get("text", "").strip()

    except FileNotFoundError:
        print(f"Error: The test audio file '{file_path}' was not found.")
        return ""
    except TypeError as e:
        print(f"Error: {e}")
        return ""
    except Exception as e:
        print(f"[STT File Error]: {e}")
        return ""
    

# Run transcription directly
def recognize_from_microphone():
    text = transcribe()
    print("Recognized Text:", text)

if __name__ == "__main__":
    recognize_from_microphone()
