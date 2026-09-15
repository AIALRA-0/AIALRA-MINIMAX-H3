"""Run the mature H3 Continuum workflow through the local ComfyUI API."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import time
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))


DEFAULT_PROMPT = """Subject: One adult woman with a short black bob, a charcoal wool coat, a narrow burgundy scarf, and a small brass compass held in her right hand. Keep her face, hair, clothing, compass, glasshouse architecture, wet floor, and cool dawn lighting unchanged throughout. Live-action cinematic photography, realistic skin and fabric, one uninterrupted tracking shot with no cut, no dissolve, no teleportation, and no camera reset.

[0-5s]
Inside a misted Victorian glasshouse at blue dawn, the woman walks slowly along the same narrow aisle between dense green ferns. The camera tracks backward at her walking speed in a steady medium shot. She looks down at the brass compass while condensation beads remain on the iron-framed glass. Her right foot lands, then her left foot begins the next step as the section ends.

[5-10s]
Continue the exact same walking stride from the preceding instant: her left foot completes that step and her coat hem preserves its direction and momentum. The same camera continues tracking backward at the same speed and height without reframing. She raises the same brass compass slightly toward the cool window light, then lifts her gaze toward the far end of the same aisle. Keep the ferns, wet floor reflections, fog, face, clothing, and lighting continuous.

[10-15s]
Continue from that exact pose and camera velocity. She slows naturally without stopping abruptly, closes her fingers around the same compass, and turns only her eyes toward a soft movement among the ferns on her left. The camera eases backward with her while preserving the same lens, axis, height, and composition. End with her still in the same aisle and the ambient mist unchanged.

overall_soundscape: A continuous low glasshouse ventilation hum, soft rain ticking on the same glass roof, steady shoe steps on the wet stone floor, quiet coat fabric movement, and one uninterrupted distant bird call. No sound resets at section boundaries.

non_diegetic_music: A single sustained low cello tone with sparse soft piano notes, continuous in tempo, room, and volume across the full sequence, fading only during the final second."""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--comfy-url", default="http://127.0.0.1:8188")
    parser.add_argument("--duration", type=float, default=15.0)
    parser.add_argument("--chunks", type=int, default=3)
    parser.add_argument("--seed", type=int, default=408031)
    parser.add_argument("--balanced", action="store_true")
    parser.add_argument("--run-name", default="aialra_h3_continuum_glasshouse_v1")
    parser.add_argument(
        "--video-seam",
        choices=("Analyze Only", "Auto", "Auto 2", "Off"),
        default="Analyze Only",
    )
    parser.add_argument("--prompt-file", type=Path)
    parser.add_argument("--poll-seconds", type=float, default=10.0)
    return parser.parse_args()


async def wait_for_job(driver, job_id: str, poll_seconds: float):
    from core.drivers.base import GenerationStatus

    started = time.monotonic()
    while True:
        response = await driver.check_status(job_id)
        elapsed = time.monotonic() - started
        print(json.dumps({
            "event": "poll",
            "job_id": job_id,
            "status": response.status.value,
            "elapsed_seconds": round(elapsed, 1),
        }), flush=True)
        if response.status == GenerationStatus.COMPLETED:
            return response, elapsed
        if response.status == GenerationStatus.FAILED:
            raise RuntimeError(response.error_message or "H3 Continuum job failed")
        await asyncio.sleep(poll_seconds)


async def run(args: argparse.Namespace) -> None:
    from core.drivers.base import AspectRatio, GenerationStatus, VideoGenerationMode, VideoGenerationRequest
    from core.drivers.comfy_video import ComfyVideoDriver

    runtime_root = Path(r"D:\AIALRA-MINIMAX-H3")
    output_dir = runtime_root / "outputs" / "continuum"
    output_dir.mkdir(parents=True, exist_ok=True)
    os.environ["COMFY_OUTPUT_DIR"] = str(runtime_root / "outputs" / "comfyui")

    prompt = DEFAULT_PROMPT
    if args.prompt_file:
        prompt = args.prompt_file.read_text(encoding="utf-8").strip()

    request = VideoGenerationRequest(
        prompt=prompt,
        mode=VideoGenerationMode.T2V,
        duration_seconds=args.duration,
        aspect_ratio=AspectRatio.LANDSCAPE_16_9,
        seed=args.seed,
        extra_params={
            "continuum": True,
            "continuum_chunks": args.chunks,
            "continuum_chunk_seconds": args.duration / args.chunks,
            "continuum_balanced": args.balanced,
            "continuum_context": "Balanced — 22 frames",
            "continuum_audio": True,
            "continuum_storage": "Save + Auto Resume",
            "continuum_run_name": args.run_name,
            "continuum_video_seam": args.video_seam,
            "continuum_audio_seam": "Auto",
        },
    )
    driver = ComfyVideoDriver(comfy_url=args.comfy_url, model_id="minimax_h3")
    print(json.dumps({"event": "submit", "run_name": args.run_name}), flush=True)
    response = await driver.generate(request)
    if response.status == GenerationStatus.FAILED:
        raise RuntimeError(response.error_message or "H3 Continuum submission failed")
    completed, elapsed = await wait_for_job(driver, response.job_id, args.poll_seconds)
    downloaded = Path(await driver.download(response.job_id, str(output_dir)))
    final_path = output_dir / f"{args.run_name}.mp4"
    if downloaded.resolve() != final_path.resolve():
        os.replace(downloaded, final_path)
    print(json.dumps({
        "event": "complete",
        "file": str(final_path),
        "elapsed_seconds": round(elapsed, 1),
        "comfy_video_url": completed.video_url,
    }), flush=True)


def main() -> int:
    args = parse_args()
    asyncio.run(run(args))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
