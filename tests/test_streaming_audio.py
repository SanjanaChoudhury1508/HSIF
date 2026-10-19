import numpy as np
import pytest

from ai.speech.streaming.chunk_processor import StreamingAudioProcessor


def test_silence_is_not_detected_as_speech():
    processor = StreamingAudioProcessor()

    silence = np.zeros(1600, dtype="<i2").tobytes()
    result = processor.process_chunk(silence)

    assert result["is_speech"] is False
    assert result["duration"] == pytest.approx(0.1)
    assert result["total_duration"] == pytest.approx(0.1)


def test_audio_chunk_updates_duration():
    processor = StreamingAudioProcessor()

    silence = np.zeros(1600, dtype="<i2").tobytes()
    processor.process_chunk(silence)
    result = processor.process_chunk(silence)

    assert result["total_duration"] == pytest.approx(0.2)


def test_empty_chunk_does_not_change_state():
    processor = StreamingAudioProcessor()

    result = processor.process_chunk(b"")

    assert result["duration"] == 0.0
    assert result["is_speech"] is False
    assert result["total_duration"] == 0.0


def test_reset_clears_streaming_state():
    processor = StreamingAudioProcessor()

    silence = np.zeros(1600, dtype="<i2").tobytes()
    processor.process_chunk(silence)
    processor.reset()

    assert processor.total_audio_duration == 0.0
    assert processor.total_speech_duration == 0.0