# tests/test_stt.py

import os
import pytest
import jiwer
from jetvoice.stt.stt import transcribe_file

# Define the path to the test audio file. This makes the test runnable from anywhere.
TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
TEST_WAV_FILE = os.path.join(TESTS_DIR, "assets", "test_speech.wav")

# This is the exact phrase you recorded in your audio file.
EXPECTED_REFERENCE_TEXT = "Hey everyone, I'm Jim. I work as an AI engineer on the Zozajet team with Alma. Right now, I'm working on JetVoice an open-source voice assistant that uses large language models"
WER_THRESHOLD = 0.4 

@pytest.fixture(scope="module")
def audio_file_path():
    """
    This is a pytest fixture. It checks that the test audio file exists 
    before a test runs and provides its path.
    """
    if not os.path.exists(TEST_WAV_FILE):
        pytest.fail(
            f"\n\n--> Test audio file not found at: {TEST_WAV_FILE}\n"
            f"--> Please record yourself saying '{EXPECTED_REFERENCE_TEXT}' and save it there.\n"
            "--> Required format: WAV, 16000 Hz, 16-bit, Mono."
        )
    return TEST_WAV_FILE

def test_transcribe_from_file(audio_file_path):
    """
    Tests that the STT transcription's Word Error Rate (WER) is below an
    acceptable threshold.

    This is a robust test that ignores minor differences in punctuation and
    capitalization and focuses on the core word accuracy.
    """
    # GIVEN the ground truth text and a path to the corresponding audio file.
    ground_truth = EXPECTED_REFERENCE_TEXT
    
    # WHEN the audio file is transcribed.
    hypothesis = transcribe_file(audio_file_path) # This is the text from the STT model

    # jiwer's default transformation handles converting to lowercase, removing
    # punctuation, and standardizing whitespace. This is crucial for a fair comparison.
    transformation = jiwer.Compose([
        jiwer.ToLowerCase(),
        jiwer.RemoveMultipleSpaces(),
        jiwer.RemovePunctuation(),
        jiwer.Strip()
    ])

    ground_truth_transformed = transformation(ground_truth)
    hypothesis_transformed = transformation(hypothesis)

    wer = jiwer.wer(ground_truth_transformed, hypothesis_transformed)

    # AND assert that the error rate is below our defined threshold.
    print("\n--- WER Test Details ---")
    print(f"Ground Truth: '{ground_truth}'")
    print(f"Hypothesis  : '{hypothesis}'")
    print(f"Calculated WER: {wer:.2%} ({wer})")
    print(f"Threshold     : {WER_THRESHOLD:.2%} ({WER_THRESHOLD})")
    print("------------------------")
    
    assert wer <= WER_THRESHOLD, f"Word Error Rate ({wer:.2%}) is higher than the threshold ({WER_THRESHOLD:.2%})."