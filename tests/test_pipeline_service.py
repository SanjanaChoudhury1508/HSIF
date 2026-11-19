import pytest
from unittest.mock import Mock

from backend.app.services.pipeline_service import (
    NoSpeechDetectedError,
    PipelineService,
)
from backend.app.services.llm.errors import LLMIncompleteResponseError


def test_pipeline_service_stores_completed_conversation_turn():
    llm_provider = Mock()
    llm_provider.generate.return_value = "This is the assistant response."

    service = PipelineService(llm_provider=llm_provider)

    # Mock the expensive speech and human-state stages.
    service.speech_service.process = Mock(
        return_value={
            "transcript": "Hello, how are you?",
        }
    )

    service.human_state_engine.process_to_dict = Mock(
        return_value={
            "emotion": {
                "label": "neutral",
                "score": 0.6,
            },
            "hesitation": {
                "score": 0.2,
            },
            "confidence": {
                "score": 0.7,
            },
            "engagement": {
                "score": 0.8,
            },
            "cognitive_load": {
                "score": 0.3,
            },
        }
    )

    result = service.process_audio("test.wav")

    assert result["response"] == "This is the assistant response."

    history = service.dialogue_service.get_history()

    assert len(history) == 1
    assert history[0]["user_message"] == "Hello, how are you?"
    assert history[0]["assistant_message"] == "This is the assistant response."
    assert history[0]["dialogue_strategy"] == result["dialogue"]["policy"]["strategy"]


def test_pipeline_persists_full_provider_response_without_truncation():
    full_response = "# Full answer\n\n" + ("A complete paragraph. " * 180) + "**The final point is complete.**"
    repository = Mock()
    repository.get_turns.return_value = []
    llm_provider = Mock()
    llm_provider.generate.return_value = full_response
    service = PipelineService(
        llm_provider=llm_provider,
        session_id="full-response-test",
        repository=repository,
    )

    result = service.process_text("Please give a detailed explanation.")

    assert result["response"] == full_response
    repository.add_turn.assert_called_once()
    assert repository.add_turn.call_args.kwargs["assistant_message"] == full_response
    assert service.dialogue_service.get_history()[0]["assistant_message"] == full_response


def test_pipeline_does_not_persist_a_truncated_provider_response():
    repository = Mock()
    repository.get_turns.return_value = []
    llm_provider = Mock()
    llm_provider.generate.side_effect = LLMIncompleteResponseError(
        "The AI response was cut off before it finished. Please try again."
    )
    service = PipelineService(
        llm_provider=llm_provider,
        session_id="truncated-response-test",
        repository=repository,
    )

    with pytest.raises(LLMIncompleteResponseError):
        service.process_text("Please give a detailed explanation.")

    repository.add_turn.assert_not_called()
    assert service.dialogue_service.get_history() == []


@pytest.mark.parametrize("transcript", ["", " \n\t", None])
def test_empty_audio_transcript_stops_before_llm_or_persistence(transcript):
    repository = Mock()
    repository.get_turns.return_value = []
    llm_provider = Mock()
    service = PipelineService(
        llm_provider=llm_provider,
        session_id="empty-transcript-test",
        repository=repository,
    )
    service.speech_service = Mock()
    service.speech_service.process.return_value = {"transcript": transcript}
    service.dialogue_service = Mock()

    with pytest.raises(NoSpeechDetectedError, match="No speech could be transcribed"):
        service.process_audio("test.wav")

    service.dialogue_service.process.assert_not_called()
    llm_provider.generate.assert_not_called()
    repository.add_turn.assert_not_called()


def test_short_nonempty_audio_transcript_is_allowed():
    llm_provider = Mock()
    llm_provider.generate.return_value = "Hi there."
    service = PipelineService(llm_provider=llm_provider)
    service.speech_service = Mock()
    service.speech_service.process.return_value = {"transcript": " Hi "}

    result = service.process_audio("test.wav")

    assert result["speech"]["transcript"] == "Hi"
    llm_provider.generate.assert_called_once()

