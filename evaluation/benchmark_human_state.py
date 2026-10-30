
"""Standalone behavioral benchmark for the HSIF Human State Engine.

Synthetic profiles assess heuristic consistency only.
They do not measure psychological accuracy.
"""

import csv
import json
import math
import platform
import statistics
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from ai.human_state.human_state_engine import HumanStateEngine

RESULTS_DIR = ROOT / "evaluation" / "results"
REPEATS = 5

SCORE_FIELDS = (
    "hesitation",
    "confidence",
    "engagement",
    "cognitive_load",
)

# Fixed synthetic inputs, not human-labeled observations.
PROFILES = {
    "typical_speech": {
        "transcript": "This is a representative speech sample.",
        "language": "en",
        "audio": {
            "duration": 6.0,
            "speech_duration": 5.2,
            "silence_duration": 0.8,
        },
        "features": {
            "number_of_pauses": 2,
            "average_pause_duration": 0.3,
            "max_pause_duration": 0.5,
            "mean_energy": 0.08,
            "mean_pitch": 180.0,
            "min_pitch": 100.0,
            "max_pitch": 240.0,
        },
        "vad": {"speech_segments": [], "pauses": []},
    },
    "frequent_long_pauses": {
        "transcript": "This is a sample with pauses.",
        "language": "en",
        "audio": {
            "duration": 8.0,
            "speech_duration": 4.0,
            "silence_duration": 4.0,
        },
        "features": {
            "number_of_pauses": 8,
            "average_pause_duration": 0.5,
            "max_pause_duration": 1.5,
            "mean_energy": 0.08,
            "mean_pitch": 180.0,
            "min_pitch": 100.0,
            "max_pitch": 240.0,
        },
        "vad": {"speech_segments": [], "pauses": []},
    },
    "low_energy_speech": {
        "transcript": "This is a quiet sample.",
        "language": "en",
        "audio": {
            "duration": 6.0,
            "speech_duration": 5.2,
            "silence_duration": 0.8,
        },
        "features": {
            "number_of_pauses": 2,
            "average_pause_duration": 0.3,
            "max_pause_duration": 0.5,
            "mean_energy": 0.01,
            "mean_pitch": 180.0,
            "min_pitch": 100.0,
            "max_pitch": 240.0,
        },
        "vad": {"speech_segments": [], "pauses": []},
    },
    "missing_features": {
        "transcript": "",
        "language": "en",
        "audio": {
            "duration": 0.0,
            "speech_duration": 0.0,
            "silence_duration": 0.0,
        },
        "features": {},
        "vad": {"speech_segments": [], "pauses": []},
    },
}


def extract_scores(result):
    """Extract and validate the stable HSR dictionary."""
    emotion = result["emotion"]
    assert emotion["label"] in {
        "neutral", "excited", "sad", "happy"
    }
    assert isinstance(emotion["score"], (int, float))

    scores = {"emotion": float(emotion["score"])}
    for field in SCORE_FIELDS:
        scores[field] = float(result[field]["score"])

    for field, score in scores.items():
        assert math.isfinite(score), f"{field} is not finite"
        assert 0.0 <= score <= 1.0, f"{field} out of range: {score}"

    return {"emotion_label": emotion["label"], **scores}


def evaluate_profile(name, speech_result):
    timings_ms = []
    outputs = []

    for _ in range(REPEATS):
        # Fresh engine per run avoids history affecting measurements.
        engine = HumanStateEngine()
        started = time.perf_counter()
        result = engine.process_to_dict(speech_result)
        elapsed_ms = (time.perf_counter() - started) * 1000

        timings_ms.append(elapsed_ms)
        outputs.append(extract_scores(result))

    # Exact output comparison checks deterministic behavior.
    deterministic = all(output == outputs[0] for output in outputs)

    return {
        "profile": name,
        "repeats": REPEATS,
        "valid_outputs": len(outputs),
        "deterministic": deterministic,
        "mean_latency_ms": statistics.mean(timings_ms),
        "median_latency_ms": statistics.median(timings_ms),
        "min_latency_ms": min(timings_ms),
        "max_latency_ms": max(timings_ms),
        "output": outputs[0],
    }


def main():
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    run_id = (
        datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        + "_" + uuid.uuid4().hex[:8]
    )

    profile_results = [
        evaluate_profile(name, sample)
        for name, sample in PROFILES.items()
    ]

    typical = next(
        row for row in profile_results
        if row["profile"] == "typical_speech"
    )
    paused = next(
        row for row in profile_results
        if row["profile"] == "frequent_long_pauses"
    )

    # Behavioral checks only; these are not accuracy metrics.
    behavioral_checks = {
        "more_pauses_increase_hesitation": (
            paused["output"]["hesitation"]
            > typical["output"]["hesitation"]
        ),
        "more_pauses_increase_cognitive_load": (
            paused["output"]["cognitive_load"]
            > typical["output"]["cognitive_load"]
        ),
        "all_profiles_deterministic": all(
            row["deterministic"] for row in profile_results
        ),
        "all_outputs_valid": all(
            row["valid_outputs"] == REPEATS
            for row in profile_results
        ),
        "low_energy_produces_lower_emotion_score": (
            next(
                row for row in profile_results
                if row["profile"] == "low_energy_speech"
            )["output"]["emotion"]
            < typical["output"]["emotion"]
        ),
    }

    report = {
        "run_id": run_id,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "benchmark": "human_state_heuristic_behavioral",
        "repeats_per_profile": REPEATS,
        "python_version": sys.version,
        "platform": platform.platform(),
        "profile_count": len(PROFILES),
        "total_engine_runs": len(PROFILES) * REPEATS,
        "profiles": profile_results,
        "behavioral_checks": behavioral_checks,
        "interpretation": (
            "Synthetic behavioral and runtime evaluation only. "
            "Not real-world accuracy, clinical validity, or evidence "
            "of psychological-state detection performance."
        ),
    }

    json_path = RESULTS_DIR / f"human_state_{run_id}.json"
    csv_path = RESULTS_DIR / f"human_state_{run_id}.csv"

    json_path.write_text(
        json.dumps(report, indent=2, allow_nan=False),
        encoding="utf-8",
    )

    with csv_path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=[
                "run_id", "profile", "repeats", "valid_outputs",
                "deterministic", "mean_latency_ms", "median_latency_ms",
                "min_latency_ms", "max_latency_ms", "emotion_label",
                "emotion", "hesitation", "confidence", "engagement",
                "cognitive_load",
            ],
        )
        writer.writeheader()

        for row in profile_results:
            writer.writerow({
                "run_id": run_id,
                **{key: row[key] for key in (
                    "profile", "repeats", "valid_outputs",
                    "deterministic", "mean_latency_ms",
                    "median_latency_ms", "min_latency_ms",
                    "max_latency_ms",
                )},
                **row["output"],
            })

    print(json.dumps({
        "run_id": run_id,
        "json": str(json_path),
        "csv": str(csv_path),
        "total_engine_runs": report["total_engine_runs"],
        "behavioral_checks": behavioral_checks,
        "profiles": [
            {
                "profile": row["profile"],
                "mean_latency_ms": round(row["mean_latency_ms"], 3),
                "median_latency_ms": round(row["median_latency_ms"], 3),
                "deterministic": row["deterministic"],
                "output": row["output"],
            }
            for row in profile_results
        ],
    }, indent=2))

    # Fail loudly if core invariants or the selected behavioral checks fail.
    if not all(behavioral_checks.values()):
        raise SystemExit(
            "Benchmark completed, but one or more checks failed. "
            "Inspect the JSON report before drawing conclusions."
        )


if __name__ == "__main__":
    main()