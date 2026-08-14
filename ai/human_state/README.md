# Human State Engine

The Human State Engine converts the structured output of the speech-processing pipeline into a **Human State Representation (HSR)**.

The engine receives a `SpeechResult` from the speech-processing module and produces a single structured `HumanState` object containing estimates for:

* Emotion
* Hesitation
* Confidence
* Engagement
* Cognitive Load

The current implementation uses modular baseline and heuristic estimators. These implementations are designed so that more advanced machine-learning models can replace individual components later without changing the overall Human State Engine interface.

## Architecture

The current processing flow is:

```text
Audio
  |
  v
Speech Processing
  |
  v
SpeechResult
  |
  v
HumanStateEngine
  |
  +----> EmotionDetector
  |
  +----> HesitationDetector
  |
  +----> ConfidenceEstimator
  |
  +----> EngagementEstimator
  |
  +----> Cognitive Load Estimator
  |
  v
HumanState / HSR
  |
  v
Dialogue System
```

The main entry point is:

```python
from ai.human_state.human_state_engine import HumanStateEngine

engine = HumanStateEngine()
human_state = engine.process(speech_result)
```

For JSON-friendly output:

```python
result = engine.process_to_dict(speech_result)
```

## Input Format

The Human State Engine consumes the structured `SpeechResult` produced by the speech-processing module.

A representative input is:

```python
speech_result = {
    "transcript": "Hello, this is a test.",
    "language": "en",
    "language_probability": 0.657,

    "audio": {
        "duration": 6.037,
        "speech_duration": 5.52,
        "silence_duration": 0.517
    },

    "features": {
        "number_of_pauses": 1,
        "average_pause_duration": 0.45,
        "max_pause_duration": 0.45,
        "mean_energy": 0.0789,
        "mean_pitch": 186.16,
        "min_pitch": 69.7,
        "max_pitch": 242.7
    },

    "vad": {
        "speech_segments": [],
        "pauses": []
    }
}
```

The Human State Engine does not implement the speech-processing pipeline itself. It consumes the structured information produced by that pipeline.

## Human State Representation

The HSR is represented by the `HumanState` dataclass in `hsr.py`.

The structure is:

```python
{
    "emotion": {
        "label": "neutral",
        "score": 0.72
    },
    "hesitation": {
        "score": 0.31
    },
    "confidence": {
        "score": 0.68
    },
    "engagement": {
        "score": 0.75
    },
    "cognitive_load": {
        "score": 0.42
    }
}
```

All numerical scores are normalized to the range:

```text
0.0 - 1.0
```

For emotion:

* `label` represents the estimated emotional category.
* `score` represents the confidence of the baseline classification.

For the other components:

* `score` represents the estimated strength of the corresponding speech-derived signal.

These values are baseline estimates and should not be interpreted as scientifically validated psychological measurements.

## Components

### 1. Emotion

Implementation:

```text
ai/human_state/emotion/detector.py
```

Interface:

```python
EmotionDetector().detect(speech_result)
```

Output:

```python
{
    "label": "neutral",
    "score": 0.6
}
```

The current baseline uses speech features such as:

* Mean pitch
* Pitch range
* Mean energy

The current implementation provides a simple baseline classification. A trained speech-emotion model can replace this implementation later while preserving the `detect()` interface.

### 2. Hesitation

Implementation:

```text
ai/human_state/hesitation/detector.py
```

Interface:

```python
HesitationDetector().detect(speech_result)
```

Output:

```python
{
    "score": 0.227
}
```

The baseline uses:

* Number of pauses
* Average pause duration
* Maximum pause duration
* Silence duration
* Speech duration

The general heuristic is that more frequent and longer pauses increase the hesitation score.

### 3. Confidence

Implementation:

```text
ai/human_state/confidence/estimator.py
```

Interface:

```python
ConfidenceEstimator().estimate(speech_result)
```

Output:

```python
{
    "score": 0.671
}
```

The baseline considers:

* Pause frequency
* Pause duration
* Pitch variation
* Mean energy
* Speech duration

The resulting value is normalized to the range `0.0 - 1.0`.

This should be treated as a **speech-derived confidence estimate**, not a scientifically validated psychological measurement.

### 4. Engagement

Implementation:

```text
ai/human_state/engagement/estimator.py
```

Interface:

```python
EngagementEstimator().estimate(speech_result)
```

Output:

```python
{
    "score": 0.839
}
```

The baseline considers:

* Speech activity
* Speech duration
* Mean energy
* Pause patterns
* Pitch variation

Higher speech activity and stronger speech signals generally contribute to a higher engagement score.

### 5. Cognitive Load

Implementation:

```text
ai/human_state/cognitive_load/estimator.py
```

Interface:

```python
estimate_cognitive_load(speech_result)
```

Output:

