from pathlib import Path

from ai.speech.preprocessing.audio_processor import AudioProcessor
from ai.speech.whisper.transcriber import SpeechTranscriber


def test_transcription():
    input_path = Path("tests/audio/recording.m4a")
    processed_path = Path("tests/audio/test_transcription_processed.wav")

    processor = AudioProcessor()
    processor.convert_to_wav(input_path, processed_path)

    try:
        transcriber = SpeechTranscriber()
        result = transcriber.transcribe(processed_path)

        assert isinstance(result, dict)
        assert isinstance(result["text"], str)
        assert result["text"].strip()

        assert isinstance(result["language"], str)
        assert result["language"].strip()

        assert 0 <= result["language_probability"] <= 1

    finally:
        if processed_path.exists():
            processed_path.unlink()