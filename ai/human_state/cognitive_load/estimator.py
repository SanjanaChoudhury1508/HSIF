"""
cognitive_load/estimator.py

Baseline cognitive load estimator.

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
      "max_pause_duration": 0.45,
      "mean_energy": 0.0789,
      "mean_pitch": 186.16,
      "min_pitch": 69.7,
      "max_pitch": 242.7
  },
  ...
}

Output: {"score": 0.42}   (0.0 = low cognitive load, 1.0 = high cognitive load)

This is a heuristic baseline, not a validated clinical/psychological
measurement. It's a rough SPEECH-DERIVED signal for "does this speech
show patterns associated with mental strain" (long pauses, frequent
pauses, slower/thinner speech, unstable energy) -- not a diagnosis of
someone's actual cognitive state.

Heuristic idea:
  - frequent pauses               -> higher load (searching for words)
  - long pauses (especially max)  -> higher load
  - low speech rate (low activity ratio) -> higher load
  - very flat OR very erratic pitch -> higher load
    (struggling speech often loses natural pitch variation, or
    becomes erratic under strain)
  - low/unstable energy           -> higher load
"""

from typing import Dict, Any


def _safe_get(d: Dict[str, Any], *keys, default=0.0):
    current = d
    for key in keys:
        if not isinstance(current, dict) or key not in current:
            return default
        current = current[key]
    return current if current is not None else default


def estimate_cognitive_load(speech_result: Dict[str, Any]) -> Dict[str, float]:
    duration = _safe_get(speech_result, "audio", "duration", default=0.0)

    # No usable audio info -> can't estimate; return neutral midpoint
    if duration <= 0:
        return {"score": 0.5}

    speech_duration = _safe_get(speech_result, "audio", "speech_duration", default=0.0)
    number_of_pauses = _safe_get(speech_result, "features", "number_of_pauses", default=0)
    average_pause_duration = _safe_get(speech_result, "features", "average_pause_duration", default=0.0)
    max_pause_duration = _safe_get(speech_result, "features", "max_pause_duration", default=0.0)
    mean_energy = _safe_get(speech_result, "features", "mean_energy", default=0.0)
    mean_pitch = _safe_get(speech_result, "features", "mean_pitch", default=0.0)
    min_pitch = _safe_get(speech_result, "features", "min_pitch", default=0.0)
    max_pitch = _safe_get(speech_result, "features", "max_pitch", default=0.0)

    # --- Pause frequency component ---
    pause_rate = number_of_pauses / duration
    pause_rate_score = min(pause_rate / 0.5, 1.0)

    # --- Pause length component (uses max pause, since one long stumble
    # is a stronger signal of strain than average alone) ---
    max_pause_score = min(max_pause_duration / (0.3 * duration), 1.0) if duration > 0 else 0.0

    # --- Low speech rate component (a lot of silence relative to duration) ---
    activity_ratio = speech_duration / duration if duration > 0 else 0.0
    low_activity_score = 1.0 - min(activity_ratio, 1.0)

    # --- Pitch instability component ---
    # Both very flat and very erratic pitch read as elevated load.
    pitch_range = max_pitch - min_pitch
    pitch_range_ratio = (pitch_range / mean_pitch) if mean_pitch > 0 else 0.0
    if pitch_range_ratio <= 0.2:
        pitch_score = 0.7  # flat/monotone -> moderately elevated load
    elif 0.2 < pitch_range_ratio <= 0.8:
        pitch_score = 0.2  # natural variation -> low load
    else:
        # erratic pitch -> load rises with how far past 0.8 it goes
        pitch_score = min(0.2 + (pitch_range_ratio - 0.8) * 0.5, 1.0)

    # --- Energy component (low energy -> higher load) ---
    energy_score = 1.0 - min(mean_energy / 0.15, 1.0)

    # Weighted combination -- starting baseline weights
    score = (
        0.25 * pause_rate_score +
        0.2 * max_pause_score +
        0.2 * low_activity_score +
        0.2 * pitch_score +
        0.15 * energy_score
    )

    score = max(0.0, min(1.0, score))

    return {"score": round(score, 3)}


if __name__ == "__main__":
    # Quick manual sanity check -- run with: python cognitive_load/estimator.py
    low_load_sample = {
        "audio": {"duration": 6.0, "speech_duration": 5.8, "silence_duration": 0.2},
        "features": {
            "number_of_pauses": 0,
            "average_pause_duration": 0.0,
            "max_pause_duration": 0.0,
            "mean_energy": 0.12,
            "mean_pitch": 180.0,
            "min_pitch": 140.0,
            "max_pitch": 230.0,
        },
    }
    print(estimate_cognitive_load(low_load_sample))

    high_load_sample = {
        "audio": {"duration": 8.0, "speech_duration": 4.0, "silence_duration": 4.0},
        "features": {
            "number_of_pauses": 5,
            "average_pause_duration": 0.8,
            "max_pause_duration": 2.0,
            "mean_energy": 0.02,
            "mean_pitch": 150.0,
            "min_pitch": 148.0,
            "max_pitch": 152.0,
        },
    }
    print(estimate_cognitive_load(high_load_sample))

    # Edge case: missing/empty speech_result
    print(estimate_cognitive_load({}))