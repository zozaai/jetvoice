from jetvoice.tts.tts import JetVoiceTTS

if __name__ == "__main__":
    print("--- Running TTS Test Module ---")
    tts = JetVoiceTTS()
    long_text = (
        "Hello! I am running via the main module. "
        "This avoids the import warning and tests the voice configuration."
    )
    tts.speak(long_text)