
import csv
import json
import platform
import statistics
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from jiwer import wer, cer
from ai.speech.whisper.transcriber import SpeechTranscriber


AUDIO = ROOT / "tests" / "audio" / "processed.wav"
REFERENCES = ROOT / "evaluation" / "datasets" / "speech_references.json"
RESULTS = ROOT / "evaluation" / "results"
REPEATS = 5
MODEL_SIZE = "base"


def percentile(values, fraction):
    if not values:
        return None
    ordered = sorted(values)
    index = max(
        0,
        min(len(ordered) - 1, round(fraction * (len(ordered) - 1))),
    )
    return round(ordered[index], 4)


def load_reference():
    if not REFERENCES.exists():
        raise FileNotFoundError(
            f"Reference transcript file not found: {REFERENCES}"
        )

    data = json.loads(REFERENCES.read_text(encoding="utf-8"))
    entry = data.get(AUDIO.name)

    if not isinstance(entry, dict):
        raise ValueError(
            f"No reference entry found for {AUDIO.name!r} in {REFERENCES}"
        )

    reference = entry.get("reference_transcript")
    if not isinstance(reference, str) or not reference.strip():
        raise ValueError("Reference transcript must be a non-empty string.")

    if "REPLACE WITH VERIFIED SPOKEN WORDS" in reference:
        raise ValueError("Replace the reference transcript placeholder first.")

    return reference.strip(), entry


def main():
    if not AUDIO.exists():
        raise FileNotFoundError(f"Audio fixture not found: {AUDIO}")

    reference, reference_metadata = load_reference()

    RESULTS.mkdir(parents=True, exist_ok=True)
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_id += "_" + uuid.uuid4().hex[:8]

    print(f"Run ID: {run_id}")
    print(f"Audio: {AUDIO}")
    print(f"Reference transcript: {reference!r}")
    print(f"Verification method: {reference_metadata.get('verification_method', 'unspecified')}")
    print(f"Model: faster-whisper / {MODEL_SIZE} / CPU / int8")
    print("Loading model...")

    transcriber = SpeechTranscriber(model_size=MODEL_SIZE)

    print("Warm-up run (excluded from measured results)...")
    warmup_start = time.perf_counter()
    warmup = transcriber.transcribe(str(AUDIO))
    warmup_seconds = time.perf_counter() - warmup_start
    print(f"Warm-up: {warmup_seconds:.3f}s")
    print(f"Warm-up transcript: {warmup['text']!r}")

    records = []

    for index in range(1, REPEATS + 1):
        started = time.perf_counter()

        try:
            output = transcriber.transcribe(str(AUDIO))
            elapsed = time.perf_counter() - started
            predicted = output["text"]

            record = {
                "run_id": run_id,
                "example_id": AUDIO.name,
                "repeat": index,
                "success": True,
                "latency_seconds": round(elapsed, 4),
                "reference_transcript": reference,
                "transcript": predicted,
                "wer": round(wer(reference, predicted), 4),
                "cer": round(cer(reference, predicted), 4),
                "language": output["language"],
                "language_probability": output["language_probability"],
                "error": None,
            }

            print(
                f"[{index}/{REPEATS}] OK | {elapsed:.3f}s | "
                f"WER={record['wer']:.4f} | CER={record['cer']:.4f} | "
                f"language={output['language']}"
            )

        except Exception as exc:
            elapsed = time.perf_counter() - started
            record = {
                "run_id": run_id,
                "example_id": AUDIO.name,
                "repeat": index,
                "success": False,
                "latency_seconds": round(elapsed, 4),
                "reference_transcript": reference,
                "transcript": None,
                "wer": None,
                "cer": None,
                "language": None,
                "language_probability": None,
                "error": f"{type(exc).__name__}: {exc}",
            }
            print(f"[{index}/{REPEATS}] FAILED | {record['error']}")

        records.append(record)

    successful = [row for row in records if row["success"]]
    latencies = [row["latency_seconds"] for row in successful]
    wer_values = [row["wer"] for row in successful]
    cer_values = [row["cer"] for row in successful]
    successes = len(successful)

    summary = {
        "run_id": run_id,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "component": "SpeechTranscriber.transcribe",
        "model": "faster-whisper",
        "model_size": MODEL_SIZE,
        "device": "cpu",
        "compute_type": "int8",
        "audio_file": str(AUDIO.relative_to(ROOT)),
        "audio_bytes": AUDIO.stat().st_size,
        "reference_file": str(REFERENCES.relative_to(ROOT)),
        "reference_transcript": reference,
        "reference_verification_method": reference_metadata.get(
            "verification_method", "unspecified"
        ),
        "warmup_seconds": round(warmup_seconds, 4),
        "warmup_excluded_from_statistics": True,
        "repeats": REPEATS,
        "successes": successes,
        "failures": REPEATS - successes,
        "success_rate": round(successes / REPEATS, 4),
        "mean_latency_seconds": (
            round(statistics.mean(latencies), 4) if latencies else None
        ),
        "median_latency_seconds": (
            round(statistics.median(latencies), 4) if latencies else None
        ),
        "p95_latency_seconds": percentile(latencies, 0.95),
        "min_latency_seconds": round(min(latencies), 4) if latencies else None,
        "max_latency_seconds": round(max(latencies), 4) if latencies else None,
        "accuracy_metrics": {
            "mean_wer": round(statistics.mean(wer_values), 4) if wer_values else None,
            "mean_cer": round(statistics.mean(cer_values), 4) if cer_values else None,
            "successful_transcriptions_scored": successes,
            "note": (
                "WER/CER are measured against the configured reference transcript. "
                "Results describe this fixture only, not general model accuracy."
            ),
        },
        "results": records,
    }

    json_path = RESULTS / f"speech_{run_id}.json"
    csv_path = RESULTS / f"speech_{run_id}.csv"

    json_path.write_text(
        json.dumps(summary, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    fieldnames = list(records[0].keys())
    with csv_path.open("w", newline="", encoding="utf-8-sig") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(records)

    print("\n=== Speech Benchmark Summary ===")
    print(f"Successful runs: {successes}/{REPEATS}")
    print(f"Success rate: {summary['success_rate']:.1%}")
    print(f"Mean latency: {summary['mean_latency_seconds']} s")
    print(f"Median latency: {summary['median_latency_seconds']} s")
    print(f"P95 latency: {summary['p95_latency_seconds']} s")
    print(f"Mean WER: {summary['accuracy_metrics']['mean_wer']}")
    print(f"Mean CER: {summary['accuracy_metrics']['mean_cer']}")
    print(f"\nJSON: {json_path.relative_to(ROOT)}")
    print(f"CSV:  {csv_path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()