import shutil
import subprocess
from pathlib import Path

import pytest

from core.media_pipeline import extract_ranked_keyframes, normalize_delivery, probe_video


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