def test_pipeline_adapts_to_high_cognitive_load():
    llm_provider = Mock()
    llm_provider.generate.return_value = "Here is a simpler explanation."

    service = PipelineService(llm_provider=llm_provider)

    service.speech_service.process = Mock(
        return_value={
            "transcript": "There is too much information and I am getting confused.",
            "audio": {"duration": 1.0, "speech_duration": 0.8},
            "vad": {"speech_segments": [{"start": 0.0, "end": 0.8}]},
            "features": {"mean_pitch": 180, "min_pitch": 140, "max_pitch": 220, "mean_energy": 0.08},
        }
    )

    service.human_state_engine.process_to_dict = Mock(
        return_value={
            "emotion": {
                "label": "neutral",
                "score": 0.6,
            },
            "hesitation": {
                "score": 0.6,
            },
            "confidence": {
                "score": 0.4,
            },
            "engagement": {
                "score": 0.7,
            },
            "cognitive_load": {
                "score": 0.9,
            },
        }
    )

    result = service.process_audio("test.wav")

    assert result["dialogue"]["policy"]["strategy"] == "reduce_information"
    assert "reduce_information" in result["dialogue"]["prompt"]
    assert result["response"] == "Here is a simpler explanation."

    history = service.dialogue_service.get_history()

    assert len(history) == 1
    assert history[0]["dialogue_strategy"] == "reduce_information"


def test_pipeline_adapts_to_frustration():
    llm_provider = Mock()
    llm_provider.generate.return_value = (
        "I understand this is frustrating. Let's work through it step by step."
    )

    service = PipelineService(llm_provider=llm_provider)

    service.speech_service.process = Mock(
        return_value={
            "transcript": "This is frustrating. I still cannot understand it.",
            "audio": {"duration": 1.0, "speech_duration": 0.8},
            "vad": {"speech_segments": [{"start": 0.0, "end": 0.8}]},
            "features": {"mean_pitch": 180, "min_pitch": 140, "max_pitch": 220, "mean_energy": 0.08},
        }
    )

    service.human_state_engine.process_to_dict = Mock(
        return_value={
            "emotion": {
                "label": "frustrated",
                "score": 0.9,
            },
            "hesitation": {
                "score": 0.6,
            },
            "confidence": {
                "score": 0.4,
            },
            "engagement": {
                "score": 0.6,
            },
            "cognitive_load": {
                "score": 0.7,
            },
        }
    )

    result = service.process_audio("test.wav")

    assert result["dialogue"]["policy"]["strategy"] == "acknowledge_frustration"
    assert "acknowledge_frustration" in result["dialogue"]["prompt"]
    assert result["response"] == (
        "I understand this is frustrating. Let's work through it step by step."
    )

    history = service.dialogue_service.get_history()

    assert len(history) == 1
    assert history[0]["dialogue_strategy"] == "acknowledge_frustration"

