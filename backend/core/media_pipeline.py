"""Deterministic FFmpeg helpers for the draft-to-master video pipeline."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import time
from dataclasses import asdict, dataclass
from functools import lru_cache
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
    configured = os.getenv(f"AIALRA_{name.upper()}", "").strip()
    if configured:
        path = Path(configured).expanduser().resolve()
        if path.is_file():
            return str(path)
        raise MediaPipelineError(f"Configured executable does not exist: {path}")
    found = shutil.which(name)
    if not found:
        raise MediaPipelineError(f"Required executable not found: {name}")
    return found


def _run(command: list[str], timeout: int = 1800) -> subprocess.CompletedProcess[str]:
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired as error:
        raise MediaPipelineError(f"Command timed out after {timeout}s: {command[0]}") from error
    if result.returncode != 0:
        detail = result.stderr.strip()[-2000:]
        raise MediaPipelineError(detail or f"Command failed: {command[0]}")
    return result


def _env_int(name: str, default: int, minimum: int = 0) -> int:
    raw = os.getenv(name, str(default)).strip()
    try:
        value = int(raw)
    except ValueError:
        return default
    return max(minimum, value)


@lru_cache(maxsize=8)
def _ffmpeg_has_encoder(ffmpeg: str, encoder: str) -> bool:
    result = subprocess.run(
        [ffmpeg, "-hide_banner", "-encoders"],
        capture_output=True,
        text=True,
        timeout=30,
    )
    return result.returncode == 0 and encoder in result.stdout


def _media_gpu_metrics(gpu_index: int) -> dict[str, int] | None:
    nvidia_smi = shutil.which("nvidia-smi")
    if not nvidia_smi:
        return None
    result = subprocess.run(
        [
            nvidia_smi,
            f"--id={gpu_index}",
            "--query-gpu=utilization.gpu,utilization.encoder,utilization.decoder,memory.free",
            "--format=csv,noheader,nounits",
        ],
        capture_output=True,
        text=True,
        timeout=10,
    )
    if result.returncode != 0:
        return None
    try:
        graphics, encoder, decoder, memory_free = (
            int(value.strip()) for value in result.stdout.strip().split(",")
        )
    except (TypeError, ValueError):
        return None
    return {
        "graphics_percent": graphics,
        "encoder_percent": encoder,
        "decoder_percent": decoder,
        "memory_free_mib": memory_free,
    }


def media_acceleration_status() -> dict:
    """Describe whether the display GPU is currently safe for fixed-function encode."""
    mode = os.getenv("AIALRA_MEDIA_ACCELERATION", "auto").strip().lower()
    gpu_index = _env_int("AIALRA_MEDIA_GPU_INDEX", 1)
    max_graphics = _env_int("AIALRA_MEDIA_GPU_MAX_GRAPHICS", 20, minimum=1)
    max_encoder = _env_int("AIALRA_MEDIA_GPU_MAX_ENCODER", 10, minimum=1)
    max_decoder = _env_int("AIALRA_MEDIA_GPU_MAX_DECODER", 10, minimum=1)
    min_memory = _env_int("AIALRA_MEDIA_GPU_MIN_FREE_MIB", 1024)
    try:
        ffmpeg = _binary("ffmpeg")
        has_nvenc = _ffmpeg_has_encoder(ffmpeg, "h264_nvenc")
    except (MediaPipelineError, OSError, subprocess.SubprocessError):
        ffmpeg = None
        has_nvenc = False
    metrics = _media_gpu_metrics(gpu_index)
    reason = "ready"
    if mode == "cpu":
        reason = "disabled_by_configuration"
    elif mode not in {"auto", "nvenc"}:
        reason = "invalid_mode"
    elif ffmpeg is None:
        reason = "ffmpeg_unavailable"
    elif not has_nvenc:
        reason = "ffmpeg_without_nvenc"
    elif metrics is None:
        reason = "gpu_metrics_unavailable"
    elif metrics["graphics_percent"] > max_graphics:
        reason = "display_gpu_busy"
    elif metrics["encoder_percent"] > max_encoder:
        reason = "encoder_busy"
    elif metrics["decoder_percent"] > max_decoder:
        reason = "decoder_busy"
    elif metrics["memory_free_mib"] < min_memory:
        reason = "display_gpu_memory_pressure"
    return {
        "mode": mode,
        "gpu_index": gpu_index,
        "nvenc_available": has_nvenc,
        "selected_encoder": "h264_nvenc" if reason == "ready" else "libx264",
        "reason": reason,
        "metrics": metrics,
        "limits": {
            "graphics_percent": max_graphics,
            "encoder_percent": max_encoder,
            "decoder_percent": max_decoder,
            "memory_free_mib": min_memory,
        },
    }


def _video_encoder_args(
    quality: int = 17,
    pixel_rate: float | None = None,
) -> tuple[list[str], dict]:
    status = media_acceleration_status()
    max_pixel_rate = _env_int(
        "AIALRA_MEDIA_GPU_MAX_PIXEL_RATE",
        1920 * 1080 * 30,
        minimum=1,
    )
    status["limits"]["pixel_rate"] = max_pixel_rate
    if pixel_rate is not None and pixel_rate > max_pixel_rate:
        status["selected_encoder"] = "libx264"
        status["reason"] = "pixel_rate_exceeds_display_safe_limit"
    elif status["selected_encoder"] == "h264_nvenc":
        # A second idle sample keeps a transient foreground spike from starting
        # work on the display adapter. The running process remains guarded below.
        time.sleep(0.15)
        second_sample = media_acceleration_status()
        if second_sample["selected_encoder"] != "h264_nvenc":
            status = second_sample
            status["limits"]["pixel_rate"] = max_pixel_rate
    if status["selected_encoder"] == "h264_nvenc":
        return [
            "-c:v", "h264_nvenc", "-gpu", str(status["gpu_index"]),
            "-preset", "p7", "-tune", "hq", "-rc", "vbr", "-cq", str(quality),
            "-b:v", "0", "-spatial-aq", "1",
        ], status
    return ["-c:v", "libx264", "-preset", "slow", "-crf", str(quality)], status


def _run_guarded_encode(
    command: list[str],
    cpu_command: list[str],
    status: dict,
    timeout: int = 1800,
) -> subprocess.CompletedProcess[str]:
    """Run NVENC only while display/3D load stays below the configured limit."""
    if status["selected_encoder"] != "h264_nvenc":
        return _run(cpu_command, timeout=timeout)
    process = subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, text=True)
    deadline = time.monotonic() + timeout
    busy_samples = 0
    while process.poll() is None:
        if time.monotonic() >= deadline:
            process.kill()
            process.communicate()
            raise MediaPipelineError(f"Encode timed out after {timeout}s")
        metrics = _media_gpu_metrics(status["gpu_index"])
        display_is_busy = metrics is None or any((
            metrics["graphics_percent"] > status["limits"]["graphics_percent"],
            metrics["encoder_percent"] > status["limits"]["encoder_percent"],
            metrics["decoder_percent"] > status["limits"]["decoder_percent"],
            metrics["memory_free_mib"] < status["limits"]["memory_free_mib"],
        ))
        if display_is_busy:
            busy_samples += 1
        else:
            busy_samples = 0
        if busy_samples >= 2:
            process.terminate()
            try:
                process.communicate(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.communicate()
            return _run(cpu_command, timeout=timeout)
        time.sleep(0.5)
    process.wait()
    result = subprocess.CompletedProcess(command, process.returncode, "", "")
    if result.returncode != 0:
        return _run(cpu_command, timeout=timeout)
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
    prefix = [
        _binary("ffmpeg"), "-y", "-i", str(input_path.resolve()),
        "-map", "0:v:0", "-map", "0:a?", "-vf", f"fps={fps}",
        "-t", f"{duration_seconds:.6f}",
    ]
    suffix = [
        "-pix_fmt", "yuv420p", "-movflags", "+faststart",
        "-c:a", "aac", "-b:a", "192k", "-ar", "48000", str(output_path),
    ]
    input_probe = probe_video(input_path)
    encoder_args, acceleration = _video_encoder_args(
        quality=17,
        pixel_rate=input_probe.width * input_probe.height * fps,
    )
    command = [*prefix, *encoder_args, *suffix]
    cpu_command = [*prefix, "-c:v", "libx264", "-preset", "slow", "-crf", "17", *suffix]
    _run_guarded_encode(command, cpu_command, acceleration)
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
        "-vf", f"fps={sample_fps}", "-fps_mode", "vfr",
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
    concat_lines = []
    for path in paths:
        escaped_path = str(path).replace("'", "'\\''")
        concat_lines.append(f"file '{escaped_path}'\n")
    concat_file.write_text("".join(concat_lines), encoding="utf-8")
    try:
        probes = [probe_video(path) for path in paths]
        first = probes[0]
        stream_copy_safe = all(
            probe.video_codec == first.video_codec
            and probe.width == first.width
            and probe.height == first.height
            and abs(probe.fps - first.fps) < 0.01
            and probe.has_audio == first.has_audio
            for probe in probes[1:]
        )
        if stream_copy_safe:
            copy_result = subprocess.run(
                [
                    _binary("ffmpeg"), "-y", "-f", "concat", "-safe", "0",
                    "-i", str(concat_file), "-map", "0:v:0", "-map", "0:a?",
                    "-c", "copy", "-movflags", "+faststart", str(output_path),
                ],
                capture_output=True,
                text=True,
                timeout=300,
            )
            if copy_result.returncode == 0:
                return probe_video(output_path)
        encoder_args, acceleration = _video_encoder_args(
            quality=17,
            pixel_rate=first.width * first.height * first.fps,
        )
        prefix = [
            _binary("ffmpeg"), "-y", "-f", "concat", "-safe", "0",
            "-i", str(concat_file),
        ]
        suffix = [
            "-pix_fmt", "yuv420p", "-c:a", "aac",
            "-movflags", "+faststart", str(output_path),
        ]
        _run_guarded_encode(
            [*prefix, *encoder_args, *suffix],
            [*prefix, "-c:v", "libx264", "-crf", "17", "-preset", "slow", *suffix],
            acceleration,
        )
    finally:
        concat_file.unlink(missing_ok=True)
    return probe_video(output_path)


def smooth_concatenated_audio(
    inputs: Iterable[Path],
    video_master: Path,
    output_path: Path,
    fade_seconds: float = 0.08,
) -> VideoProbe:
    """Keep the assembled video bitstream while smoothing native-audio boundaries."""
    paths = [path.resolve() for path in inputs]
    if not paths:
        raise MediaPipelineError("At least one video is required")
    probes = [probe_video(path) for path in paths]
    if not all(probe.has_audio for probe in probes):
        raise MediaPipelineError("Every input must contain audio")
    output_path = output_path.resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    command = [_binary("ffmpeg"), "-y", "-i", str(video_master.resolve())]
    for path in paths:
        command.extend(["-i", str(path)])
    filters = []
    labels = []
    for index, probe in enumerate(probes, start=1):
        label = f"a{index}"
        chain = [
            f"[{index}:a:0]loudnorm=I=-24:LRA=7:TP=-2",
            "aresample=48000",
        ]
        if index > 1:
            chain.append(f"afade=t=in:st=0:d={fade_seconds:.3f}")
        if index < len(probes):
            fade_start = max(0.0, probe.duration_seconds - fade_seconds)
            chain.append(f"afade=t=out:st={fade_start:.6f}:d={fade_seconds:.3f}")
        filters.append(",".join(chain) + f",asetpts=PTS-STARTPTS[{label}]")
        labels.append(f"[{label}]")
    filters.append("".join(labels) + f"concat=n={len(paths)}:v=0:a=1[aout]")
    command.extend([
        "-filter_complex", ";".join(filters),
        "-map", "0:v:0", "-map", "[aout]",
        "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
        "-movflags", "+faststart", "-shortest", str(output_path),
    ])
    _run(command, timeout=600)
    return probe_video(output_path)


def probe_as_dict(path: Path) -> dict:
    return asdict(probe_video(path))
