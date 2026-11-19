
from pathlib import Path

import numpy as np
import pytest

from ai.speech.preprocessing.audio_processor import AudioProcessor
from ai.speech.vad.detector import VoiceActivityDetector
from ai.speech.feature_extraction.acoustic_features import (
    AcousticFeatureExtractor,
)


def test_audio_features():
    input_path = Path("tests/audio/recording.m4a")
    processed_path = Path("tests/audio/test_features_processed.wav")

    if not input_path.exists():
        pytest.skip("Audio fixture recording.m4a is not available")

    processor = AudioProcessor()
    processor.convert_to_wav(input_path, processed_path)

    try:
        vad = VoiceActivityDetector()
        vad_result = vad.detect(processed_path)

        extractor = AcousticFeatureExtractor()
        features = extractor.extract(
            processed_path,
            vad_result,
        )

        assert isinstance(features, dict)
        assert features
        assert features["duration"] > 0
        assert features["speech_duration"] > 0
        assert features["number_of_pauses"] >= 0
        assert features["mean_energy"] >= 0
        assert features["mean_pitch"] >= 0
        assert features["min_pitch"] >= 0
        assert features["max_pitch"] >= 0

    finally:
        if processed_path.exists():
            processed_path.unlink()


def test_features_exclude_long_silence_outside_vad_speech_segments(monkeypatch):
    sample_rate = 16000
    audio = np.zeros(sample_rate * 5, dtype=float)
    audio[sample_rate * 4 : sample_rate * 4 + 4000] = 0.2
    pitch_inputs = []

    monkeypatch.setattr(
        "ai.speech.feature_extraction.acoustic_features.librosa.load",
        lambda *_args, **_kwargs: (audio, sample_rate),
    )

    def fake_pyin(segment, **_kwargs):
        pitch_inputs.append(segment.copy())
        return np.array([150.0, 160.0]), None, None

    monkeypatch.setattr(
        "ai.speech.feature_extraction.acoustic_features.librosa.pyin",
        fake_pyin,
    )

    result = AcousticFeatureExtractor(sample_rate).extract(
        "unused.wav",
        {
            "speech_segments": [{"start": 4.0, "end": 4.25}],
            "pauses": [],
            "duration": 5.0,
            "speech_duration": 0.25,
            "silence_duration": 4.75,
        },
    )

    assert result["mean_energy"] == pytest.approx(0.2)
    assert len(pitch_inputs) == 1
    assert np.array_equal(pitch_inputs[0], audio[64000:68000])


def test_features_use_each_vad_segment_and_ignore_invalid_boundaries(monkeypatch):
    sample_rate = 16000
    audio = np.zeros(sample_rate * 2, dtype=float)
    audio[1600:4800] = 0.1
    audio[16000:19200] = 0.3
    pitch_inputs = []
    monkeypatch.setattr(
        "ai.speech.feature_extraction.acoustic_features.librosa.load",
        lambda *_args, **_kwargs: (audio, sample_rate),
    )

    def fake_pyin(segment, **_kwargs):
        pitch_inputs.append(segment.copy())
        return np.array([float(segment[0] * 1000)]), None, None

    monkeypatch.setattr(
        "ai.speech.feature_extraction.acoustic_features.librosa.pyin",
        fake_pyin,
    )
    result = AcousticFeatureExtractor(sample_rate).extract(
        "unused.wav",
        {
            "speech_segments": [
                {"start": 0.1, "end": 0.3},
                {"start": 1.0, "end": 1.2},
                {"start": 1.8, "end": 1.7},
                {"start": "invalid", "end": 1.9},
            ],
            "pauses": [],
            "duration": 2.0,
            "speech_duration": 0.4,
            "silence_duration": 1.6,
        },
    )

    expected = np.concatenate([audio[1600:4800], audio[16000:19200]])
    assert result["mean_energy"] == pytest.approx(float(np.sqrt(np.mean(expected ** 2))))
    assert len(pitch_inputs) == 2
    assert np.array_equal(pitch_inputs[0], audio[1600:4800])
    assert np.array_equal(pitch_inputs[1], audio[16000:19200])


def test_overlapping_and_out_of_range_segments_are_clipped_and_deduplicated(monkeypatch):
    sample_rate = 16000
    audio = np.zeros(sample_rate, dtype=float)
    audio[0:8000] = 0.2
    audio[8000:16000] = 0.4
    pitch_inputs = []
    monkeypatch.setattr(
        "ai.speech.feature_extraction.acoustic_features.librosa.load",
        lambda *_args, **_kwargs: (audio, sample_rate),
    )

    def fake_pyin(segment, **_kwargs):
        pitch_inputs.append(segment.copy())
        return np.array([140.0]), None, None

    monkeypatch.setattr(
        "ai.speech.feature_extraction.acoustic_features.librosa.pyin",
        fake_pyin,
    )
    result = AcousticFeatureExtractor(sample_rate).extract(
        "unused.wav",
        {
            "speech_segments": [
                {"start": -0.1, "end": 0.3},
                {"start": 0.2, "end": 0.6},
                {"start": 0.5, "end": 2.0},
            ],
            "pauses": [],
            "duration": 1.0,
            "speech_duration": 1.0,
            "silence_duration": 0.0,
        },
    )

    assert result["mean_energy"] == pytest.approx(float(np.sqrt(np.mean(audio ** 2))))
    assert len(pitch_inputs) == 1
    assert np.array_equal(pitch_inputs[0], audio)


def test_short_segments_are_not_joined_for_pitch_analysis(monkeypatch):
    sample_rate = 16000
    audio = np.zeros(5000, dtype=float)
    audio[:1500] = 0.2
    audio[3000:4500] = 0.4
    monkeypatch.setattr(
        "ai.speech.feature_extraction.acoustic_features.librosa.load",
        lambda *_args, **_kwargs: (audio, sample_rate),
    )
    monkeypatch.setattr(
        "ai.speech.feature_extraction.acoustic_features.librosa.pyin",
        lambda *_args, **_kwargs: pytest.fail(
            "short VAD segments must not be concatenated for pitch analysis"
        ),
    )

    result = AcousticFeatureExtractor(sample_rate).extract(
        "unused.wav",
        {
            "speech_segments": [
                {"start": 0.0, "end": 1500 / sample_rate},
                {"start": 3000 / sample_rate, "end": 4500 / sample_rate},
            ],
            "pauses": [],
            "duration": len(audio) / sample_rate,
            "speech_duration": 3000 / sample_rate,
            "silence_duration": 2000 / sample_rate,
        },
    )

    assert result["mean_energy"] > 0.0
    assert result["mean_pitch"] == 0.0


def test_short_speech_segment_returns_safe_missing_pitch(monkeypatch):
    sample_rate = 16000
    audio = np.full(500, 0.2, dtype=float)
    monkeypatch.setattr(
        "ai.speech.feature_extraction.acoustic_features.librosa.load",
        lambda *_args, **_kwargs: (audio, sample_rate),
    )
    monkeypatch.setattr(
        "ai.speech.feature_extraction.acoustic_features.librosa.pyin",
        lambda *_args, **_kwargs: pytest.fail("pyin should skip very short audio"),
    )
    result = AcousticFeatureExtractor(sample_rate).extract(
        "unused.wav",
        {
            "speech_segments": [
                {"start": 0.0, "end": len(audio) / sample_rate}
            ],
            "pauses": [],
            "duration": len(audio) / sample_rate,
            "speech_duration": len(audio) / sample_rate,
            "silence_duration": 0.0,
        },
    )

    assert result["mean_energy"] == pytest.approx(0.2)
    assert result["mean_pitch"] == 0.0