def test_pipeline_service_restores_persisted_history_and_state():
    repository = Mock()

    persisted_state = {
        "emotion": {
            "label": "excited",
            "score": 0.739,
        },
        "hesitation": {
            "score": 0.227,
        },
        "confidence": {
            "score": 0.713,
        },
        "engagement": {
            "score": 0.792,
        },
        "cognitive_load": {
            "score": 0.274,
        },
    }

    persisted_turn = Mock()
    persisted_turn.user_message = "I am ready to continue."
    persisted_turn.assistant_message = "Great, let's continue."
    persisted_turn.human_state = persisted_state
    persisted_turn.dialogue_strategy = "continue"

    repository.get_or_create_session.return_value = Mock()
    repository.get_turns.return_value = [persisted_turn]

    llm_provider = Mock()
    llm_provider.generate.return_value = "Restored conversation response."

    service = PipelineService(
        llm_provider=llm_provider,
        session_id="restart-test-session",
        repository=repository,
    )

    history = service.dialogue_service.get_history()
    trajectory = service.human_state_engine.get_state_trajectory()

    assert len(history) == 1
    assert history[0]["user_message"] == "I am ready to continue."
    assert history[0]["assistant_message"] == "Great, let's continue."
    assert history[0]["dialogue_strategy"] == "continue"

    assert len(trajectory) == 1
    assert trajectory[0]["emotion"]["label"] == "excited"
    assert trajectory[0]["emotion"]["score"] == 0.739
    assert trajectory[0]["hesitation"] == 0.227
    assert trajectory[0]["confidence"] == 0.713
    assert trajectory[0]["engagement"] == 0.792
    assert trajectory[0]["cognitive_load"] == 0.274

    repository.get_or_create_session.assert_called_once_with(
        "restart-test-session"
    )
    repository.get_turns.assert_called_once()


def test_pipeline_enables_temporal_smoothing():
    service = PipelineService()

    assert service.human_state_engine.enable_temporal_smoothing is True


def test_restored_history_does_not_initialize_smoother_baseline():
    from ai.human_state.temporal_smoother import TemporalSmoother

    repository = Mock()
    persisted_state = {
        "emotion": {"label": "excited", "score": 0.9},
        "hesitation": {"score": 0.9},
        "confidence": {"score": 0.9},
        "engagement": {"score": 0.9},
        "cognitive_load": {"score": 0.9},
    }

    persisted_turn = Mock()
    persisted_turn.user_message = "Previous message"
    persisted_turn.assistant_message = "Previous response"
    persisted_turn.human_state = persisted_state
    persisted_turn.dialogue_strategy = "continue"

    repository.get_turns.return_value = [persisted_turn]

    service = PipelineService(
        session_id="restore-smoother-test",
        repository=repository,
    )

    assert len(service.human_state_engine.get_state_history()) == 1

    # Restored history is for trajectory reconstruction, not a new
    # acoustic observation. The smoother should have no baseline yet.
    assert service.human_state_engine.temporal_smoother._previous is None


def test_pipeline_services_have_independent_smoothing_context():
    first = PipelineService()
    second = PipelineService()

    assert first.human_state_engine is not second.human_state_engine
    assert (
        first.human_state_engine.temporal_smoother
        is not second.human_state_engine.temporal_smoother
    )

def test_persisted_human_state_includes_temporal_metadata():
    from ai.human_state.hsr import build_human_state

    state = build_human_state(
        emotion_label="happy",
        emotion_score=0.8,
        hesitation_score=0.2,
        confidence_score=0.7,
        engagement_score=0.9,
        cognitive_load_score=0.3,
        timestamp=123.5,
        observation_valid=False,
    )

    public_hsr = state.to_dict()
    persisted = PipelineService._build_persisted_human_state(
        public_hsr,
        state,
    )

    assert set(public_hsr) == {
        "emotion",
        "hesitation",
        "confidence",
        "engagement",
        "cognitive_load",
    }
    assert persisted["_temporal"] == {
        "timestamp": 123.5,
        "observation_valid": False,
        "source": "audio",
    }


def test_restore_history_restores_temporal_metadata():
    repository = Mock()
    persisted_state = {
        "emotion": {"label": "happy", "score": 0.8},
        "hesitation": {"score": 0.2},
        "confidence": {"score": 0.7},
        "engagement": {"score": 0.9},
        "cognitive_load": {"score": 0.3},
        "_temporal": {
            "timestamp": 123.5,
            "observation_valid": False,
        },
    }

    persisted_turn = Mock()
    persisted_turn.user_message = "Previous message"
    persisted_turn.assistant_message = "Previous response"
    persisted_turn.human_state = persisted_state
    persisted_turn.dialogue_strategy = "continue"
    repository.get_turns.return_value = [persisted_turn]

    service = PipelineService(
        session_id="temporal-restore-test",
        repository=repository,
    )

    restored = service.human_state_engine.get_state_history()[0]

    assert restored.timestamp == 123.5
    assert restored.observation_valid is False


