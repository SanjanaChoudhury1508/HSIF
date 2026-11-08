
import csv
import json
import random
import sys
from pathlib import Path
from datetime import datetime, timezone

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from evaluation.benchmark_gemini_responses import (
    SCENARIOS,
    GeminiProvider,
    GeminiQuotaExceededError,
    build_baseline_prompt,
    build_adaptive_prompt,
    generate_response,
)

RUN_ID = "20261105T180011Z_5ec43391"
RESULTS_DIR = PROJECT_ROOT / "evaluation" / "results"

JSON_PATH = RESULTS_DIR / f"gemini_response_{RUN_ID}.json"
CSV_PATH = RESULTS_DIR / f"gemini_response_{RUN_ID}.csv"
REVIEW_PATH = RESULTS_DIR / f"gemini_blind_review_{RUN_ID}.csv"

CSV_FIELDS = [
    "scenario_id", "variant", "policy_strategy",
    "success", "latency_ms", "prompt", "response", "error"
]


def save_results(payload):
    payload["updated_at_utc"] = datetime.now(timezone.utc).isoformat()

    JSON_PATH.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )

    with CSV_PATH.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(payload["completed_records"])


def update_review(records):
    # Preserve existing ratings and completed A/B comparisons.
    existing_rows = []
    if REVIEW_PATH.exists():
        with REVIEW_PATH.open("r", newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            fields = reader.fieldnames
            existing_rows = list(reader)
    else:
        raise FileNotFoundError("Existing blind-review CSV not found.")

    reviewed_ids = {row["scenario_id"] for row in existing_rows}
    rng = random.Random(42)

    for scenario in SCENARIOS:
        sid = scenario["id"]

        if sid in reviewed_ids:
            continue

        baseline = next(
            (r for r in records
             if r["scenario_id"] == sid
             and r["variant"] == "baseline"
             and r["success"]),
            None
        )
        adaptive = next(
            (r for r in records
             if r["scenario_id"] == sid
             and r["variant"] == "adaptive"
             and r["success"]),
            None
        )

        if not baseline or not adaptive:
            continue

        variants = [
            ("baseline", baseline["response"]),
            ("adaptive", adaptive["response"])
        ]
        rng.shuffle(variants)

        existing_rows.append({
            "scenario_id": sid,
            "response_A": variants[0][1],
            "response_B": variants[1][1],
            **{field: "" for field in fields
               if field not in ("scenario_id", "response_A", "response_B")}
        })

    with REVIEW_PATH.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(existing_rows)


def main():
    if not JSON_PATH.exists():
        raise FileNotFoundError(JSON_PATH)

    payload = json.loads(JSON_PATH.read_text(encoding="utf-8"))
    records = payload["completed_records"]

    provider = GeminiProvider()

    if payload["model"] != provider.model:
        raise RuntimeError(
            f"Model mismatch: saved={payload['model']}, "
            f"current={provider.model}"
        )

    print(f"Resuming run: {RUN_ID}")
    print(f"Model: {provider.model}")

    quota_exceeded = False

    for scenario in SCENARIOS:
        sid = scenario["id"]

        for variant in ("baseline", "adaptive"):
            previous = next(
                (r for r in records
                 if r["scenario_id"] == sid
                 and r["variant"] == variant),
                None
            )

            if previous and previous["success"]:
                print(f"SKIP {sid}/{variant}: already successful")
                continue

            if variant == "baseline":
                prompt = build_baseline_prompt(scenario["message"])
                strategy = None
            else:
                prompt, policy = build_adaptive_prompt(
                    scenario["message"], scenario["state"]
                )
                strategy = policy["strategy"]

            print(f"RUN {sid}/{variant}")

            result = generate_response(provider, prompt)

            record = {
                "scenario_id": sid,
                "variant": variant,
                "policy_strategy": strategy,
                "success": result["success"],
                "latency_ms": result["latency_ms"],
                "prompt": prompt,
                "response": result["response"],
                "error": result["error"],
            }

            if previous:
                records[records.index(previous)] = record
            else:
                records.append(record)

            save_results(payload)

            print(
                f"  Success: {result['success']} | "
                f"Latency: {result['latency_ms']} ms"
            )

            if not result["success"]:
                print(f"  Error: {result['error']}")

                if "GeminiQuotaExceededError" in (result["error"] or ""):
                    quota_exceeded = True
                    break

        if quota_exceeded:
            print("Quota exhausted. Progress saved; stopping.")
            break

    update_review(records)
    save_results(payload)

    successful = sum(r["success"] for r in records)
    print("\nResume summary")
    print(f"Successful records: {successful}")
    print(f"Total records: {len(records)}")
    print(f"Quota stopped: {quota_exceeded}")
    print(f"Results: {JSON_PATH}")
    print(f"Review: {REVIEW_PATH}")


if __name__ == "__main__":
    main()