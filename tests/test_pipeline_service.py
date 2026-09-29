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