def test_restore_legacy_human_state_without_temporal_metadata():
    repository = Mock()
    persisted_turn = Mock()
    persisted_turn.user_message = "Older message"
    persisted_turn.assistant_message = "Older response"
    persisted_turn.human_state = {
        "emotion": {"label": "neutral", "score": 0.6},
        "hesitation": {"score": 0.2},
        "confidence": {"score": 0.7},
        "engagement": {"score": 0.8},
        "cognitive_load": {"score": 0.3},
    }
    persisted_turn.dialogue_strategy = "continue"
    repository.get_turns.return_value = [persisted_turn]

    service = PipelineService(
        session_id="legacy-restore-test",
        repository=repository,
    )

    restored = service.human_state_engine.get_state_history()[0]

    assert restored.timestamp is None
    assert restored.observation_valid is True

def test_process_audio_passes_timestamp_to_human_state_engine():
    from unittest.mock import Mock, patch

    from ai.human_state.hsr import build_human_state

    service = PipelineService()
    service.speech_service = Mock()
    service.speech_service.process.return_value = {
        "transcript": "Testing timestamp propagation",
        "audio": {},
        "features": {},
        "vad": {},
    }

    state = build_human_state(
        emotion_label="neutral",
        emotion_score=0.6,
        hesitation_score=0.2,
        confidence_score=0.7,
        engagement_score=0.8,
        cognitive_load_score=0.3,
        timestamp=123.0,
    )

    service.human_state_engine = Mock()
    service.human_state_engine.process_to_dict.return_value = (
        state.to_dict()
    )
    service.human_state_engine.get_current_state.return_value = state

    service.dialogue_service = Mock()
    service.dialogue_service.process.return_value = {
        "prompt": "Test prompt",
        "policy": {"strategy": "continue"},
    }
    service.llm_service = Mock()
    service.llm_service.generate.return_value = "Test response"

    with patch("backend.app.services.pipeline_service.time.time", return_value=123.0):
        service.process_audio("test.wav")

    service.human_state_engine.process_to_dict.assert_called_once()

    _, kwargs = service.human_state_engine.process_to_dict.call_args
    assert kwargs["timestamp"] == 123.0


def test_process_audio_persists_temporal_metadata():
    from unittest.mock import Mock, patch

    from ai.human_state.hsr import build_human_state

    repository = Mock()
    repository.get_turns.return_value=[]
    service = PipelineService(
        session_id="persistence-test-session",
        repository=repository,
    )

    service.speech_service = Mock()
    service.speech_service.process.return_value = {
        "transcript": "Test persistence",
        "audio": {},
        "features": {},
        "vad": {},
    }

    state = build_human_state(
        emotion_label="neutral",
        emotion_score=0.6,
        hesitation_score=0.2,
        confidence_score=0.7,
        engagement_score=0.8,
        cognitive_load_score=0.3,
        timestamp=123.0,
        observation_valid=True,
    )

    service.human_state_engine = Mock()
    service.human_state_engine.process_to_dict.return_value = state.to_dict()
    service.human_state_engine.get_current_state.return_value = state

    service.dialogue_service = Mock()
    service.dialogue_service.process.return_value = {
        "prompt": "Test prompt",
        "policy": {"strategy": "continue"},
    }

    service.llm_service = Mock()
    service.llm_service.generate.return_value = "Test response"

    with patch(
        "backend.app.services.pipeline_service.time.time",
        return_value=123.0,
    ):
        result = service.process_audio("test.wav")

    repository.add_turn.assert_called_once()
    saved_state = repository.add_turn.call_args.kwargs["human_state"]

    assert saved_state == result["human_state"]
    assert saved_state["_temporal"] == {
        "timestamp": 123.0,
        "observation_valid": True,
        "source": "audio",
    }

