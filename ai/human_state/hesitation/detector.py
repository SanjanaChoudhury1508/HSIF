"""
hesitation/detector.py

Baseline hesitation estimator.

Input: a SpeechResult dict from Eesha's SpeechService, e.g.

{
  "transcript": "Hello, this is a test.",
  "audio": {
      "duration": 6.037,
      "speech_duration": 5.52,
      "silence_duration": 0.517
  },
  "features": {
      "number_of_pauses": 1,
      "average_pause_duration": 0.45,
      "max_pause_duration": 0.45,
      ...
  },
  ...
}

Output: {"score": 0.31}   (0.0 = no hesitation, 1.0 = maximum hesitation)

This is a heuristic baseline, not a trained model. The idea:
more pauses, longer pauses, and more silence relative to total
duration --> higher hesitation score.

This can be swapped out later for a proper model as long as it
keeps the same input/output shape.
"""

from typing import Dict, Any


def _safe_get(d: Dict[str, Any], *keys, default=0.0):
    """Walk nested dict keys safely, returning default if missing."""
    current = d
    for key in keys:
        if not isinstance(current, dict) or key not in current:
            return default
        current = current[key]
    return current if current is not None else default


def detect_hesitation(speech_result: Dict[str, Any]) -> Dict[str, float]:
    """
    Compute a hesitation score in [0.0, 1.0] from speech features.

    Heuristic components:
      - pause_rate: number_of_pauses relative to total duration
      - avg_pause_weight: how long pauses tend to be, relative to duration
      - silence_ratio: silence_duration / total duration

    These are combined with simple fixed weights. Weights and the
    normalization caps are rough starting points, not tuned values.
    """
    duration = _safe_get(speech_result, "audio", "duration", default=0.0)

    # Edge case: no audio duration info at all -> can't estimate, return 0
    if duration <= 0:
        return {"score": 0.0}

    number_of_pauses = _safe_get(speech_result, "features", "number_of_pauses", default=0)
    average_pause_duration = _safe_get(speech_result, "features", "average_pause_duration", default=0.0)
    silence_duration = _safe_get(speech_result, "audio", "silence_duration", default=0.0)

    # Pauses per second of audio, capped and normalized to 0-1.
    # Assume more than ~1 pause every 2 seconds is "maximum" hesitation for this signal.
    pause_rate = number_of_pauses / duration
    pause_rate_score = min(pause_rate / 0.5, 1.0)

    # Average pause duration relative to total duration, capped at 1.0.
    # A single average pause taking up >20% of duration is treated as high.
    avg_pause_score = min(average_pause_duration / (0.2 * duration), 1.0) if duration > 0 else 0.0

    # Fraction of the clip that is silence.
    silence_ratio = min(silence_duration / duration, 1.0)

    # Weighted combination -- these weights are a starting baseline.
    score = (
        0.4 * pause_rate_score +
        0.3 * avg_pause_score +
        0.3 * silence_ratio
    )

    # Clamp to [0, 1] just in case
    score = max(0.0, min(1.0, score))

    return {"score": round(score, 3)}


if __name__ == "__main__":
    # Quick manual sanity check -- run with: python hesitation/detector.py
    sample_speech_result = {
        "transcript": "Hello, this is a test.",
        "audio": {
            "duration": 6.037,
            "speech_duration": 5.52,
            "silence_duration": 0.517,
        },
        "features": {
            "number_of_pauses": 1,
            "average_pause_duration": 0.45,
            "max_pause_duration": 0.45,
        },
    }
    print(detect_hesitation(sample_speech_result))

    # Edge case: no pauses at all
    no_pause_result = {
        "audio": {"duration": 5.0, "speech_duration": 5.0, "silence_duration": 0.0},
        "features": {"number_of_pauses": 0, "average_pause_duration": 0.0, "max_pause_duration": 0.0},
    }
    print(detect_hesitation(no_pause_result))

    # Edge case: missing/empty speech_result
    print(detect_hesitation({}))