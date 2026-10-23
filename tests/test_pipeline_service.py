import pytest
from unittest.mock import Mock

from backend.app.services.pipeline_service import PipelineService


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

def test_pipeline_adapts_to_high_cognitive_load():
    llm_provider = Mock()
    llm_provider.generate.return_value = "Here is a simpler explanation."

    service = PipelineService(llm_provider=llm_provider)

    service.speech_service.process = Mock(
        return_value={
            "transcript": "There is too much information and I am getting confused.",
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
