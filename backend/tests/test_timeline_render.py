from pathlib import Path

from api import routes_timeline


def test_timeline_export_preserves_transitions_audio_offsets_and_volume(tmp_path: Path, monkeypatch):
    first = tmp_path / "first.mp4"
    second = tmp_path / "second.mp4"
    music = tmp_path / "music.wav"
    for path in (first, second, music):
        path.write_bytes(b"fixture")
    monkeypatch.setattr(routes_timeline, "_source_has_audio", lambda path: True)

    videos = [
        {
            "sourceUrl": str(first), "startTime": 0, "trimInSeconds": 0,
            "trimOutSeconds": 5, "volume": 0.8,
            "transitionOut": {"type": "dissolve", "durationSeconds": 0.25},
        },
        {
            "sourceUrl": str(second), "startTime": 4.75, "trimInSeconds": 0,
            "trimOutSeconds": 5, "volume": 0.7,
            "transitionIn": {"type": "dissolve", "durationSeconds": 0.25},
        },
    ]
    audio = [{
        "sourceUrl": str(music), "startTime": 1.5, "trimInSeconds": 0,
        "trimOutSeconds": 8, "volume": 0.5, "_track_volume": 0.6,
        "fadeInSeconds": 0.4, "fadeOutSeconds": 0.6,
    }]

    command = routes_timeline._build_ffmpeg_command(videos, audio, str(tmp_path / "out.mp4"))
    filters = command[command.index("-filter_complex") + 1]

    assert "xfade=transition=fade:duration=0.250000" in filters
    assert "adelay=1500|1500" in filters
    assert "volume=0.300000" in filters
    assert "afade=t=in:st=0:d=0.400000" in filters
    assert "amix=inputs=3:duration=longest:normalize=0:dropout_transition=0" in filters
    assert filters.count("loudnorm=I=-16:LRA=11:TP=-1.5") == 1


def test_atempo_chain_supports_full_editor_speed_range():
    assert routes_timeline._atempo_filter(0.25) == "atempo=0.500000,atempo=0.500000"
    assert routes_timeline._atempo_filter(4) == "atempo=2.000000,atempo=2.000000"
