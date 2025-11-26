import pyttsx3
import os
import subprocess
from gtts import gTTS

class JetVoiceTTS:
    def __init__(self):
        """
        Initializes the TTS engine.
        """
        self.engine = None
        self.use_online = os.getenv("TTS_ONLINE", "false").lower() == "true"
        
        # Only init pyttsx3 if we are NOT using online TTS (or as backup)
        if not self.use_online:
            try:
                self.engine = pyttsx3.init()
                self._configure_engine()
            except Exception as e:
                print(f"[TTS] Offline engine init failed: {e}")

    def _configure_engine(self):
        """
        Configures the offline engine properties.
        """
        if not self.engine: 
            return
        
        # 1. Rate (Slower = Less Robotic)
        # Defaulting to 125 makes espeak much clearer
        try:
            rate = int(os.getenv("TTS_RATE", "125")) 
            self.engine.setProperty('rate', rate)
        except Exception:
            pass

        # 2. Volume
        try:
            volume = float(os.getenv("TTS_VOLUME", "1.0"))
            self.engine.setProperty('volume', volume)
        except Exception:
            pass

        # 3. Voice (Prefer US English)
        try:
            self.engine.setProperty('voice', 'english-us')
        except Exception:
            pass

    def speak(self, text: str):
        """
        Speaks the provided text.
        """
        if not text: 
            return

        print(f"[TTS] Speaking: '{text}'")

        if self.use_online:
            self._speak_online(text)
        else:
            self._speak_offline(text)

    def _speak_online(self, text: str):
        """
        Uses Google TTS (Natural voice). Requires Internet and mpg123.
        """
        try:
            # Generate MP3
            tts = gTTS(text, lang='en', tld='us')
            filepath = "/tmp/jetvoice_output.mp3"
            tts.save(filepath)
            
            # Play MP3 using mpg123
            subprocess.run(
                ['mpg123', '-q', filepath], 
                check=True
            )
        except Exception as e:
            print(f"[TTS] Online failed ({e}). Switching to offline fallback.")
            self._speak_offline(text)

    def _speak_offline(self, text: str):
        """
        Fallback to pyttsx3 (Robot voice)
        """
        if self.engine:
            try:
                self.engine.say(text)
                self.engine.runAndWait()
            except Exception as e:
                print(f"[TTS] pyttsx3 error: {e}")
                self._fallback_espeak(text)
        else:
            self._fallback_espeak(text)

    def _fallback_espeak(self, text: str):
        """
        Direct shell call to espeak if Python bindings fail.
        """
        try:
            subprocess.run(['espeak', '-s', '125', '-v', 'en-us', text], check=True)
        except Exception as e:
            print(f"[TTS] espeak command failed: {e}")

if __name__ == "__main__":
    # This block runs when you execute: python -m jetvoice.tts.tts
    
    print("--- Initializing JetVoiceTTS ---")
    tts = JetVoiceTTS()
    
    # Long sentence to test naturalness/robotics
    long_text = (
        "Hello there! I am testing my voice capabilities. "
        "This is a longer sentence designed to check if I sound like a "
        "friendly assistant, or if I still sound a bit too much like a "
        "robot from the nineteen eighties. I hope the audio is clear!"
    )
    
    tts.speak(long_text)