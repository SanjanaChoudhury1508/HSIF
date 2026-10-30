# HSIF Evaluation

## Purpose

This directory contains reproducible benchmarks for speech processing,
human-state estimation, and dialogue-policy processing. Results are
saved as timestamped JSON and CSV files in `evaluation/results/`.

## Benchmarks

### Speech

Run:

```powershell
python evaluation\benchmark_speech.py
```

Measures speech transcription latency and compares recognized text against
a manually verified reference transcript using word error rate (WER) and
character error rate (CER).

The current reference uses one audio fixture repeated multiple times.
These measurements characterize that fixture and environment; they are
not a general estimate of speech-recognition accuracy.

### Human-state processing

Run:

```powershell
python evaluation\benchmark_human_state.py
```

Uses synthetic behavioral profiles to check deterministic behavior,
valid outputs, and expected relationships between selected input features
and heuristic scores.

These checks do not establish real-world accuracy or psychological or
clinical validity. Human-state estimates are heuristic signals.

### Dialogue processing

Run:

```powershell
python evaluation\benchmark_dialogue.py
```

Compares a fixed neutral-policy prompt-building baseline with the adaptive
dialogue pipeline using five synthetic profiles and repeated measurements.

The benchmark records local pipeline latency, prompt length, successful
outputs, and whether the adaptive policy matches the expected strategy.

The baseline is a controlled comparator, not a historical production
baseline. The benchmark does not measure LLM generation quality, human
ratings, or user outcomes.

## Reproducibility and interpretation

- Each run writes a timestamped JSON result and a CSV record file.
- Warm-up runs are excluded from the recorded measurements.
- Results depend on the local machine, Python environment, dependencies,
  and benchmark inputs.
- Synthetic profiles validate configured behavior, not real-world
  predictive accuracy.
- Very small local processing times should not be interpreted as end-to-end
  response latency.
- Compare runs only when their benchmark inputs and measurement methods
  are compatible.

## Running the test suite

```powershell
python -m pytest -q
```

The test suite validates software behavior. Its pass rate is not a model
accuracy metric.
