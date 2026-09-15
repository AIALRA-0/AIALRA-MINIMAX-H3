import shutil
import subprocess
from pathlib import Path

import pytest

from core.media_pipeline import (
    _video_encoder_args,
    concat_videos,
    extract_ranked_keyframes,
    media_acceleration_status,
    normalize_delivery,
    probe_video,
    smooth_concatenated_audio,
)


pytestmark = pytest.mark.skipif(
    shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None,
    reason="FFmpeg is required",
)


def _synthetic_video(path: Path, duration: float = 2.2) -> None:
    subprocess.run(
        [
            shutil.which("ffmpeg"), "-y", "-f", "lavfi",
            "-i", f"testsrc2=size=320x180:rate=30:duration={duration}",
            "-f", "lavfi", "-i", f"sine=frequency=440:duration={duration}",
            "-shortest", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac",
            str(path),
        ],
        check=True,
        capture_output=True,
    )


def test_normalize_delivery_enforces_duration_and_fps(tmp_path: Path):
    source = tmp_path / "source.mp4"
    output = tmp_path / "delivery.mp4"
    _synthetic_video(source, duration=2.2)
    result = normalize_delivery(source, output, duration_seconds=2.0, fps=24)
    assert abs(result.duration_seconds - 2.0) < 0.06
    assert abs(result.fps - 24.0) < 0.01
    assert result.has_audio


def test_extract_ranked_keyframes_writes_manifest(tmp_path: Path):
    source = tmp_path / "source.mp4"
    _synthetic_video(source, duration=3.2)
    manifest = extract_ranked_keyframes(source, tmp_path / "frames", count=3, sample_fps=1.0)
    assert manifest["selected_count"] == 3
    assert (tmp_path / "frames" / "manifest.json").is_file()
    assert all(Path(frame["file"]).is_file() for frame in manifest["frames"])


def test_probe_video_reports_geometry(tmp_path: Path):
    source = tmp_path / "source.mp4"
    _synthetic_video(source)
    probe = probe_video(source)
    assert (probe.width, probe.height) == (320, 180)
    assert probe.video_codec == "h264"


def test_concat_videos_preserves_compatible_streams(tmp_path: Path, monkeypatch):
    first = tmp_path / "first.mp4"
    second = tmp_path / "second.mp4"
    output = tmp_path / "joined.mp4"
    _synthetic_video(first, duration=1.0)
    _synthetic_video(second, duration=1.0)
    monkeypatch.setattr(
        "core.media_pipeline._video_encoder_args",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("encoder should not run")),
    )
    result = concat_videos([first, second], output)
    assert output.is_file()
    assert result.video_codec == "h264"
    assert result.has_audio
    assert result.duration_seconds > 1.8


def test_media_status_survives_invalid_numeric_configuration(monkeypatch):
    monkeypatch.setenv("AIALRA_MEDIA_ACCELERATION", "cpu")
    monkeypatch.setenv("AIALRA_MEDIA_GPU_INDEX", "not-a-number")
    monkeypatch.setenv("AIALRA_MEDIA_GPU_MAX_GRAPHICS", "invalid")
    status = media_acceleration_status()
    assert status["selected_encoder"] == "libx264"
    assert status["reason"] == "disabled_by_configuration"


def test_display_gpu_is_not_used_above_safe_pixel_rate(monkeypatch):
    monkeypatch.setenv("AIALRA_MEDIA_GPU_MAX_PIXEL_RATE", "100")
    monkeypatch.setattr(
        "core.media_pipeline.media_acceleration_status",
        lambda: {
            "selected_encoder": "h264_nvenc",
            "reason": "ready",
            "gpu_index": 1,
            "limits": {},
        },
    )
    encoder, status = _video_encoder_args(pixel_rate=101)
    assert encoder[1] == "libx264"
    assert status["reason"] == "pixel_rate_exceeds_display_safe_limit"


def test_smooth_audio_keeps_video_stream_and_duration(tmp_path: Path):
    first = tmp_path / "first.mp4"
    second = tmp_path / "second.mp4"
    stream_master = tmp_path / "stream.mp4"
    output = tmp_path / "smooth.mp4"
    _synthetic_video(first, duration=1.0)
    _synthetic_video(second, duration=1.0)
    concat_videos([first, second], stream_master)
    result = smooth_concatenated_audio([first, second], stream_master, output)
    assert result.video_codec == "h264"
    assert result.has_audio
    assert result.duration_seconds > 1.8
