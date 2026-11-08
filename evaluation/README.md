# HSIF Phase 6 – Evaluation Report

## 1. Purpose

Phase 6 evaluates the speech-processing, human-state estimation, emotion detection, and adaptive dialogue components of HSIF.

The evaluation combines reference-based measurements, synthetic behavioral tests, and a baseline-versus-adaptive Gemini response comparison.

Results are stored as timestamped JSON and CSV files in `evaluation/results/`.

## 2. Evaluation Results

### 2.1 Speech Processing – Thapaswini

**Method:** Faster-Whisper base model, CPU/int8, evaluated over five repeated runs using one manually verified audio reference.

| Metric | Result |
|---|---:|
| Successful runs | 5/5 |
| Mean latency | 1.8391 s |
| Median latency | 1.8409 s |
| P95 latency | 2.2088 s |
| Mean WER | 0.125 |
| Mean CER | 0.0392 |

The transcription consistently included one additional word ("a") compared with the reference.

**Limitation:** Only one audio fixture was evaluated. These results characterize the tested sample and environment, not general speech-recognition accuracy.

### 2.2 Human-State Estimation – Krupa

**Method:** CREMA-D acted-speech dataset containing 7,442 recordings across six emotion categories.

The HSIF emotion detector is a heuristic system supporting four output labels: neutral, excited, sad, and happy.

| Metric | Result |
|---|---:|
| Recordings processed | 7,442 |
| Successful recordings | 7,442 |
| Six-class accuracy | 21.61% |
| Six-class macro-F1 | 0.1169 |
| Supported three-class accuracy | 44.31% |
| Supported three-class macro-F1 | 0.4395 |
| Mean latency (excluding first run) | 214.45 ms |
| Median latency | 196.01 ms |
| P95 latency | 349.67 ms |

The supported three-class evaluation considers happy, neutral, and sad reference labels. Unsupported reference categories are retained in the full six-class evaluation and are not silently removed from the original dataset.

**Limitation:** CREMA-D contains acted emotional speech. The detector is heuristic rather than trained, and these results do not establish real-world emotion recognition or psychological validity.

### 2.3 Synthetic Human-State Tests – Sanjana

**Method:** Four synthetic behavioral profiles, each tested five times.

| Metric | Result |
|---|---:|
| Total runs | 20 |
| Successful checks | 20/20 |
| Behavioral checks passed | 5/5 |

Checks covered:
- Increased pauses producing higher hesitation estimates.
- Increased pauses producing higher cognitive-load estimates.
- Deterministic outputs.
- Valid output structure and score ranges.
- Lower energy producing a lower emotion score than the typical profile.

**Limitation:** These tests verify configured heuristic behavior, not accuracy against labelled human-state data or clinical validity.

### 2.4 Dialogue Processing – Sanjana

**Method:** Five synthetic profiles, 30 repetitions, comparing a fixed neutral-policy baseline with adaptive dialogue processing.

| Metric | Result |
|---|---:|
| Total records | 300 |
| Successful baseline records | 150/150 |
| Successful adaptive records | 150/150 |
| Adaptive expected strategy matches | 150/150 |

The benchmark measured local processing latency and prompt characteristics. It did not measure actual LLM generation quality.

**Limitation:** The baseline is a controlled neutral-policy comparator, not a historical production baseline. Synthetic profiles do not establish improved user outcomes.

### 2.5 Gemini Response Quality – Jennie

**Method:** Five scenarios comparing generic baseline prompts with HSIF-adaptive prompts using the same Gemini model.

The five scenarios were confusion, frustration, cognitive overload, low engagement, and normal interaction. Ten final successful API calls were evaluated.

**Response ratings (single evaluator, 1–5 scale):**

| Metric | Adaptive | Baseline |
|---|---:|---:|
| Overall average rating | 4.44 | 3.76 |
| Relevance | 4.60 | 4.80 |
| Clarity | 5.00 | 3.80 |
| Empathy | 4.40 | 2.80 |
| Adaptation | 4.40 | 2.60 |
| Helpfulness | 4.20 | 4.40 |

Adaptive responses were preferred in four of five scenarios. Baseline was preferred in the normal-interaction scenario.

**API latency:**

| Metric | Adaptive | Baseline |
|---|---:|---:|
| Mean latency | 10.18 s | 16.28 s |
| Median latency | 8.32 s | 16.23 s |
| Successful calls | 5/5 | 5/5 |

Adaptive responses had lower observed mean latency in this run. This should not be interpreted as evidence that adaptive prompting inherently reduces Gemini latency, since API response times vary.

**Limitation:** Ratings were produced by a single evaluator with assistant-assisted scoring, not an independent human-rating study. Only five scenarios were evaluated. API availability and latency are subject to external service conditions.

## 3. Reproduction Commands

Run from the repository root with the project virtual environment activated.

```powershell
python evaluation\benchmark_speech.py
python evaluation\benchmark_human_state.py
python evaluation\benchmark_dialogue.py
python evaluation\benchmark_cremad_emotion.py
python evaluation\benchmark_gemini_responses.py
```

The CREMA-D benchmark requires the dataset to be downloaded and extracted locally under `evaluation/datasets/crema-d/AudioWAV/`.

The Gemini benchmark requires a valid `GEMINI_API_KEY` and available API quota. It makes external API requests.

The original Gemini run and its resumed results are preserved in the recorded result files; rerunning the script creates a new benchmark run.

## 4. Result Artifacts

Each benchmark produces timestamped JSON and CSV outputs under `evaluation/results/`.

Important recorded runs:

- CREMA-D: `20261105T171105Z_1a23bbc0`
- Gemini: `20261105T180011Z_5ec43391`
- Speech: `20261030T052436Z_3e8ed483`
- Human-state: `20261030T162245Z_2e5fd208`
- Dialogue: `20261030T163347Z_ba01ff17`

## 5. Overall Interpretation and Limitations

The evaluation demonstrates that HSIF's current components can be executed and measured reproducibly under the tested conditions.

The results indicate:
- Speech transcription quality and latency were measured against a manually verified reference.
- Emotion detection was evaluated against an acted-speech dataset, with a substantial limitation in supported output categories.
- Human-state heuristics passed their configured synthetic behavioral checks.
- Adaptive dialogue policy processing matched expected strategies for the synthetic profiles.
- Adaptive Gemini responses received higher average single-evaluator ratings across the five tested scenarios.

These findings should not be interpreted as proof of clinical validity, general emotion-recognition accuracy, or improved real-world user outcomes.

Dataset size, synthetic inputs, limited audio references, single-evaluator ratings, and external API variability constrain the conclusions.

## 6. Test Suite

Run:

```powershell
python -m pytest -q
```

The test suite validates software behavior. Its pass rate is not a model accuracy metric.