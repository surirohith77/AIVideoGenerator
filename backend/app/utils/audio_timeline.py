"""Helpers for splitting continuous narration at scene boundaries."""

import re
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Tuple


_SILENCE_START = re.compile(r"silence_start:\s*([0-9.]+)")
_SILENCE_END = re.compile(r"silence_end:\s*([0-9.]+)")


def _find_pause_centers(audio_path: str) -> List[float]:
    """Return centers of short speech pauses that can serve as scene cuts."""
    result = subprocess.run(
        [
            "ffmpeg",
            "-hide_banner",
            "-nostats",
            "-i",
            audio_path,
            "-af",
            "silencedetect=noise=-42dB:d=0.18",
            "-f",
            "null",
            "-",
        ],
        capture_output=True,
        text=True,
        check=False,
        timeout=60,
    )
    starts = [float(match.group(1)) for match in _SILENCE_START.finditer(result.stderr)]
    ends = [float(match.group(1)) for match in _SILENCE_END.finditer(result.stderr)]
    return [(start + end) / 2 for start, end in zip(starts, ends) if end > start]


def split_continuous_audio_by_scenes(
    audio_path: str,
    scenes: List[Any],
    duration: float,
    output_dir: str,
) -> Tuple[List[Dict[str, float]], List[str]]:
    """Allocate continuous narration to scenes and export exact audio segments.

    Scene text gives an initial proportional estimate. Nearby speech pauses are
    preferred as boundaries so cuts are less likely to split a spoken word.
    The returned intervals partition the full audio without overlaps or gaps.
    """
    if duration <= 0 or not scenes:
        raise ValueError("Continuous narration must have a positive duration and at least one scene.")

    weights = [max(1, len((scene.narration or "").split())) for scene in scenes]
    total_weight = sum(weights)
    expected = []
    elapsed_weight = 0
    for weight in weights[:-1]:
        elapsed_weight += weight
        expected.append(duration * elapsed_weight / total_weight)

    try:
        pause_centers = _find_pause_centers(audio_path)
    except (OSError, subprocess.SubprocessError):
        pause_centers = []

    boundaries = [0.0]
    tolerance = max(1.0, min(2.5, duration * 0.08))
    min_segment = min(0.75, duration / (len(scenes) * 2))
    for index, target in enumerate(expected):
        lower = boundaries[-1] + min_segment
        upper = duration - min_segment * (len(expected) - index)
        candidates = [
            point
            for point in pause_centers
            if lower <= point <= upper and abs(point - target) <= tolerance
        ]
        boundary = min(candidates, key=lambda point: abs(point - target)) if candidates else target
        boundary = min(max(boundary, lower), upper)
        boundaries.append(boundary)
    boundaries.append(duration)

    segments: List[Dict[str, float]] = []
    output_paths: List[str] = []
    for index, (start, end) in enumerate(zip(boundaries, boundaries[1:]), 1):
        segment_duration = end - start
        if segment_duration <= 0:
            raise RuntimeError(f"Invalid narration segment duration for scene {index}.")
        output_path = str(Path(output_dir) / f"audio_scene_{index:03d}.wav")
        result = subprocess.run(
            [
                "ffmpeg",
                "-hide_banner",
                "-loglevel",
                "error",
                "-y",
                "-i",
                audio_path,
                "-ss",
                f"{start:.6f}",
                "-t",
                f"{segment_duration:.6f}",
                "-vn",
                "-c:a",
                "pcm_s16le",
                output_path,
            ],
            capture_output=True,
            text=True,
            check=False,
            timeout=60,
        )
        if result.returncode != 0:
            raise RuntimeError(
                f"Failed to create narration segment for scene {index}: "
                f"{result.stderr[-500:]}"
            )
        segments.append({"start": start, "duration": segment_duration})
        output_paths.append(output_path)

    return segments, output_paths
