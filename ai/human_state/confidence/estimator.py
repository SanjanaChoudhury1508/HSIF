"""
confidence/estimator.py

Baseline confidence estimator.

Input: a SpeechResult dict from Eesha's SpeechService, e.g.

{
  "audio": {
      "duration": 6.037,
      "speech_duration": 5.52,
      "silence_duration": 0.517
  },
  "features": {
      "number_of_pauses": 1,
      "average_pause_duration": 0.45,
      "mean_energy": 0.0789,
      "mean_pitch": 186.16,
      "min_pitch": 69.7,
      "max_pitch": 242.7
  },
  ...
}

Output: {"score": 0.68}   (0.0 = low confidence, 1.0 = high confidence)

This is a heuristic baseline treating this as a SPEECH-DERIVED signal,
not a scientifically validated psychological measurement of actual
confidence. It should be read as "how confident does this speech
SOUND", not a claim about the speaker's inner state.

Heuristic idea:
  - fewer / shorter pauses            -> more confident
  - stronger (higher) energy          -> more confident
  - moderate, stable pitch variation  -> more confident
    (extremely flat OR extremely erratic pitch both read as less
    confident; a little natural variation is normal/expected)
"""

from typing import Dict, Any


def _safe_get(d: Dict[str, Any], *keys, default=0.0):
    current = d
    for key in keys:
        if not isinstance(current, dict) or key not in current:
            return default
        current = current[key]
    return current if current is not None else default


def estimate_confidence(speech_result: Dict[str, Any]) -> Dict[str, float]:
    duration = _safe_get(speech_result, "audio", "duration", default=0.0)

    # No usable audio info -> can't estimate; return neutral midpoint
    if duration <= 0:
        return {"score": 0.5}

    number_of_pauses = _safe_get(speech_result, "features", "number_of_pauses", default=0)
    average_pause_duration = _safe_get(speech_result, "features", "average_pause_duration", default=0.0)
    mean_energy = _safe_get(speech_result, "features", "mean_energy", default=0.0)
    mean_pitch = _safe_get(speech_result, "features", "mean_pitch", default=0.0)
    min_pitch = _safe_get(speech_result, "features", "min_pitch", default=0.0)
    max_pitch = _safe_get(speech_result, "features", "max_pitch", default=0.0)

    # --- Pause component (fewer/shorter pauses -> higher confidence) ---
    pause_rate = number_of_pauses / duration
    pause_penalty = min(pause_rate / 0.5, 1.0)  # same normalization as hesitation
    avg_pause_penalty = min(average_pause_duration / (0.2 * duration), 1.0) if duration > 0 else 0.0
    pause_score = 1.0 - (0.5 * pause_penalty + 0.5 * avg_pause_penalty)

    # --- Energy component (assume typical speech energy caps around 0.15) ---
    # mean_energy is a small positive float in Eesha's output (e.g. 0.0789)
    energy_score = min(mean_energy / 0.15, 1.0)

    # --- Pitch stability component ---
    # A moderate pitch range relative to mean pitch reads as natural/confident.
    # Very low range (monotone/flat) or very high range (erratic) both score lower.
    pitch_range = max_pitch - min_pitch
    if mean_pitch > 0:
        pitch_range_ratio = pitch_range / mean_pitch
    else:
        pitch_range_ratio = 0.0

    # Ideal ratio assumed around 0.5-1.0; score peaks there and falls off outside it.
    if pitch_range_ratio <= 0.0:
        pitch_score = 0.3  # flat/monotone speech, penalized a bit
    elif 0.5 <= pitch_range_ratio <= 1.0:
        pitch_score = 1.0
    elif pitch_range_ratio < 0.5:
        pitch_score = 0.3 + (pitch_range_ratio / 0.5) * 0.7
    else:
        # erratic pitch beyond 1.0 ratio -> decreasing score, floor at 0.2
        pitch_score = max(0.2, 1.0 - (pitch_range_ratio - 1.0) * 0.5)

    # Weighted combination -- starting baseline weights
    score = (
        0.4 * pause_score +
        0.3 * energy_score +
        0.3 * pitch_score
    )

    score = max(0.0, min(1.0, score))

    return {"score": round(score, 3)}


if __name__ == "__main__":
    # Quick manual sanity check -- run with: python confidence/estimator.py
    confident_sample = {
        "audio": {"duration": 6.0, "speech_duration": 5.8, "silence_duration": 0.2},
        "features": {
            "number_of_pauses": 0,
            "average_pause_duration": 0.0,
            "mean_energy": 0.12,
            "mean_pitch": 180.0,
            "min_pitch": 140.0,
            "max_pitch": 230.0,
        },
    }
    print(detect := estimate_confidence(confident_sample))

    hesitant_sample = {
        "audio": {"duration": 6.0, "speech_duration": 4.0, "silence_duration": 2.0},
        "features": {
            "number_of_pauses": 4,
            "average_pause_duration": 0.9,
            "mean_energy": 0.03,
            "mean_pitch": 150.0,
            "min_pitch": 145.0,
            "max_pitch": 155.0,
        },
    }
    print(estimate_confidence(hesitant_sample))

    # Edge case: missing/empty speech_result
    print(estimate_confidence({}))