"""Draft-to-master media pipeline routes."""

from __future__ import annotations

import uuid
from pathlib import Path

import aiohttp
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from core.media_pipeline import (
    MediaPipelineError,
    extract_ranked_keyframes,
    normalize_delivery,
    probe_as_dict,
)
from core.runtime import project_dir, resolve_asset_url, safe_identifier
from core.drivers.comfy_upscale import upscale_driver


router = APIRouter()


class AssetVideoRequest(BaseModel):
    project_id: str
    video_url: str = Field(description="Local URL beginning with /assets/")


class NormalizeRequest(AssetVideoRequest):
    duration_seconds: float = Field(default=15.0, ge=1.0, le=60.0)
    fps: int = Field(default=24, ge=1, le=120)


class ExtractKeyframesRequest(AssetVideoRequest):
    count: int = Field(default=8, ge=1, le=64)
    sample_fps: float = Field(default=1.0, gt=0, le=24)


class UpscaleRequest(AssetVideoRequest):
    scale: float = Field(default=2.0, ge=1.0, le=4.0)
    seed: int | None = None


def _source(req: AssetVideoRequest) -> Path:
    safe_identifier(req.project_id, "project_id")
    source = resolve_asset_url(req.video_url)
    expected_root = project_dir(req.project_id, create=False).resolve()
    source.resolve().relative_to(expected_root)
    if not source.is_file():
        raise ValueError("Video asset does not exist")
    return source


@router.post("/probe")
async def probe_video(req: AssetVideoRequest):
    try:
        return probe_as_dict(_source(req))
    except (ValueError, MediaPipelineError) as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@router.post("/normalize")
async def normalize_video(req: NormalizeRequest):
    try:
        source = _source(req)
        job_id = uuid.uuid4().hex[:12]
        output_dir = project_dir(req.project_id) / "pipeline" / job_id
        output = output_dir / "delivery.mp4"
        probe = normalize_delivery(source, output, req.duration_seconds, req.fps)
        return {
            "job_id": job_id,
            "video_url": f"/assets/{req.project_id}/pipeline/{job_id}/delivery.mp4",
            "probe": probe.__dict__,
        }
    except (ValueError, MediaPipelineError) as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@router.post("/extract-keyframes")
async def extract_keyframes(req: ExtractKeyframesRequest):
    try:
        source = _source(req)
        job_id = uuid.uuid4().hex[:12]
        output_dir = project_dir(req.project_id) / "pipeline" / job_id / "keyframes"
        manifest = extract_ranked_keyframes(source, output_dir, req.count, req.sample_fps)
        for frame in manifest["frames"]:
            filename = Path(frame["file"]).name
            frame["url"] = f"/assets/{req.project_id}/pipeline/{job_id}/keyframes/selected/{filename}"
        return {"job_id": job_id, **manifest}
    except (ValueError, MediaPipelineError) as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@router.post("/upscale")
async def upscale_video(req: UpscaleRequest):
    try:
        source = _source(req)
        response = await upscale_driver.submit(req.video_url, req.scale, req.seed)
        if response.get("status") != "failed":
            job = upscale_driver._jobs[response["job_id"]]
            job["project_id"] = req.project_id
            job["duration_seconds"] = probe_as_dict(source)["duration_seconds"]
            upscale_driver._jobs[response["job_id"]] = job
        return response
    except (ValueError, aiohttp.ClientError, MediaPipelineError) as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@router.get("/upscale/status/{job_id}")
async def upscale_status(job_id: str):
    response = await upscale_driver.status(job_id)
    if response.get("status") != "completed" or response.get("delivery_video_url"):
        return response
    project_id = response.get("project_id")
    if not project_id:
        return response
    try:
        duration_value = response.get("duration_seconds")
        if duration_value is None:
            duration_value = probe_as_dict(
                resolve_asset_url(response["source_video_url"])
            )["duration_seconds"]
        duration_seconds = float(duration_value)
        output_dir = project_dir(project_id) / "pipeline" / job_id
        output_dir.mkdir(parents=True, exist_ok=True)
        raw_output = output_dir / "seedvr2_raw.mp4"
        async with aiohttp.ClientSession() as session:
            async with session.get(response["comfy_video_url"]) as download:
                download.raise_for_status()
                raw_output.write_bytes(await download.read())
        delivery = output_dir / "seedvr2_delivery.mp4"
        normalize_delivery(raw_output, delivery, duration_seconds=duration_seconds, fps=24)
        video_url = f"/assets/{project_id}/pipeline/{job_id}/{delivery.name}"
        job = upscale_driver._jobs[job_id]
        job["delivery_video_url"] = video_url
        upscale_driver._jobs[job_id] = job
        return {"job_id": job_id, **job}
    except (aiohttp.ClientError, MediaPipelineError, OSError, ValueError) as error:
        job = upscale_driver._jobs[job_id]
        job["status"] = "failed"
        job["error_message"] = str(error)
        upscale_driver._jobs[job_id] = job
        return {"job_id": job_id, **job}
