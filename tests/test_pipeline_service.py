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

    service = PipelineService(
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