from __future__ import annotations

import csv
import json
import platform
import statistics
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ai.dialogue.dialogue_service import DialogueService
from ai.dialogue.prompts.prompt_builder import PromptBuilder

RESULTS_DIR = ROOT / "evaluation" / "results"
REPEATS = 30

CASES = [
    {
        "case_id": "neutral",
        "message": "Explain what a neural network is.",
        "state": {
            "emotion": {"label": "neutral", "score": 0.7},
            "hesitation": {"score": 0.1},
            "confidence": {"score": 0.9},
            "engagement": {"score": 0.9},
            "cognitive_load": {"score": 0.2},
        },
        "expected_strategy": "continue",
    },
    {
        "case_id": "struggling",
        "message": "I still do not understand this concept.",
        "state": {
            "emotion": {"label": "confused", "score": 0.8},
            "hesitation": {"score": 0.8},
            "confidence": {"score": 0.3},
            "engagement": {"score": 0.7},
            "cognitive_load": {"score": 0.5},
        },
        "expected_strategy": "reassure",
    },
    {
        "case_id": "overloaded",
        "message": "There are too many steps to follow.",
        "state": {
            "emotion": {"label": "neutral", "score": 0.6},
            "hesitation": {"score": 0.3},
            "confidence": {"score": 0.7},
            "engagement": {"score": 0.6},
            "cognitive_load": {"score": 0.9},
        },
        "expected_strategy": "reduce_information",
    },
    {
        "case_id": "frustrated",
        "message": "This is frustrating. I still cannot get it.",
        "state": {
            "emotion": {"label": "frustrated", "score": 0.9},
            "hesitation": {"score": 0.6},
            "confidence": {"score": 0.4},
            "engagement": {"score": 0.6},
            "cognitive_load": {"score": 0.7},
        },
        "expected_strategy": "acknowledge_frustration",
    },
    {
        "case_id": "disengaged",
        "message": "Okay...",
        "state": {
            "emotion": {"label": "neutral", "score": 0.6},
            "hesitation": {"score": 0.2},
            "confidence": {"score": 0.6},
            "engagement": {"score": 0.2},
            "cognitive_load": {"score": 0.3},
        },
        "expected_strategy": "re_engage",
    },
]


def percentile(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, int((len(ordered) - 1) * fraction)))
    return ordered[index]


def run_once(case: dict, mode: str) -> dict:
    service = DialogueService()
    start = time.perf_counter()

    if mode == "adaptive":
        result = service.process(case["message"], case["state"])
        strategy = result["policy"]["strategy"]
        prompt = result["prompt"]
    else:
        neutral_state = {
            "emotion": {"label": "neutral", "score": 0.5},
            "hesitation": {"score": 0.5},
            "confidence": {"score": 0.5},
            "engagement": {"score": 0.5},
            "cognitive_load": {"score": 0.5},
        }
        dialogue_state = {
            "emotion": "neutral",
            "emotion_score": 0.5,
            "hesitation": 0.5,
            "confidence": 0.5,
            "engagement": 0.5,
            "cognitive_load": 0.5,
            "interaction_state": "neutral",
            "needs_clarification": False,
            "needs_encouragement": False,
        }
        policy = {
            "strategy": "normal_response",
            "reason": "Baseline uses a fixed response strategy.",
            "priority": "low",
            "response_style": "natural",
            "complexity": "moderate",
            "detail_level": "moderate",
        }
        prompt = PromptBuilder.build(
            user_message=case["message"],
            dialogue_state=dialogue_state,
            policy_decision=policy,
            conversation_history=[],
        )
        strategy = "normal_response"

    elapsed_ms = (time.perf_counter() - start) * 1000
    return {
        "mode": mode,
        "case_id": case["case_id"],
        "latency_ms": elapsed_ms,
        "strategy": strategy,
        "prompt_chars": len(prompt),
        "prompt_words": len(prompt.split()),
        "valid_output": bool(prompt.strip()) and bool(strategy),
        "expected_strategy": case["expected_strategy"],
        "strategy_matches_expectation": (
            mode == "adaptive" and strategy == case["expected_strategy"]
        ),
    }


def main() -> None:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "_" + uuid.uuid4().hex[:8]
    records = []

    # Warm up both paths; warm-up measurements are excluded.
    for mode in ("baseline", "adaptive"):
        run_once(CASES[0], mode)

    for case in CASES:
        for mode in ("baseline", "adaptive"):
            for _ in range(REPEATS):
                try:
                    records.append(run_once(case, mode))
                except Exception as exc:
                    records.append({
                        "mode": mode,
                        "case_id": case["case_id"],
                        "error": f"{type(exc).__name__}: {exc}",
                        "valid_output": False,
                        "expected_strategy": case["expected_strategy"],
                        "strategy_matches_expectation": False,
                    })

    summary = {}
    for mode in ("baseline", "adaptive"):
        successful = [
            row for row in records
            if row["mode"] == mode and row.get("valid_output")
        ]
        latencies = [row["latency_ms"] for row in successful]
        summary[mode] = {
            "runs": sum(row["mode"] == mode for row in records),
            "successful_runs": len(successful),
            "success_rate": len(successful) / max(
                1, sum(row["mode"] == mode for row in records)
            ),
            "mean_latency_ms": statistics.mean(latencies) if latencies else None,
            "median_latency_ms": statistics.median(latencies) if latencies else None,
            "p95_latency_ms": percentile(latencies, 0.95) if latencies else None,
            "mean_prompt_chars": statistics.mean(
                row["prompt_chars"] for row in successful
            ) if successful else None,
            "mean_prompt_words": statistics.mean(
                row["prompt_words"] for row in successful
            ) if successful else None,
        }

    adaptive_rows = [
        row for row in records
        if row["mode"] == "adaptive" and row.get("valid_output")
    ]
    summary["adaptive"]["expected_strategy_matches"] = sum(
        row["strategy_matches_expectation"] for row in adaptive_rows
    )
    summary["adaptive"]["expected_strategy_match_rate"] = (
        summary["adaptive"]["expected_strategy_matches"] / len(adaptive_rows)
        if adaptive_rows else None
    )

    payload = {
        "run_id": run_id,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "benchmark": "controlled_dialogue_pipeline_baseline_vs_adaptive",
        "repeats_per_case_per_mode": REPEATS,
        "case_count": len(CASES),
        "total_attempts": len(records),
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "limitations": [
            "Synthetic, hand-authored human-state profiles; no human-subject evaluation.",
            "Measures local pipeline latency and prompt properties, not LLM generation quality.",
            "Expected strategy checks validate configured rule behavior, not user benefit.",
            "Baseline uses a fixed neutral policy and the same prompt builder; this is a controlled comparator, not a historical production baseline.",
        ],
        "summary": summary,
        "records": records,
    }

    json_path = RESULTS_DIR / f"dialogue_{run_id}.json"
    csv_path = RESULTS_DIR / f"dialogue_{run_id}.csv"

    json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    columns = sorted({key for row in records for key in row})
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerows(records)

    print(f"run_id: {run_id}")
    print(f"json: {json_path.relative_to(ROOT)}")
    print(f"csv: {csv_path.relative_to(ROOT)}")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
