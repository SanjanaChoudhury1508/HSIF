import csv
import json
import random
import uuid
from datetime import datetime, timezone
from pathlib import Path
import sys
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
from time import perf_counter

from ai.dialogue.dialogue_service import DialogueService
from backend.app.services.llm.gemini_provider import (
    GeminiProvider,
    GeminiQuotaExceededError,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RESULTS_DIR = PROJECT_ROOT / "evaluation" / "results"

# Five controlled scenarios. Scores use the nested HumanState format
# expected by StateFusion.
SCENARIOS = [
    {
        "id": "confusion",
        "message": "I don't understand how recursion works. I've read the explanation several times, but I still can't follow it.",
        "state": {
            "emotion": {"label": "confused", "score": 0.85},
            "hesitation": {"score": 0.85},
            "confidence": {"score": 0.30},
            "engagement": {"score": 0.80},
            "cognitive_load": {"score": 0.55},
        },
    },
    {
        "id": "frustration",
        "message": "I've been debugging this same error for two hours. Nothing works and I'm getting really frustrated.",
        "state": {
            "emotion": {"label": "frustrated", "score": 0.90},
            "hesitation": {"score": 0.65},
            "confidence": {"score": 0.35},
            "engagement": {"score": 0.55},
            "cognitive_load": {"score": 0.75},
        },
    },
    {
        "id": "cognitive_overload",
        "message": "Explain how an operating system handles processes, threads, scheduling, memory management, and synchronization.",
        "state": {
            "emotion": {"label": "neutral", "score": 0.70},
            "hesitation": {"score": 0.55},
            "confidence": {"score": 0.45},
            "engagement": {"score": 0.65},
            "cognitive_load": {"score": 0.95},
        },
    },
    {
        "id": "low_engagement",
        "message": "I know I should study, but I keep losing focus and don't feel motivated to continue.",
        "state": {
            "emotion": {"label": "neutral", "score": 0.65},
            "hesitation": {"score": 0.40},
            "confidence": {"score": 0.50},
            "engagement": {"score": 0.20},
            "cognitive_load": {"score": 0.40},
        },
    },
    {
        "id": "normal_interaction",
        "message": "Can you explain the difference between a stack and a queue with a simple example?",
        "state": {
            "emotion": {"label": "neutral", "score": 0.90},
            "hesitation": {"score": 0.10},
            "confidence": {"score": 0.90},
            "engagement": {"score": 0.90},
            "cognitive_load": {"score": 0.20},
        },
    },
]


BASELINE_INSTRUCTIONS = """You are a helpful, knowledgeable conversational assistant.
Answer the user's question accurately and directly.
Use clear language and an appropriate level of detail.
Be respectful and constructive.
Do not assume anything about the user's emotional or cognitive state."""


def build_baseline_prompt(message: str) -> str:
    return (
        f"{BASELINE_INSTRUCTIONS}\n\n"
        f"User message:\n{message}\n\n"
        "Assistant response:"
    )


def build_adaptive_prompt(message: str, human_state: dict) -> tuple[str, dict]:
    # A fresh DialogueService prevents conversation history from
    # one scenario influencing another.
    dialogue_service = DialogueService(max_memory_turns=10)

    dialogue_result = dialogue_service.process(
        user_message=message,
        human_state=human_state,
    )

    return dialogue_result["prompt"], dialogue_result["policy"]


def generate_response(provider, prompt: str) -> dict:
    start = perf_counter()

    try:
        response = provider.generate(prompt)
        elapsed_ms = (perf_counter() - start) * 1000

        return {
            "success": True,
            "response": response,
            "latency_ms": round(elapsed_ms, 3),
            "error": None,
        }

    except Exception as exc:
        elapsed_ms = (perf_counter() - start) * 1000

        return {
            "success": False,
            "response": None,
            "latency_ms": round(elapsed_ms, 3),
            "error": f"{type(exc).__name__}: {exc}",
        }


def save_results(run_id: str, records: list[dict], model: str) -> None:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    json_path = RESULTS_DIR / f"gemini_response_{run_id}.json"
    csv_path = RESULTS_DIR / f"gemini_response_{run_id}.csv"
    review_path = RESULTS_DIR / f"gemini_blind_review_{run_id}.csv"

    payload = {
        "run_id": run_id,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "model": model,
        "scenario_count": len(SCENARIOS),
        "planned_api_requests": len(SCENARIOS) * 2,
        "completed_records": records,
    }

    json_path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    csv_fields = [
        "scenario_id",
        "variant",
        "policy_strategy",
        "success",
        "latency_ms",
        "prompt",
        "response",
        "error",
    ]

    with csv_path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=csv_fields)
        writer.writeheader()

        for record in records:
            writer.writerow({
                field: record.get(field)
                for field in csv_fields
            })

    # Blind A/B review sheet. The mapping from A/B to baseline/adaptive
    # remains in the JSON results, not in this review sheet.
    rng = random.Random(42)

    with review_path.open("w", newline="", encoding="utf-8") as file:
        fields = [
            "scenario_id",
            "response_A",
            "response_B",
            "A_relevance_1_to_5",
            "A_clarity_1_to_5",
            "A_empathy_appropriateness_1_to_5",
            "A_adaptation_1_to_5",
            "A_helpfulness_1_to_5",
            "B_relevance_1_to_5",
            "B_clarity_1_to_5",
            "B_empathy_appropriateness_1_to_5",
            "B_adaptation_1_to_5",
            "B_helpfulness_1_to_5",
            "preferred_response",
            "notes",
        ]

        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()

        for scenario in SCENARIOS:
            baseline = next(
                (r for r in records
                 if r["scenario_id"] == scenario["id"]
                 and r["variant"] == "baseline"),
                None,
            )
            adaptive = next(
                (r for r in records
                 if r["scenario_id"] == scenario["id"]
                 and r["variant"] == "adaptive"),
                None,
            )

            if not baseline or not adaptive:
                continue

            variants = [
                ("baseline", baseline["response"]),
                ("adaptive", adaptive["response"]),
            ]
            rng.shuffle(variants)

            writer.writerow({
                "scenario_id": scenario["id"],
                "response_A": variants[0][1],
                "response_B": variants[1][1],
            })

    print("\nSaved:")
    print(json_path)
    print(csv_path)
    print(review_path)


