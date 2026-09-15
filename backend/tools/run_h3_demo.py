"""Generate a resumable three-shot MiniMax H3 continuity demo."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import shutil
import sys
import time
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("anchor", type=Path, help="Initial image used as the first I2V anchor")
    parser.add_argument("--runtime-root", type=Path, default=Path(r"D:\AIALRA-MINIMAX-H3"))
    parser.add_argument("--project-id", default="aialra_h3_glasshouse_15s")
    parser.add_argument("--comfy-url", default="http://127.0.0.1:8188")
    parser.add_argument("--megapixels", type=float, default=0.4)
    parser.add_argument("--steps", type=int, default=20)
    parser.add_argument("--duration", type=float, default=5.17)
    parser.add_argument("--poll-seconds", type=float, default=10.0)
    parser.add_argument("--prompt-dir", type=Path)
    parser.add_argument("--ffmpeg", type=Path)
    return parser.parse_args()


def configure_environment(args: argparse.Namespace) -> tuple[Path, Path]:
    runtime_root = args.runtime_root.resolve()
    data_root = runtime_root / "outputs" / "studio"
    os.environ["AIALRA_DATA_ROOT"] = str(data_root)
    os.environ["AIALRA_JOB_DB"] = str(data_root / "jobs.sqlite3")
    os.environ["COMFY_URL"] = args.comfy_url
    os.environ["COMFY_VIDEO_URL"] = args.comfy_url
    os.environ["COMFY_OUTPUT_DIR"] = str(runtime_root / "outputs" / "comfyui")
    if args.ffmpeg:
        ffmpeg = args.ffmpeg.resolve()
        os.environ["AIALRA_FFMPEG"] = str(ffmpeg)
        ffprobe = ffmpeg.with_name("ffprobe.exe" if os.name == "nt" else "ffprobe")
        if ffprobe.is_file():
            os.environ["AIALRA_FFPROBE"] = str(ffprobe)
    return runtime_root, data_root


def tail_frame(video: Path, output: Path) -> None:
    from core.media_pipeline import _binary, _run

    output.parent.mkdir(parents=True, exist_ok=True)
    _run([
        _binary("ffmpeg"), "-y", "-sseof", "-0.08", "-i", str(video),
        "-frames:v", "1", "-q:v", "2", str(output),
    ], timeout=120)


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
            raise RuntimeError(response.error_message or "MiniMax H3 job failed")
        await asyncio.sleep(poll_seconds)


async def run(args: argparse.Namespace, data_root: Path) -> Path:
    from core.drivers.base import AspectRatio, GenerationStatus, VideoGenerationMode, VideoGenerationRequest
    from core.drivers.comfy_video import ComfyVideoDriver
    from core.media_pipeline import (
        concat_videos,
        extract_ranked_keyframes,
        probe_as_dict,
        smooth_concatenated_audio,
    )

    source_anchor = args.anchor.resolve()
    if not source_anchor.is_file():
        raise FileNotFoundError(source_anchor)
    project_dir = data_root / args.project_id
    shots_dir = project_dir / "shots"
    anchors_dir = project_dir / "anchors"
    delivery_dir = project_dir / "delivery"
    for directory in (shots_dir, anchors_dir, delivery_dir):
        directory.mkdir(parents=True, exist_ok=True)

    first_anchor = anchors_dir / "anchor_00.png"
    if not first_anchor.is_file():
        shutil.copy2(source_anchor, first_anchor)

    prompt_root = (args.prompt_dir or Path(__file__).resolve().parents[2] / "examples" / "prompts").resolve()
    prompts = [
        (prompt_root / f"h3_glasshouse_shot_{index:02d}.txt").read_text(encoding="utf-8").strip()
        for index in range(1, 4)
    ]
    manifest_path = project_dir / "manifest.json"
    manifest = {
        "project_id": args.project_id,
        "model": "MiniMax H3 FL2VA pruned INT8 ConvRot",
        "profile": "base-quality",
        "steps": args.steps,
        "megapixels": args.megapixels,
        "segment_duration_seconds": args.duration,
        "shots": [],
    }
    if manifest_path.is_file():
        manifest.update(json.loads(manifest_path.read_text(encoding="utf-8")))

    driver = ComfyVideoDriver(comfy_url=args.comfy_url, model_id="minimax_h3")
    shot_paths: list[Path] = []
    current_anchor = first_anchor
    for index, prompt in enumerate(prompts, start=1):
        shot_path = shots_dir / f"shot_{index:02d}.mp4"
        next_anchor = anchors_dir / f"anchor_{index:02d}.png"
        if shot_path.is_file() and next_anchor.is_file():
            print(json.dumps({"event": "resume", "shot": index, "file": str(shot_path)}), flush=True)
            shot_paths.append(shot_path)
            current_anchor = next_anchor
            continue

        anchor_url = "/assets/" + current_anchor.relative_to(data_root).as_posix()
        request = VideoGenerationRequest(
            prompt=prompt,
            mode=VideoGenerationMode.I2V,
            duration_seconds=args.duration,
            aspect_ratio=AspectRatio.LANDSCAPE_16_9,
            seed=408030 + index,
            first_frame_path=anchor_url,
            extra_params={
                "turbo_mode": False,
                "steps": args.steps,
                "megapixels": args.megapixels,
            },
        )
        print(json.dumps({"event": "submit", "shot": index, "anchor": anchor_url}), flush=True)
        response = await driver.generate(request)
        if response.status == GenerationStatus.FAILED:
            raise RuntimeError(response.error_message or "MiniMax H3 submission failed")
        completed, elapsed = await wait_for_job(driver, response.job_id, args.poll_seconds)
        downloaded = Path(await driver.download(response.job_id, str(shots_dir)))
        if downloaded != shot_path:
            os.replace(downloaded, shot_path)
        tail_frame(shot_path, next_anchor)
        shot_record = {
            "index": index,
            "seed": request.seed,
            "prompt": prompt,
            "input_anchor": str(current_anchor),
            "output_video": str(shot_path),
            "output_anchor": str(next_anchor),
            "elapsed_seconds": round(elapsed, 1),
            "probe": probe_as_dict(shot_path),
            "comfy_video_url": completed.video_url,
        }
        manifest["shots"] = [record for record in manifest.get("shots", []) if record.get("index") != index]
        manifest["shots"].append(shot_record)
        manifest["shots"].sort(key=lambda record: record["index"])
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        shot_paths.append(shot_path)
        current_anchor = next_anchor

    stream_master = delivery_dir / "aialra_h3_glasshouse_15s_streamcopy.mp4"
    concat_videos(shot_paths, stream_master)
    master = delivery_dir / "aialra_h3_glasshouse_15s.mp4"
    probe = smooth_concatenated_audio(shot_paths, stream_master, master)
    keyframes = extract_ranked_keyframes(master, delivery_dir / "keyframes", count=8, sample_fps=2.0)
    manifest["master"] = {
        "file": str(master),
        "stream_copy_source": str(stream_master),
        "video_reencoded": False,
        "audio_boundary_fade_seconds": 0.08,
        "probe": probe.__dict__,
    }
    manifest["keyframes"] = keyframes
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"event": "complete", "master": str(master), "probe": probe.__dict__}), flush=True)
    return master


def main() -> int:
    args = parse_args()
    _, data_root = configure_environment(args)
    asyncio.run(run(args, data_root))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
