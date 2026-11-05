
from pathlib import Path
import sys
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
from time import perf_counter
from datetime import datetime, timezone
from collections import Counter
import csv
import json
import uuid

from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
)

from ai.speech.vad.detector import VoiceActivityDetector
from ai.speech.feature_extraction.acoustic_features import AcousticFeatureExtractor
from ai.human_state.emotion.detector import EmotionDetector


AUDIO_DIR = Path("evaluation/datasets/crema-d/AudioWAV")
RESULTS_DIR = Path("evaluation/results")

# Canonical labels used for evaluation.
GT_LABELS = ["anger", "disgust", "fear", "happy", "neutral", "sad"]
SUPPORTED_LABELS = ["happy", "neutral", "sad"]

CREMA_LABELS = {
    "ANG": "anger",
    "DIS": "disgust",
    "FEA": "fear",
    "HAP": "happy",
    "NEU": "neutral",
    "SAD": "sad",
}

# Keep unsupported predictions visible rather than silently remapping them.
PRED_LABELS = GT_LABELS + ["excited", "error"]


def calculate_metrics(y_true, y_pred, labels):
    return {
        "accuracy": round(accuracy_score(y_true, y_pred), 6),
        "macro_f1": round(
            f1_score(
                y_true,
                y_pred,
                labels=labels,
                average="macro",
                zero_division=0,
            ),
            6,
        ),
        "per_class": classification_report(
            y_true,
            y_pred,
            labels=labels,
            output_dict=True,
            zero_division=0,
        ),
        "confusion_matrix": confusion_matrix(
            y_true,
            y_pred,
            labels=labels,
        ).tolist(),
        "class_order": labels,
    }


def main():
    if not AUDIO_DIR.exists():
        raise FileNotFoundError(f"Dataset directory not found: {AUDIO_DIR}")

    files = sorted(AUDIO_DIR.glob("*.wav"))
    if not files:
        raise RuntimeError(f"No WAV files found in {AUDIO_DIR}")

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    vad = VoiceActivityDetector()
    extractor = AcousticFeatureExtractor()
    detector = EmotionDetector()

    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_id += "_" + uuid.uuid4().hex[:8]

    records = []
    failures = []
    latencies = []

    print(f"Starting CREMA-D benchmark: {len(files)} recordings")
    print(f"Run ID: {run_id}")

    for index, path in enumerate(files, start=1):
        ground_truth_code = path.stem.split("_")[2]
        ground_truth = CREMA_LABELS.get(ground_truth_code)

        if ground_truth is None:
            print(f"Skipping unrecognized label: {path.name}")
            continue

        start = perf_counter()

        try:
            vad_result = vad.detect(str(path))
            features = extractor.extract(
                str(path),
                vad_result,
                transcript="",
            )

            prediction = detector.detect({
                "features": features,
                "vad": vad_result,
            })

            elapsed_ms = (perf_counter() - start) * 1000
            predicted_label = str(prediction["label"]).lower()

            if predicted_label not in PRED_LABELS:
                predicted_label = "error"

            score = float(prediction["score"])

            record = {
                "file": path.name,
                "ground_truth": ground_truth,
                "prediction": predicted_label,
                "score": score,
                "latency_ms": round(elapsed_ms, 3),
                "status": "success",
                "error": "",
            }

            latencies.append(elapsed_ms)

        except Exception as exc:
            elapsed_ms = (perf_counter() - start) * 1000

            record = {
                "file": path.name,
                "ground_truth": ground_truth,
                "prediction": "error",
                "score": None,
                "latency_ms": round(elapsed_ms, 3),
                "status": "failed",
                "error": repr(exc),
            }

            failures.append({
                "file": path.name,
                "error": repr(exc),
            })

        records.append(record)

        if index % 100 == 0 or index == len(files):
            print(f"Progress: {index}/{len(files)}")

    successful = [r for r in records if r["status"] == "success"]

    # Failures count as incorrect predictions in the overall evaluation.
    y_true = [r["ground_truth"] for r in records]
    y_pred = [r["prediction"] for r in records]

    full_metrics = calculate_metrics(
        y_true,
        y_pred,
        PRED_LABELS,
    )

    # Evaluate only the three labels supported by the detector.
    subset_records = [
        r for r in records
        if r["ground_truth"] in SUPPORTED_LABELS
    ]

    subset_true = [r["ground_truth"] for r in subset_records]
    subset_pred = [r["prediction"] for r in subset_records]

    subset_metrics = calculate_metrics(
        subset_true,
        subset_pred,
        SUPPORTED_LABELS,
    )

    # First recording is reported separately due to cold-start effects.
    steady_latencies = latencies[1:] if len(latencies) > 1 else []

    def latency_summary(values):
        if not values:
            return None

        ordered = sorted(values)
        n = len(ordered)

        return {
            "mean_ms": round(sum(ordered) / n, 3),
            "median_ms": round(ordered[n // 2], 3),
            "p95_ms": round(ordered[min(n - 1, int(0.95 * n))], 3),
            "min_ms": round(ordered[0], 3),
            "max_ms": round(ordered[-1], 3),
        }

    summary = {
        "run_id": run_id,
        "dataset": "CREMA-D",
        "total_recordings": len(records),
        "successful_recordings": len(successful),
        "failed_recordings": len(failures),
        "prediction_distribution": dict(
            Counter(r["prediction"] for r in records)
        ),
        "ground_truth_distribution": dict(
            Counter(r["ground_truth"] for r in records)
        ),
        "full_six_class_evaluation": full_metrics,
        "supported_three_class_evaluation": subset_metrics,
        "latency_all_successful_runs": latency_summary(latencies),
        "latency_excluding_first_successful_run": latency_summary(
            steady_latencies
        ),
        "cold_start_latency_ms": (
            round(latencies[0], 3) if latencies else None
        ),
        "limitations": [
            "CREMA-D contains acted emotional speech.",
            "The detector is a heuristic, not a trained six-class classifier.",
            "Excited is not mapped to happy.",
            "Unsupported ground-truth classes remain in the full evaluation.",
            "Results do not establish real-world conversational emotion accuracy.",
        ],
    }

    json_path = RESULTS_DIR / f"cremad_emotion_{run_id}.json"
    csv_path = RESULTS_DIR / f"cremad_emotion_{run_id}.csv"

    with json_path.open("w", encoding="utf-8") as f:
        json.dump(
            {"summary": summary, "records": records, "failures": failures},
            f,
            indent=2,
        )

    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "file",
                "ground_truth",
                "prediction",
                "score",
                "latency_ms",
                "status",
                "error",
            ],
        )
        writer.writeheader()
        writer.writerows(records)

    print("\n========== CREMA-D RESULTS ==========")
    print("Total:", len(records))
    print("Successful:", len(successful))
    print("Failed:", len(failures))

    print("\nFull six-class accuracy:",
          full_metrics["accuracy"])
    print("Full six-class macro-F1:",
          full_metrics["macro_f1"])

    print("\nSupported three-class accuracy:",
          subset_metrics["accuracy"])
    print("Supported three-class macro-F1:",
          subset_metrics["macro_f1"])

    print("\nPrediction distribution:",
          summary["prediction_distribution"])

    print("\nLatency excluding first successful run:",
          summary["latency_excluding_first_successful_run"])

    print("\nSaved:")
    print(json_path)
    print(csv_path)


if __name__ == "__main__":
    main()