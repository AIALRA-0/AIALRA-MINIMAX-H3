import json
from pathlib import Path

import pytest

from core.drivers.base import AspectRatio, VideoGenerationMode, VideoGenerationRequest
from core.drivers.comfy_video import ComfyVideoDriver
from core.drivers.comfy_upscale import ComfyUpscaleDriver
from core.job_store import PersistentJobMap
from core.runtime import path_within, safe_identifier


def _request(**extra_params) -> VideoGenerationRequest:
    return VideoGenerationRequest(
        prompt="A quiet test shot with room tone",
        mode=VideoGenerationMode.T2V,
        duration_seconds=15.0,
        aspect_ratio=AspectRatio.LANDSCAPE_16_9,
        seed=1234,
        extra_params=extra_params,
    )


def test_h3_draft_profile_is_362_frames_and_eight_steps():
    driver = ComfyVideoDriver(model_id="minimax_h3")
    workflow = driver._build_workflow(_request(turbo_mode=True, megapixels=0.2))
    assert workflow["104"]["inputs"]["length"] == 362
    assert workflow["9"]["inputs"]["steps"] == 8
    assert workflow["115"]["inputs"]["megapixels"] == 0.2
    assert workflow["200"]["inputs"]["model"] == ["201", 0]
    assert workflow["202"]["inputs"] == {"model": ["200", 0], "head_chunks": 4}
    assert workflow["203"]["inputs"]["model"] == ["202", 0]
    assert workflow["9"]["inputs"]["model"] == ["203", 0]
    assert workflow["16"]["inputs"]["model"] == ["203", 0]


def test_h3_quality_profile_removes_lightning_lora():
    driver = ComfyVideoDriver(model_id="minimax_h3")
    workflow = driver._build_workflow(_request(turbo_mode=False, megapixels=0.4))
    assert "201" not in workflow
    assert workflow["9"]["inputs"]["steps"] == 20
    assert workflow["200"]["inputs"]["model"] == ["6", 0]


def test_job_mapping_survives_new_instance():
    namespace = "test-restart-roundtrip"
    first = PersistentJobMap(namespace)
    first.pop("job-1", None)
    first["job-1"] = {"prompt_id": "comfy-123", "status": "processing"}
    second = PersistentJobMap(namespace)
    assert second["job-1"]["prompt_id"] == "comfy-123"
    second.pop("job-1")


@pytest.mark.parametrize("value", ["../escape", "..", "bad/name", "bad\\name", ""])
def test_unsafe_identifier_is_rejected(value):
    with pytest.raises(ValueError):
        safe_identifier(value)


def test_path_within_rejects_parent_escape(tmp_path: Path):
    with pytest.raises(ValueError):
        path_within(tmp_path, "..", "escape")


def test_video_driver_resolves_local_asset_for_i2v(tmp_path: Path, monkeypatch):
    image = tmp_path / "first-frame.png"
    image.write_bytes(b"test")
    monkeypatch.setattr(
        "core.drivers.comfy_video.resolve_asset_url",
        lambda asset_url: image,
    )

    driver = ComfyVideoDriver(model_id="minimax_h3")
    assert driver._resolve_to_local_abs("/assets/demo/first-frame.png") == str(image.resolve())


def test_seedvr2_conditioning_uses_the_same_temporal_chunks_as_sampler():
    workflow_path = Path(__file__).parents[1] / "core" / "workflows" / "seedvr2_upscale.json"
    workflow = json.loads(workflow_path.read_text(encoding="utf-8"))

    chunked_latent = workflow["9"]["inputs"]["latent"]
    assert chunked_latent == ["6", 0]
    assert workflow["8"]["inputs"]["vae_conditioning"] == ["9", 0]
    assert workflow["10"]["inputs"]["latent_image"] == ["9", 0]


def test_seedvr2_driver_ignores_load_video_input_echo():
    driver = ComfyUpscaleDriver()
    outputs = {
        "1": {"videos": [{"filename": "copied-input.mp4", "type": "input"}]},
        "15": {
            "videos": [
                {
                    "filename": "AIALRA_SeedVR2_00001_.mp4",
                    "subfolder": "video",
                    "type": "output",
                }
            ]
        },
    }

    urls = driver._video_urls_from_outputs(outputs, driver.OUTPUT_NODE_ID)
    assert len(urls) == 1
    assert "AIALRA_SeedVR2_00001_.mp4" in urls[0]
    assert "type=output" in urls[0]