@pytest.mark.parametrize(
    ("speech_result", "expected_valid"),
    [
        (
            {
                "audio": {"duration": 2.0, "speech_duration": 1.5},
                "vad": {"speech_segments": [{"start": 0.2, "end": 1.7}]},
                "transcript": "Hello there",
                "features": {},
            },
            True,
        ),
        (
            {
                "audio": {"duration": 0.0, "speech_duration": 0.0},
                "vad": {"speech_segments": []},
                "transcript": "",
                "features": {},
            },
            False,
        ),
        (
            {
                "audio": {"duration": 2.0, "speech_duration": 0.0},
                "vad": {"speech_segments": []},
                "transcript": "",
                "features": {},
            },
            False,
        ),
        (
            {
                "audio": {"duration": 2.0, "speech_duration": 1.5},
                "vad": {"speech_segments": [{"start": 0.2, "end": 1.7}]},
                "transcript": "",
                "features": {},
            },
            True,
        ),
    ],
)
def test_observation_validity_from_speech_result(
    speech_result,
    expected_valid,
):
    assert (
        PipelineService._is_valid_observation(speech_result)
        is expected_valid
    )


@pytest.mark.parametrize(
    "speech_result",
    [
        None,
        {},
        {"audio": None, "vad": None},
        {"audio": [], "vad": {}},
        {"audio": {}, "vad": []},
        {
            "audio": {"duration": float("nan"), "speech_duration": 1.0},
            "vad": {"speech_segments": [{"start": 0.0, "end": 1.0}]},
        },
        {
            "audio": {"duration": float("inf"), "speech_duration": 1.0},
            "vad": {"speech_segments": [{"start": 0.0, "end": 1.0}]},
        },
        {
            "audio": {"duration": 2.0, "speech_duration": float("nan")},
            "vad": {"speech_segments": [{"start": 0.0, "end": 1.0}]},
        },
    ],
)
def test_invalid_or_malformed_speech_results_are_rejected(speech_result):
    assert PipelineService._is_valid_observation(speech_result) is False

def test_pipeline_does_not_add_dialogue_memory_when_persistence_fails():
    from unittest.mock import Mock

    import pytest

    repository = Mock()
    repository.get_turns.return_value = []
    repository.add_turn.side_effect = RuntimeError("database unavailable")

    service = PipelineService(
        session_id="persistence-failure-test",
        repository=repository,
    )

    service.speech_service = Mock()
    service.speech_service.process.return_value = {
        "transcript": "Test persistence failure",
        "audio": {},
        "features": {},
        "vad": {},
    }

    state = {
        "emotion": {"label": "neutral", "score": 0.6},
        "hesitation": {"score": 0.2},
        "confidence": {"score": 0.7},
        "engagement": {"score": 0.8},
        "cognitive_load": {"score": 0.3},
    }

    service.human_state_engine.process_to_dict = Mock(return_value=state)
    service.human_state_engine.get_current_state = Mock(return_value=None)
    service.dialogue_service.process = Mock(
        return_value={
            "prompt": "Test prompt",
            "policy": {"strategy": "continue"},
        }
    )
    service.dialogue_service.add_response = Mock()
    service.llm_service.generate = Mock(return_value="Test response")

    with pytest.raises(RuntimeError, match="database unavailable"):
        service.process_audio("test.wav")

    service.dialogue_service.add_response.assert_not_called()