```python
{
    "score": 0.274
}
```

The baseline considers:

* Pause frequency
* Maximum pause duration
* Speech activity ratio
* Pitch variation
* Mean energy

Longer or more frequent pauses, lower speech activity, and certain pitch/energy patterns contribute to a higher estimated cognitive-load score.

This is a speech-derived heuristic signal and is **not a diagnosis or clinical measurement**.

## HumanStateEngine

Implementation:

```text
ai/human_state/human_state_engine.py
```

The `HumanStateEngine` is responsible for coordinating all individual estimators.

Instead of the dialogue system calling every estimator independently:

```python
emotion = ...
hesitation = ...
confidence = ...
engagement = ...
cognitive_load = ...
```

the caller can use one interface:

```python
engine = HumanStateEngine()

human_state = engine.process(speech_result)
```

Or:

```python
human_state_dict = engine.process_to_dict(speech_result)
```

The engine also normalizes estimator outputs and safely handles missing optional sections of the `SpeechResult`.

## Input Validation and Edge Cases

The engine provides safe handling for incomplete inputs.

Examples include:

* Empty `SpeechResult`
* `None` input
* Missing `audio`
* Missing `features`
* Missing `vad`
* Missing feature values
* Zero-duration audio
* Very short audio
* Invalid input types

Scores are kept within the range:

```text
0.0 <= score <= 1.0
```

Invalid or unavailable score values use a neutral fallback where appropriate.

## Testing

Human State Engine tests are located at:

```text
tests/test_human_state.py
```

The test suite covers:

* Complete Human State generation
* Required HSR fields
* Emotion output
* Score normalization
* Hesitation behavior
* Engagement behavior
* Cognitive-load behavior
* Empty input
* `None` input
* Missing optional sections
* Zero-duration audio
* Very short audio
* Missing feature values
* Invalid input types
* JSON-friendly output
* Consistency between `process()` and `process_to_dict()`

Run the tests from the project root:

```powershell
python -m pytest tests\test_human_state.py -v
```

The current Human State Engine test suite contains 19 tests.

## Current Baseline Approach

The first milestone uses modular heuristic/baseline implementations rather than complex trained ML models.

This allows the complete pipeline to be implemented and tested first:

```text
SpeechResult
    |
    v
HumanStateEngine
    |
    v
HumanState
```

Each estimator can later be replaced independently.

For example:

```text
Current:
SpeechResult -> Heuristic Emotion Detector

Future:
SpeechResult -> Trained Emotion Model
```

The Human State Engine interface does not need to change as long as the replacement component maintains the expected input/output contract.

## Limitations

The current implementation has several important limitations.

### Baseline heuristics

The estimators use manually designed rules and weights rather than models trained on a validated dataset.

### Speech-derived signals

The estimates are derived from speech characteristics and should not be interpreted as definitive measurements of a person's internal psychological state.

### Emotion accuracy

The current emotion implementation is a baseline and should eventually be replaced or improved using a suitable trained speech-emotion model.

### Context sensitivity

Speech characteristics can vary naturally between speakers, languages, environments, microphones, and speaking styles.

### No clinical interpretation

The Human State Engine is not intended for medical diagnosis, psychological diagnosis, or clinical decision-making.

## Future Improvements

Possible improvements include:

1. Replace heuristic emotion detection with a trained speech-emotion model.
2. Train hesitation detection using annotated speech data.
3. Improve confidence estimation using speaker-normalized acoustic features.
4. Improve engagement estimation using temporal speech patterns.
5. Develop a trained cognitive-load estimator.
6. Add temporal smoothing across consecutive speech segments.
7. Add speaker-specific normalization.
8. Add confidence/calibration analysis for model outputs.
9. Evaluate estimators against labeled datasets.
10. Replace individual heuristic components without changing the HSR interface.

## Directory Structure

The Human State Engine module currently follows this structure:

```text
ai/
└── human_state/
    ├── __init__.py
    ├── README.md
    ├── hsr.py
    ├── human_state_engine.py
    │
    ├── emotion/
    │   ├── __init__.py
    │   └── detector.py
    │
    ├── hesitation/
    │   ├── __init__.py
    │   └── detector.py
    │
    ├── confidence/
    │   ├── __init__.py
    │   └── estimator.py
    │
    ├── engagement/
    │   ├── __init__.py
    │   └── estimator.py
    │
    └── cognitive_load/
        ├── __init__.py
        └── estimator.py
```

Tests:

```text
tests/
└── test_human_state.py
```

## Integration Contract

The main integration contract is:

```text
SpeechResult
    |
    v
HumanStateEngine.process()
    |
    v
HumanState
```

The resulting `HumanState` provides a stable structure for the downstream dialogue system.

This separation allows the speech-processing, human-state, dialogue, and backend modules to evolve independently while maintaining clear interfaces.
