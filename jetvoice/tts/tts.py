import pyttsx3
import os
import subprocess
import sys

class JetVoiceTTS:
    def __init__(self):
        """
        Initializes the TTS engine once to avoid the overhead and instability
        of repeated initialization.
        """
        self.engine = None
        
        try:
            # Initialize the engine
            self.engine = pyttsx3.init()
            self._configure_engine()
        except Exception as e:
            print(f"[TTS Init Error]: Could not initialize pyttsx3: {e}")
            print("[TTS] Switching to fallback (espeak subprocess) mode.")
            self.engine = None

    def _configure_engine(self):
        """
        Sets voice, rate, and volume based on environment variables or defaults.
        """
        if not self.engine:
            return

        # 1. Voice Selection
        try:
            voices = self.engine.getProperty('voices')
            user_voice = os.getenv("TTS_VOICE_ID")
            selected_voice = None

            # A. Try user-specified ID
            if user_voice:
                for voice in voices:
                    if user_voice == voice.id:
                        selected_voice = voice.id
                        break
            
            # B. Try preferences (US/English)
            if not selected_voice:
                voice_preference = ['english-us', 'english_rp', 'english', 'default']
                for preferred in voice_preference:
                    for voice in voices:
                        if preferred in voice.id.lower():
                            selected_voice = voice.id
                            break
                    if selected_voice:
                        break

            if selected_voice:
                self.engine.setProperty('voice', selected_voice)
                # print(f"[TTS] Configured voice: {selected_voice}")

        except Exception as e:
            print(f"[TTS Config Warning] Failed to set voice: {e}")

        # 2. Rate and Volume
        try:
            rate = int(os.getenv("TTS_RATE", "150"))
            self.engine.setProperty('rate', rate)

            volume = float(os.getenv("TTS_VOLUME", "0.9"))
            self.engine.setProperty('volume', volume)
        except Exception as e:
            print(f"[TTS Config Warning] Failed to set rate/volume: {e}")

    def speak(self, text: str):
        """
        Speaks the provided text. Uses fallback if the main engine fails.
        """
        if not text:
            return

        print(f"[TTS] Speaking: '{text}'")

        if self.engine:
            try:
                self.engine.say(text)
                self.engine.runAndWait()
            except Exception as e:
                print(f"[TTS Runtime Error]: {e}")
                self._fallback_speak(text)
        else:
            self._fallback_speak(text)

    def _fallback_speak(self, text: str):
        """
        Fallback mechanism using direct subprocess call to espeak.
        Useful for Docker environments where pyttsx3 drivers might flake out.
        """
        try:
            subprocess.run(
                ['espeak', '-s', '150', '-v', 'en-us', text], 
                capture_output=True, 
                check=True
            )
        except Exception as e:
            print(f"[TTS Fallback Error]: espeak failed: {e}")

# Create a singleton instance for easy import if needed, 
# though instantiating in main.py is cleaner.
if __name__ == "__main__":
    tts = JetVoiceTTS()
    tts.speak("System initialized.")