def main():
    run_id = (
        datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        + "_"
        + uuid.uuid4().hex[:8]
    )

    provider = GeminiProvider()
    model = provider.model

    print(f"Gemini response benchmark")
    print(f"Run ID: {run_id}")
    print(f"Model: {model}")
    print(f"Scenarios: {len(SCENARIOS)}")
    print(f"Planned API requests: {len(SCENARIOS) * 2}")
    print("\nStarting sequential baseline/adaptive comparisons...\n")

    records = []
    quota_exceeded = False

    for index, scenario in enumerate(SCENARIOS, start=1):
        scenario_id = scenario["id"]

        print(f"[{index}/{len(SCENARIOS)}] {scenario_id}")

        adaptive_prompt, policy = build_adaptive_prompt(
            scenario["message"],
            scenario["state"],
        )

        prompts = [
            ("baseline", build_baseline_prompt(scenario["message"]), None),
            ("adaptive", adaptive_prompt, policy["strategy"]),
        ]

        for variant, prompt, strategy in prompts:
            print(f"  Calling Gemini: {variant}")

            result = generate_response(provider, prompt)

            record = {
                "scenario_id": scenario_id,
                "variant": variant,
                "policy_strategy": strategy,
                "success": result["success"],
                "latency_ms": result["latency_ms"],
                "prompt": prompt,
                "response": result["response"],
                "error": result["error"],
            }
            records.append(record)

            print(
                f"    Success: {result['success']} | "
                f"Latency: {result['latency_ms']} ms"
            )

            if not result["success"]:
                print(f"    Error: {result['error']}")

                if "GeminiQuotaExceededError" in (result["error"] or ""):
                    quota_exceeded = True
                    break

        if quota_exceeded:
            print("\nQuota exceeded. Stopping without further API calls.")
            break

    save_results(run_id, records, model)

    successful = sum(record["success"] for record in records)
    print("\nBenchmark summary")
    print(f"Completed calls: {len(records)}")
    print(f"Successful calls: {successful}")
    print(f"Failed calls: {len(records) - successful}")
    print(f"Quota stopped run: {quota_exceeded}")


if __name__ == "__main__":
    main()