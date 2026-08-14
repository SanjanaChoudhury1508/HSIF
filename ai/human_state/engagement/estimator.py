"""
engagement/estimator.py

Baseline engagement estimator.

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
      "mean_energy": 0.0789,
      "mean_pitch": 186.16,
      "min_pitch": 69.7,
      "max_pitch": 242.7
  },
  ...
}

Output: {"score": 0.75}   (0.0 = disengaged, 1.0 = highly engaged)

This is a heuristic baseline, not a trained model. Engagement here
means "how actively is this person participating in the conversation
right now" -- distinct from confidence (how self-assured they sound)
and hesitation (how much they falter).

Heuristic idea:
  - higher speech-to-total-duration ratio -> more engaged
    (they're talking, not sitting in silence)
  - stronger energy                        -> more engaged
  - some pitch variation (not flat/monotone) -> more engaged
  - fewer/shorter pauses                   -> more engaged
    (though this overlaps with hesitation, pause patterns also
    reflect whether someone is actively responding or checked out)
"""

from typing import Dict, Any


def _safe_get(d: Dict[str, Any], *keys, default=0.0):
    current = d
    for key in keys:
        if not isinstance(current, dict) or key not in current:
            return default
        current = current[key]
    return current if current is not None else default


def estimate_engagement(speech_result: Dict[str, Any]) -> Dict[str, float]:
    duration = _safe_get(speech_result, "audio", "duration", default=0.0)

    # No usable audio info -> can't estimate; return neutral midpoint
    if duration <= 0:
        return {"score": 0.5}

    speech_duration = _safe_get(speech_result, "audio", "speech_duration", default=0.0)
    mean_energy = _safe_get(speech_result, "features", "mean_energy", default=0.0)
    mean_pitch = _safe_get(speech_result, "features", "mean_pitch", default=0.0)
    min_pitch = _safe_get(speech_result, "features", "min_pitch", default=0.0)
    max_pitch = _safe_get(speech_result, "features", "max_pitch", default=0.0)
    number_of_pauses = _safe_get(speech_result, "features", "number_of_pauses", default=0)
    average_pause_duration = _safe_get(speech_result, "features", "average_pause_duration", default=0.0)

    # --- Speech activity ratio: how much of the clip is actual speech ---
    activity_ratio = min(speech_duration / duration, 1.0)

    # --- Energy component (same normalization as confidence) ---
    energy_score = min(mean_energy / 0.15, 1.0)

    # --- Pitch variation component ---
    # Unlike confidence, here we simply reward SOME variation over none.
    # Flat/monotone pitch -> low engagement. More variation -> more engaged,
    # capped so extreme variation doesn't dominate the score.
    pitch_range = max_pitch - min_pitch
    if mean_pitch > 0:
        pitch_range_ratio = pitch_range / mean_pitch
    else:
        pitch_range_ratio = 0.0
    pitch_score = min(pitch_range_ratio / 0.8, 1.0)

    # --- Pause component (fewer/shorter pauses -> more engaged) ---
    pause_rate = number_of_pauses / duration
    pause_penalty = min(pause_rate / 0.5, 1.0)
    avg_pause_penalty = min(average_pause_duration / (0.2 * duration), 1.0) if duration > 0 else 0.0
    pause_score = 1.0 - (0.5 * pause_penalty + 0.5 * avg_pause_penalty)

    # Weighted combination -- starting baseline weights
    score = (
        0.4 * activity_ratio +
        0.25 * energy_score +
        0.15 * pitch_score +
        0.2 * pause_score
    )

    score = max(0.0, min(1.0, score))

    return {"score": round(score, 3)}


if __name__ == "__main__":
    # Quick manual sanity check -- run with: python engagement/estimator.py
    engaged_sample = {
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
    print(estimate_engagement(engaged_sample))

    disengaged_sample = {
        "audio": {"duration": 6.0, "speech_duration": 2.0, "silence_duration": 4.0},
        "features": {
            "number_of_pauses": 3,
            "average_pause_duration": 1.0,
            "mean_energy": 0.02,
            "mean_pitch": 150.0,
            "min_pitch": 148.0,
            "max_pitch": 152.0,
        },
    }
    print(estimate_engagement(disengaged_sample))

    # Edge case: missing/empty speech_result
    print(estimate_engagement({}))