def test_pipeline_does_not_persist_or_add_dialogue_memory_on_llm_timeout():
    from unittest.mock import Mock

    import pytest

    repository = Mock()
    repository.get_turns.return_value = []

    service = PipelineService(
        session_id="llm-timeout-test",
        repository=repository,
    )

    service.speech_service = Mock()
    service.speech_service.process.return_value = {
        "transcript": "Test timeout",
        "audio": {},
        "features": {},
        "vad": {},
    }

    state = {
        "emotion": {"label": "neutral", "score": 0.5},
        "hesitation": {"score": 0.0},
        "confidence": {"score": 0.5},
        "cognitive_load": {"score": 0.3},
    }

    service.human_state_engine.process_to_dict = Mock(
        return_value=state
    )
    service.human_state_engine.get_current_state = Mock(
        return_value=None
    )

    service.dialogue_service.process = Mock(
        return_value={
            "prompt": "Test prompt",
            "policy": {"strategy": "continue"},
        }
    )
    service.dialogue_service.add_response = Mock()

    service.llm_service.generate = Mock(
        side_effect=TimeoutError("Request timed out")
    )

    with pytest.raises(TimeoutError, match="Request timed out"):
        service.process_audio("test.wav")

    repository.add_turn.assert_not_called()
    service.dialogue_service.add_response.assert_not_called()


def test_text_only_message_passes_invalid_observation_metadata_to_dialogue():
    repository = Mock()
    repository.get_turns.return_value = []
    llm_provider = Mock()
    llm_provider.generate.return_value = "A normal response."
    service = PipelineService(
        llm_provider=llm_provider,
        session_id="text-only-neutral-state-test",
        repository=repository,
    )

    result = service.process_text("Explain this topic.")

    assert result["dialogue"]["dialogue_state"]["emotion"] == "unknown"
    assert result["dialogue"]["dialogue_state"]["interaction_state"] == "neutral"
    assert result["dialogue"]["dialogue_state"]["needs_clarification"] is False
    assert result["dialogue"]["dialogue_state"]["needs_encouragement"] is False
    assert result["dialogue"]["policy"]["strategy"] == "normal_response"
    assert result["human_state"]["_temporal"]["source"] == "text_only"
    assert result["human_state"]["_temporal"]["observation_valid"] is False
    repository.add_turn.assert_called_once()
    persisted_state = repository.add_turn.call_args.kwargs["human_state"]
    assert persisted_state["_temporal"]["observation_valid"] is False


def test_text_turn_after_audio_does_not_reuse_previous_emotion_measurement():
    repository = Mock()
    repository.get_turns.return_value = []
    llm_provider = Mock()
    llm_provider.generate.return_value = "A response."
    service = PipelineService(
        llm_provider=llm_provider,
        session_id="audio-then-text-test",
        repository=repository,
    )
    service.speech_service.process = Mock(
        return_value={
            "transcript": "I feel very excited.",
            "language": "en",
            "language_probability": 0.99,
            "audio": {"duration": 1.0, "speech_duration": 0.8},
            "vad": {"speech_segments": [{"start": 0.1, "end": 0.9}]},
            "features": {
                "mean_pitch": 250,
                "min_pitch": 120,
                "max_pitch": 300,
                "mean_energy": 0.14,
            },
        }
    )

    audio_result = service.process_audio("unused.wav")
    text_result = service.process_text("And now a text-only follow-up.")

    assert audio_result["human_state"]["emotion"]["label"] == "excited"
    assert text_result["human_state"]["emotion"] == {
        "label": "unknown",
        "score": 0.0,
    }
    assert text_result["human_state"]["_temporal"] == {
        "observation_valid": False,
        "source": "text_only",
    }
    assert text_result["dialogue"]["dialogue_state"]["emotion"] == "unknown"
    assert repository.add_turn.call_count == 2
    persisted_text_state = repository.add_turn.call_args.kwargs["human_state"]
    assert persisted_text_state["emotion"]["label"] == "unknown"
    assert persisted_text_state["_temporal"]["observation_valid"] is False


