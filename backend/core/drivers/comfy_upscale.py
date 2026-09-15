"""Persistent ComfyUI driver for the native SeedVR2 video workflow."""

from __future__ import annotations

import json
import os
import shutil
import time
import uuid
from pathlib import Path
from urllib.parse import urlencode

import aiohttp

from core.job_store import PersistentJobMap
from core.runtime import resolve_asset_url


class ComfyUpscaleDriver:
    OUTPUT_NODE_ID = "15"

    def __init__(self) -> None:
        self.comfy_url = os.getenv("COMFY_URL", "http://127.0.0.1:8188")
        self.comfy_dir = Path(os.getenv("COMFY_DIR", "ComfyUI")).resolve()
        self._jobs = PersistentJobMap("comfy_seedvr2_upscale")

    def _workflow(self) -> dict:
        path = Path(__file__).parent.parent / "workflows" / "seedvr2_upscale.json"
        return json.loads(path.read_text(encoding="utf-8"))

    async def submit(self, video_url: str, scale: float = 2.0, seed: int | None = None) -> dict:
        source = resolve_asset_url(video_url)
        if not source.is_file():
            raise ValueError("Video asset does not exist")
        job_id = uuid.uuid4().hex
        relative_name = f"aialra/{job_id}{source.suffix.lower()}"
        destination = self.comfy_dir / "input" / "aialra" / f"{job_id}{source.suffix.lower()}"
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)

        workflow = self._workflow()
        workflow["1"]["inputs"]["file"] = relative_name
        workflow["3"]["inputs"]["resize_type.multiplier"] = scale
        workflow["10"]["inputs"]["seed"] = seed if seed is not None else int(time.time()) % (2**32)
        job = {
            "status": "pending",
            "prompt_id": None,
            "output_node_id": self.OUTPUT_NODE_ID,
            "source_video_url": video_url,
            "input_copy": str(destination),
            "created_at": time.time(),
        }
        self._jobs[job_id] = job

        async with aiohttp.ClientSession() as session:
            async with session.post(f"{self.comfy_url}/prompt", json={"prompt": workflow}) as response:
                if response.status != 200:
                    detail = await response.text()
                    job["status"] = "failed"
                    job["error_message"] = detail
                    self._jobs[job_id] = job
                    return {"job_id": job_id, "status": "failed", "error_message": detail}
                payload = await response.json()
        job["prompt_id"] = payload.get("prompt_id")
        job["status"] = "processing"
        self._jobs[job_id] = job
        return {"job_id": job_id, "status": "processing", "prompt_id": job["prompt_id"]}

    async def status(self, job_id: str) -> dict:
        job = self._jobs.get(job_id)
        if not job:
            return {"job_id": job_id, "status": "failed", "error_message": "Job not found"}
        if job["status"] in {"completed", "failed"}:
            return {"job_id": job_id, **job}
        prompt_id = job.get("prompt_id")
        if not prompt_id:
            return {"job_id": job_id, **job}

        async with aiohttp.ClientSession() as session:
            async with session.get(f"{self.comfy_url}/history/{prompt_id}") as response:
                response.raise_for_status()
                history = await response.json()
        prompt = history.get(prompt_id)
        if not prompt:
            return {"job_id": job_id, **job}
        status = prompt.get("status", {})
        if status.get("status_str") == "error":
            job["status"] = "failed"
            job["error_message"] = "SeedVR2 execution failed"
            for message in reversed(status.get("messages", [])):
                if isinstance(message, list) and len(message) > 1 and isinstance(message[1], dict):
                    job["error_message"] = message[1].get("exception_message", job["error_message"])
                    break
            self._jobs[job_id] = job
            return {"job_id": job_id, **job}

        video_urls = self._video_urls_from_outputs(
            prompt.get("outputs", {}),
            str(job.get("output_node_id", self.OUTPUT_NODE_ID)),
        )
        if video_urls:
            job["status"] = "completed"
            job["comfy_video_url"] = video_urls[0]
            self._jobs[job_id] = job
        return {"job_id": job_id, **job}

    def _video_urls_from_outputs(self, outputs: dict, output_node_id: str) -> list[str]:
        """Return only files emitted by the workflow's SaveVideo node."""
        video_urls = []
        output = outputs.get(output_node_id, {})
        if not isinstance(output, dict):
            return video_urls
        for key in ("videos", "gifs", "images"):
            for item in output.get(key, []):
                filename = item.get("filename", "")
                if filename.lower().endswith((".mp4", ".mkv", ".webm", ".gif")):
                    query = urlencode({
                        "filename": filename,
                        "subfolder": item.get("subfolder", ""),
                        "type": item.get("type", "output"),
                    })
                    video_urls.append(f"{self.comfy_url}/view?{query}")
        return video_urls


upscale_driver = ComfyUpscaleDriver()
