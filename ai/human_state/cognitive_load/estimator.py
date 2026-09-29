"""
Baseline cognitive load estimator.

This is a heuristic speech-derived signal, not a validated
clinical or psychological measurement.

Higher scores indicate speech patterns associated with
potential mental strain, such as frequent/long pauses,
low speech activity, unusual pitch variation, or low energy.
"""

import math
from typing import Any, Dict


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        value = float(value)

        if not math.isfinite(value):
            return default

        return max(0.0, value)

    except (TypeError, ValueError):
        return default


def _safe_get(
    data: Dict[str, Any],
    *keys: str,
    default: float = 0.0,
) -> Any:
    current = data

    for key in keys:
        if not isinstance(current, dict) or key not in current:
            return default

        current = current[key]

    return default if current is None else current


def _normalize(value: float, maximum: float) -> float:
    if maximum <= 0:
        return 0.0

    return min(max(value / maximum, 0.0), 1.0)


def estimate_cognitive_load(
    speech_result: Dict[str, Any],
) -> Dict[str, float]:

    duration = _safe_float(
        _safe_get(
            speech_result,
            "audio",
            "duration",
            default=0.0,
        )
    )

    if duration <= 0:
        return {"score": 0.5}

    speech_duration = _safe_float(
        _safe_get(
            speech_result,
            "audio",
            "speech_duration",
            default=0.0,
        )
    )

    number_of_pauses = _safe_float(
        _safe_get(
            speech_result,
            "features",
            "number_of_pauses",
            default=0,
        )
    )

    average_pause_duration = _safe_float(
        _safe_get(
            speech_result,
            "features",
            "average_pause_duration",
            default=0.0,
        )
    )

    max_pause_duration = _safe_float(
        _safe_get(
            speech_result,
            "features",
            "max_pause_duration",
            default=0.0,
        )
    )

    mean_energy = _safe_float(
        _safe_get(
            speech_result,
            "features",
            "mean_energy",
            default=0.0,
        )
    )

    mean_pitch = _safe_float(
        _safe_get(
            speech_result,
            "features",
            "mean_pitch",
            default=0.0,
        )
    )

    min_pitch = _safe_float(
        _safe_get(
            speech_result,
            "features",
            "min_pitch",
            default=0.0,
        )
    )

    max_pitch = _safe_float(
        _safe_get(
            speech_result,
            "features",
            "max_pitch",
            default=0.0,
        )
    )

    pause_rate = number_of_pauses / duration

    pause_rate_score = _normalize(
        pause_rate,
        0.5,
    )

    max_pause_score = _normalize(
        max_pause_duration,
        0.3 * duration,
    )

    activity_ratio = min(
        speech_duration / duration,
        1.0,
    )

    low_activity_score = 1.0 - activity_ratio

    pitch_range = max(
        0.0,
        max_pitch - min_pitch,
    )

    if mean_pitch > 0:
        pitch_range_ratio = pitch_range / mean_pitch
    else:
        pitch_range_ratio = 0.0

    if pitch_range_ratio <= 0.2:
        pitch_score = 0.7

    elif pitch_range_ratio <= 0.8:
        pitch_score = 0.2

    else:
        pitch_score = min(
            0.2 + (pitch_range_ratio - 0.8) * 0.5,
            1.0,
        )

    energy_score = 1.0 - _normalize(
        mean_energy,
        0.15,
    )

    score = (
        0.25 * pause_rate_score
        + 0.20 * max_pause_score
        + 0.20 * low_activity_score
        + 0.20 * pitch_score
        + 0.15 * energy_score
    )

    return {
        "score": round(
            max(0.0, min(score, 1.0)),
            3,
        )
    }