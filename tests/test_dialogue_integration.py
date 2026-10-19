from ai.dialogue.dialogue_service import DialogueService


def test_normal_state_uses_normal_response():
    service = DialogueService()

    human_state = {
        "emotion": {
            "label": "neutral",
            "score": 0.7,
        },
        "hesitation": {
            "score": 0.1,
        },
        "confidence": {
            "score": 0.85,
        },
        "engagement": {
            "score": 0.85,
        },
        "cognitive_load": {
            "score": 0.2,
        },
    }

    result = service.process(
        "Can you explain this concept?",
        human_state,
    )

    assert result["policy"]["strategy"] in {
        "normal_response",
        "continue",
    }


def test_high_cognitive_load_adapts_dialogue():
    service = DialogueService()

    human_state = {
        "emotion": {
            "label": "neutral",
            "score": 0.6,
        },
        "hesitation": {
            "score": 0.3,
        },
        "confidence": {
            "score": 0.4,
        },
        "engagement": {
            "score": 0.6,
        },
        "cognitive_load": {
            "score": 0.9,
        },
    }

    result = service.process(
        "I don't understand how this works.",
        human_state,
    )

    assert result["policy"]["strategy"] in {
        "simplify",
        "slow_down",
        "reduce_information",
    }


def test_frustrated_user_adapts_dialogue():
    service = DialogueService()

    human_state = {
        "emotion": {
            "label": "frustrated",
            "score": 0.9,
        },
        "hesitation": {
            "score": 0.4,
        },
        "confidence": {
            "score": 0.3,
        },
        "engagement": {
            "score": 0.5,
        },
        "cognitive_load": {
            "score": 0.7,
        },
    }

    result = service.process(
        "This is really frustrating. I still don't understand it.",
        human_state,
    )

    assert result["policy"]["strategy"] in {
        "acknowledge_frustration",
        "reassure",
        "simplify",
        "slow_down",
    }


def test_low_engagement_adapts_dialogue():
    service = DialogueService()

    human_state = {
        "emotion": {
            "label": "neutral",
            "score": 0.6,
        },
        "hesitation": {
            "score": 0.2,
        },
        "confidence": {
            "score": 0.6,
        },
        "engagement": {
            "score": 0.2,
        },
        "cognitive_load": {
            "score": 0.3,
        },
    }

    result = service.process(
        "Okay...",
        human_state,
    )

    assert result["policy"]["strategy"] in {
        "re_engage",
        "encourage",
        "continue",
    }


def test_conversation_memory_accumulates_turns():
    service = DialogueService()

    state = {
        "emotion": {
            "label": "neutral",
            "score": 0.7,
        },
        "hesitation": {
            "score": 0.1,
        },
        "confidence": {
            "score": 0.8,
        },
        "engagement": {
            "score": 0.8,
        },
        "cognitive_load": {
            "score": 0.2,
        },
    }

    first = service.process(
        "What is a neural network?",
        state,
    )

    service.add_response(
        user_message="What is a neural network?",
        assistant_message="A neural network is a machine learning model.",
        human_state=state,
        dialogue_strategy=first["policy"]["strategy"],
    )

    second = service.process(
        "Can you explain that more simply?",
        state,
    )

    assert len(second["history"]) == 1
    assert second["history"][0]["user_message"] == "What is a neural network?"
    assert (
        second["history"][0]["assistant_message"]
        == "A neural network is a machine learning model."
    )