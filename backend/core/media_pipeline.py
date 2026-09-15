"""Deterministic FFmpeg helpers for the draft-to-master video pipeline."""

from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

from PIL import Image, ImageFilter, ImageStat


class MediaPipelineError(RuntimeError):
    pass


@dataclass(frozen=True)
class VideoProbe:
    duration_seconds: float
    width: int
    height: int
    fps: float
    frame_count: int | None
    has_audio: bool
    video_codec: str


def _binary(name: str) -> str:
    found = shutil.which(name)
    if not found:
        raise MediaPipelineError(f"Required executable not found: {name}")
    return found


def _run(command: list[str], timeout: int = 1800) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(command, capture_output=True, text=True, timeout=timeout)
    if result.returncode != 0:
        detail = result.stderr.strip()[-2000:]
        raise MediaPipelineError(detail or f"Command failed: {command[0]}")
    return result


def _rate(value: str | None) -> float:
    if not value or value == "0/0":
        return 0.0
    numerator, denominator = value.split("/", 1)
    return float(numerator) / float(denominator)


def probe_video(path: Path) -> VideoProbe:
    path = path.resolve()
    if not path.is_file():
        raise MediaPipelineError(f"Video does not exist: {path}")
    result = _run([
        _binary("ffprobe"), "-v", "error", "-show_streams", "-show_format",
        "-of", "json", str(path),
    ], timeout=60)
    payload = json.loads(result.stdout)
    streams = payload.get("streams", [])
    video = next((stream for stream in streams if stream.get("codec_type") == "video"), None)
    if video is None:
        raise MediaPipelineError("Input has no video stream")
    duration = float(video.get("duration") or payload.get("format", {}).get("duration") or 0)
    frame_count = video.get("nb_frames")
    return VideoProbe(
        duration_seconds=duration,
        width=int(video.get("width") or 0),
        height=int(video.get("height") or 0),
        fps=_rate(video.get("avg_frame_rate")),
        frame_count=int(frame_count) if frame_count and str(frame_count).isdigit() else None,
        has_audio=any(stream.get("codec_type") == "audio" for stream in streams),
        video_codec=str(video.get("codec_name") or "unknown"),
    )


def normalize_delivery(
    input_path: Path,
    output_path: Path,
    duration_seconds: float = 15.0,
    fps: int = 24,
) -> VideoProbe:
    """Create a browser-safe H.264/AAC delivery file with exact target duration."""
    output_path = output_path.resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    command = [
        _binary("ffmpeg"), "-y", "-i", str(input_path.resolve()),
        "-map", "0:v:0", "-map", "0:a?", "-vf", f"fps={fps}",
        "-t", f"{duration_seconds:.6f}", "-c:v", "libx264", "-preset", "slow",
        "-crf", "17", "-pix_fmt", "yuv420p", "-movflags", "+faststart",
        "-c:a", "aac", "-b:a", "192k", "-ar", "48000", str(output_path),
    ]
    _run(command)
    probe = probe_video(output_path)
    frame_tolerance = 1.0 / fps + 0.01
    if abs(probe.duration_seconds - duration_seconds) > frame_tolerance:
        raise MediaPipelineError(
            f"Delivery duration is {probe.duration_seconds:.3f}s, expected {duration_seconds:.3f}s"
        )
    if abs(probe.fps - fps) > 0.01:
        raise MediaPipelineError(f"Delivery frame rate is {probe.fps:.3f}, expected {fps}")
    return probe


def _frame_score(path: Path) -> tuple[float, float, float]:
    with Image.open(path) as image:
        gray = image.convert("L").resize((384, 216))
        brightness = ImageStat.Stat(gray).mean[0]
        edges = gray.filter(ImageFilter.FIND_EDGES)
        sharpness = ImageStat.Stat(edges).var[0]
        exposure = max(0.0, 1.0 - abs(brightness - 127.5) / 127.5)
        score = sharpness * (0.6 + 0.4 * exposure)
        return score, sharpness, brightness


def _average_hash(path: Path) -> int:
    with Image.open(path) as image:
        pixels = list(image.convert("L").resize((8, 8)).getdata())
    average = sum(pixels) / len(pixels)
    value = 0
    for index, pixel in enumerate(pixels):
        if pixel >= average:
            value |= 1 << index
    return value


def _hamming(left: int, right: int) -> int:
    return (left ^ right).bit_count()


def extract_ranked_keyframes(
    input_path: Path,
    output_dir: Path,
    count: int = 8,
    sample_fps: float = 1.0,
) -> dict:
    """Sample frames, rank sharp/exposed candidates, and remove near duplicates."""
    if count < 1 or count > 64:
        raise MediaPipelineError("count must be between 1 and 64")
    output_dir = output_dir.resolve()
    candidates = output_dir / "candidates"
    selected_dir = output_dir / "selected"
    candidates.mkdir(parents=True, exist_ok=True)
    selected_dir.mkdir(parents=True, exist_ok=True)
    _run([
        _binary("ffmpeg"), "-y", "-i", str(input_path.resolve()),
        "-vf", f"fps={sample_fps}", "-vsync", "vfr",
        str(candidates / "frame_%04d.png"),
    ])
    ranked = []
    for path in sorted(candidates.glob("frame_*.png")):
        score, sharpness, brightness = _frame_score(path)
        ranked.append({
            "path": path,
            "score": score,
            "sharpness": sharpness,
            "brightness": brightness,
            "hash": _average_hash(path),
        })
    ranked.sort(key=lambda item: item["score"], reverse=True)
    selected = []
    for item in ranked:
        if any(_hamming(item["hash"], chosen["hash"]) < 8 for chosen in selected):
            continue
        selected.append(item)
        if len(selected) == count:
            break
    if len(selected) < count:
        used = {item["path"] for item in selected}
        selected.extend(
            [item for item in ranked if item["path"] not in used][
                : count - len(selected)
            ]
        )
    manifest_frames = []
    for index, item in enumerate(selected, start=1):
        destination = selected_dir / f"keyframe_{index:02d}.png"
        shutil.copy2(item["path"], destination)
        manifest_frames.append({
            "file": str(destination),
            "score": round(item["score"], 3),
            "sharpness": round(item["sharpness"], 3),
            "brightness": round(item["brightness"], 3),
        })
    manifest = {
        "source": str(input_path.resolve()),
        "sample_fps": sample_fps,
        "requested_count": count,
        "selected_count": len(manifest_frames),
        "frames": manifest_frames,
    }
    (output_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return manifest


def concat_videos(inputs: Iterable[Path], output_path: Path) -> VideoProbe:
    paths = [path.resolve() for path in inputs]
    if not paths:
        raise MediaPipelineError("At least one video is required")
    output_path = output_path.resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    concat_file = output_path.with_suffix(".concat.txt")
    concat_file.write_text(
        "".join(f"file '{str(path).replace("'", "'\\''")}'\n" for path in paths),
        encoding="utf-8",
    )
    try:
        _run([
            _binary("ffmpeg"), "-y", "-f", "concat", "-safe", "0",
            "-i", str(concat_file), "-c:v", "libx264", "-crf", "17",
            "-preset", "slow", "-pix_fmt", "yuv420p", "-c:a", "aac",
            "-movflags", "+faststart", str(output_path),
        ])
    finally:
        concat_file.unlink(missing_ok=True)
    return probe_video(output_path)


def probe_as_dict(path: Path) -> dict:
    return asdict(probe_video(path))
