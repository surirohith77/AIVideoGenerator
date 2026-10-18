"""Conservative cleanup for long pauses in generated F5-TTS WAV files."""

import os
import re
import shutil
import subprocess
import uuid
import wave
from pathlib import Path
from typing import List, Tuple


_SILENCE_START = re.compile(r"silence_start:\s*([0-9.]+)")
_SILENCE_END = re.compile(r"silence_end:\s*([0-9.]+)")


def _find_silence_ranges(
    ffmpeg: str,
    path: Path,
    minimum_pause: float,
    threshold_db: float,
) -> List[Tuple[float, float]]:
    """Use FFmpeg's sample-level detector to avoid cutting quiet consonants."""
    result = subprocess.run(
        [
            ffmpeg,
            "-hide_banner",
            "-nostats",
            "-i",
            str(path),
            "-af",
            f"silencedetect=noise={threshold_db}dB:d={minimum_pause}",
            "-f",
            "null",
            "-",
        ],
        capture_output=True,
        text=True,
        check=False,
        timeout=60,
    )
    log = result.stderr
    starts = [float(match.group(1)) for match in _SILENCE_START.finditer(log)]
    ends = [float(match.group(1)) for match in _SILENCE_END.finditer(log)]
    return list(zip(starts, ends))


def shorten_long_silences(path: str) -> float:
    """Shorten only long internal gaps, retaining silence on both word edges.

    Returns the number of seconds removed. If FFmpeg or audio processing is
    unavailable, the original generated audio is kept so rendering can continue.
    """
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        return 0.0

    minimum_pause = float(os.getenv("F5_TTS_PAUSE_MIN_SECONDS", "0.60"))
    retained_pause = float(os.getenv("F5_TTS_PAUSE_RETAIN_SECONDS", "0.32"))
    threshold_db = float(os.getenv("F5_TTS_PAUSE_THRESHOLD_DB", "-42"))
    if minimum_pause <= retained_pause or retained_pause < 0:
        return 0.0

    source = Path(path)
    try:
        with wave.open(str(source), "rb") as audio:
            duration = audio.getnframes() / audio.getframerate()
        silence_ranges = _find_silence_ranges(
            ffmpeg, source, minimum_pause, threshold_db
        )
    except (OSError, ValueError, wave.Error, subprocess.SubprocessError):
        return 0.0

    # Silence at the beginning or end can be intentional recording cadence;
    # only compress gaps surrounded by speech.
    cuts: List[Tuple[float, float]] = []
    for start, end in silence_ranges:
        if start <= 0.02 or end >= duration - 0.02:
            continue
        removable = end - start - retained_pause
        if removable > 0:
            cut_start = start + removable / 2
            cuts.append((cut_start, cut_start + removable))
    if not cuts:
        return 0.0

    segments: List[Tuple[float, float]] = []
    cursor = 0.0
    for start, end in cuts:
        if start > cursor:
            segments.append((cursor, start))
        cursor = end
    if cursor < duration:
        segments.append((cursor, duration))
    if len(segments) < 2:
        return 0.0

    graph = ";".join(
        f"[0:a]atrim=start={start:.6f}:end={end:.6f},"
        f"asetpts=PTS-STARTPTS[a{index}]"
        for index, (start, end) in enumerate(segments)
    )
    labels = "".join(f"[a{index}]" for index in range(len(segments)))
    graph += f";{labels}concat=n={len(segments)}:v=0:a=1[out]"
    temporary = source.with_name(f"{source.stem}.{uuid.uuid4().hex}.wav")
    try:
        subprocess.run(
            [
                ffmpeg,
                "-y",
                "-v",
                "error",
                "-i",
                str(source),
                "-filter_complex",
                graph,
                "-map",
                "[out]",
                "-c:a",
                "pcm_s16le",
                str(temporary),
            ],
            capture_output=True,
            check=True,
            timeout=60,
        )
        temporary.replace(source)
    except (OSError, subprocess.SubprocessError):
        return 0.0
    finally:
        temporary.unlink(missing_ok=True)

    return sum(end - start for start, end in cuts)
