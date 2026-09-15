"""Command-line entry point for delivery normalization and keyframe selection."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from core.media_pipeline import (
    concat_videos,
    extract_ranked_keyframes,
    normalize_delivery,
    probe_as_dict,
    smooth_concatenated_audio,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="AIALRA H3 media pipeline")
    subparsers = parser.add_subparsers(dest="command", required=True)

    probe = subparsers.add_parser("probe")
    probe.add_argument("input", type=Path)

    normalize = subparsers.add_parser("normalize")
    normalize.add_argument("input", type=Path)
    normalize.add_argument("output", type=Path)
    normalize.add_argument("--duration", type=float, default=15.0)
    normalize.add_argument("--fps", type=int, default=24)

    frames = subparsers.add_parser("extract-keyframes")
    frames.add_argument("input", type=Path)
    frames.add_argument("output_dir", type=Path)
    frames.add_argument("--count", type=int, default=8)
    frames.add_argument("--sample-fps", type=float, default=1.0)

    concat = subparsers.add_parser("concat")
    concat.add_argument("output", type=Path)
    concat.add_argument("inputs", type=Path, nargs="+")

    smooth = subparsers.add_parser("smooth-audio")
    smooth.add_argument("video_master", type=Path)
    smooth.add_argument("output", type=Path)
    smooth.add_argument("inputs", type=Path, nargs="+")
    smooth.add_argument("--fade-seconds", type=float, default=0.08)

    args = parser.parse_args()
    if args.command == "probe":
        payload = probe_as_dict(args.input)
    elif args.command == "normalize":
        payload = normalize_delivery(args.input, args.output, args.duration, args.fps).__dict__
    elif args.command == "extract-keyframes":
        payload = extract_ranked_keyframes(args.input, args.output_dir, args.count, args.sample_fps)
    elif args.command == "concat":
        payload = concat_videos(args.inputs, args.output).__dict__
    else:
        payload = smooth_concatenated_audio(
            args.inputs, args.video_master, args.output, args.fade_seconds
        ).__dict__
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
