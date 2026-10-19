from unittest.mock import MagicMock

import pytest

from ai.speech.whisper.transcriber import SpeechTranscriber


def make_transcriber():
    transcriber = SpeechTranscriber.__new__(SpeechTranscriber)
    transcriber.model = MagicMock()
    return transcriber


def test_empty_pcm_returns_empty_text():
    transcriber = make_transcriber()

    assert transcriber.transcribe_pcm_chunk(b"") == ""
    transcriber.model.transcribe.assert_not_called()


def test_odd_length_pcm_raises_error():
    transcriber = make_transcriber()

    with pytest.raises(ValueError, match="16-bit samples"):
        transcriber.transcribe_pcm_chunk(b"\x01")


def test_pcm_chunk_is_wrapped_as_wav_and_transcribed():
    transcriber = make_transcriber()

    segment = MagicMock()
    segment.text = " hello "
    transcriber.model.transcribe.return_value = ([segment], None)

    result = transcriber.transcribe_pcm_chunk(b"\x00\x00" * 1600)

    assert result == "hello"
    transcriber.model.transcribe.assert_called_once()