def test_consecutive_audio_turns_report_changing_emotions_immediately():
    provider = Mock()
    provider.generate.return_value = "Recorded response."
    service = PipelineService(llm_provider=provider)
    service.speech_service.process = Mock(
        side_effect=[
            {
                "transcript": "I feel low.",
                "audio": {"duration": 1.0, "speech_duration": 0.8},
                "vad": {"speech_segments": [{"start": 0.1, "end": 0.9}]},
                "features": {
                    "mean_pitch": 150,
                    "min_pitch": 130,
                    "max_pitch": 165,
                    "mean_energy": 0.02,
                },
            },
            {
                "transcript": "I feel energized.",
                "audio": {"duration": 1.0, "speech_duration": 0.8},
                "vad": {"speech_segments": [{"start": 0.1, "end": 0.9}]},
                "features": {
                    "mean_pitch": 250,
                    "min_pitch": 120,
                    "max_pitch": 300,
                    "mean_energy": 0.14,
                },
            },
        ]
    )

    first = service.process_audio("first.wav")
    previous_baseline = service.human_state_engine.temporal_smoother._previous
    second = service.process_audio("second.wav")

    assert first["human_state"]["emotion"]["label"] == "sad"
    assert second["human_state"]["emotion"]["label"] == "excited"
    assert previous_baseline.emotion.label == "sad"
    assert service.human_state_engine.temporal_smoother._previous.emotion.label == "excited"


def test_invalid_audio_turn_does_not_change_smoother_baseline():
    provider = Mock()
    provider.generate.return_value = "Recorded response."
    service = PipelineService(llm_provider=provider)
    service.speech_service.process = Mock(
        side_effect=[
            {
                "transcript": "A valid audio turn.",
                "audio": {"duration": 1.0, "speech_duration": 0.8},
                "vad": {"speech_segments": [{"start": 0.1, "end": 0.9}]},
                "features": {
                    "mean_pitch": 150,
                    "min_pitch": 130,
                    "max_pitch": 165,
                    "mean_energy": 0.02,
                },
            },
            {
                "transcript": "A transcript with no detected speech.",
                "audio": {"duration": 1.0, "speech_duration": 0.0},
                "vad": {"speech_segments": []},
                "features": {},
            },
            {
                "transcript": "A different emotional audio turn.",
                "audio": {"duration": 1.0, "speech_duration": 0.8},
                "vad": {"speech_segments": [{"start": 0.1, "end": 0.9}]},
                "features": {
                    "mean_pitch": 250,
                    "min_pitch": 120,
                    "max_pitch": 300,
                    "mean_energy": 0.14,
                },
            },
        ]
    )

    first = service.process_audio("first.wav")
    baseline = service.human_state_engine.temporal_smoother._previous
    invalid = service.process_audio("invalid.wav")
    assert invalid["human_state"]["emotion"]["label"] == "unknown"
    assert invalid["human_state"]["_temporal"]["observation_valid"] is False
    assert service.human_state_engine.temporal_smoother._previous is baseline

    last = service.process_audio("last.wav")
    assert first["human_state"]["emotion"]["label"] == "sad"
    assert last["human_state"]["emotion"]["label"] == "excited"


def test_audio_with_unusable_emotion_features_is_marked_unmeasured():
    provider = Mock()
    provider.generate.return_value = "Recorded response."
    service = PipelineService(llm_provider=provider)
    service.speech_service.process = Mock(return_value={
        "transcript": "A clear transcript with no usable pitch estimate.",
        "audio": {"duration": 1.0, "speech_duration": 0.8},
        "vad": {"speech_segments": [{"start": 0.1, "end": 0.9}]},
        "features": {
            "mean_pitch": 0.0,
            "min_pitch": 0.0,
            "max_pitch": 0.0,
            "mean_energy": 0.12,
        },
    })

    result = service.process_audio("unmeasured.wav")

    assert result["human_state"]["emotion"] == {"label": "unknown", "score": 0.0}
    assert result["human_state"]["_temporal"]["observation_valid"] is False
    assert result["human_state"]["_temporal"]["source"] == "audio"
