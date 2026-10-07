import time

from google.genai.errors import ServerError
from ai.dialogue.dialogue_service import DialogueService
from backend.app.services.llm.llm_service import LLMService

def generate_with_retry(llm_service, prompt, max_retries=3):
    for attempt in range(max_retries):
        try:
            return llm_service.generate(prompt)

        except ServerError as exc:
            if attempt == max_retries - 1:
                raise

            print(
                f"\nGemini temporarily unavailable "
                f"(attempt {attempt + 1}/{max_retries}). "
                "Retrying..."
            )

            time.sleep(3 * (attempt + 1))

def print_turn(turn_number, title, human_state, result, response):
    print("\n" + "=" * 70)
    print(f"TURN {turn_number} — {title}")
    print("=" * 70)

    print("\nHUMAN STATE")
    print(f"  Emotion:       {human_state['emotion']['label']}")
    print(f"  Hesitation:    {human_state['hesitation']['score']}")
    print(f"  Confidence:    {human_state['confidence']['score']}")
    print(f"  Engagement:    {human_state['engagement']['score']}")
    print(f"  Cognitive Load:{human_state['cognitive_load']['score']}")

    print("\nDIALOGUE POLICY")
    print(f"  Strategy:      {result['policy']['strategy']}")
    print(f"  Priority:      {result['policy']['priority']}")
    print(f"  Reason:        {result['policy']['reason']}")

    print("\nCONVERSATION HISTORY")
    print(f"  Previous turns: {len(result['history'])}")

    print("\nGEMINI RESPONSE")
    print(response)


def main():
    print("=" * 70)
    print("HSIF — ADAPTIVE MULTI-TURN CONVERSATION DEMO")
    print("=" * 70)

    dialogue_service = DialogueService()
    llm_service = LLMService()

    # ---------------------------------------------------------
    # TURN 1 — Confident / engaged user
    # ---------------------------------------------------------
    state_1 = {
        "emotion": {
            "label": "neutral",
            "score": 0.70,
        },
        "hesitation": {
            "score": 0.10,
        },
        "confidence": {
            "score": 0.85,
        },
        "engagement": {
            "score": 0.90,
        },
        "cognitive_load": {
            "score": 0.20,
        },
    }

    user_1 = "Can you explain what a neural network is?"

    result_1 = dialogue_service.process(
        user_message=user_1,
        human_state=state_1,
    )

    response_1 = generate_with_retry(
        llm_service,
        result_1["prompt"],
    )

    dialogue_service.add_response(
        user_message=user_1,
        assistant_message=response_1,
        human_state=state_1,
        dialogue_strategy=result_1["policy"]["strategy"],
    )

    print_turn(
        1,
        "CONFIDENT USER",
        state_1,
        result_1,
        response_1,
    )

    # ---------------------------------------------------------
    # TURN 2 — High cognitive load / low confidence
    # ---------------------------------------------------------
    state_2 = {
        "emotion": {
            "label": "confused",
            "score": 0.85,
        },
        "hesitation": {
            "score": 0.65,
        },
        "confidence": {
            "score": 0.30,
        },
        "engagement": {
            "score": 0.55,
        },
        "cognitive_load": {
            "score": 0.90,
        },
    }

    user_2 = "I still don't understand this. Can you explain it more simply?"

    result_2 = dialogue_service.process(
        user_message=user_2,
        human_state=state_2,
    )

    response_2 = generate_with_retry(
        llm_service,
        result_2["prompt"],
    )

    dialogue_service.add_response(
        user_message=user_2,
        assistant_message=response_2,
        human_state=state_2,
        dialogue_strategy=result_2["policy"]["strategy"],
    )

    print_turn(
        2,
        "CONFUSED / HIGH COGNITIVE LOAD",
        state_2,
        result_2,
        response_2,
    )

    # ---------------------------------------------------------
    # TURN 3 — Frustrated / low confidence
    # ---------------------------------------------------------
    state_3 = {
        "emotion": {
            "label": "frustrated",
            "score": 0.92,
        },
        "hesitation": {
            "score": 0.70,
        },
        "confidence": {
            "score": 0.20,
        },
        "engagement": {
            "score": 0.40,
        },
        "cognitive_load": {
            "score": 0.85,
        },
    }

    user_3 = "This is really frustrating. I feel like I'm not getting it."

    result_3 = dialogue_service.process(
        user_message=user_3,
        human_state=state_3,
    )

    response_3 = generate_with_retry(
        llm_service,
        result_3["prompt"],
    )

    dialogue_service.add_response(
        user_message=user_3,
        assistant_message=response_3,
        human_state=state_3,
        dialogue_strategy=result_3["policy"]["strategy"],
    )

    print_turn(
        3,
        "FRUSTRATED / LOW CONFIDENCE",
        state_3,
        result_3,
        response_3,
    )

    # ---------------------------------------------------------
    # FINAL SUMMARY
    # ---------------------------------------------------------
    print("\n" + "=" * 70)
    print("ADAPTATION SUMMARY")
    print("=" * 70)

    print("\nStrategies selected:")
    print(f"  Turn 1 → {result_1['policy']['strategy']}")
    print(f"  Turn 2 → {result_2['policy']['strategy']}")
    print(f"  Turn 3 → {result_3['policy']['strategy']}")

    print("\nConversation memory:")
    print(f"  Stored turns → {len(dialogue_service.get_history())}")

    print("\nHSIF adaptive conversation demo complete.")


if __name__ == "__main__":
    main()