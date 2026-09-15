"""Command-line entry point for delivery normalization and keyframe selection."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from core.media_pipeline import extract_ranked_keyframes, normalize_delivery, probe_as_dict


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

    args = parser.parse_args()
    if args.command == "probe":
        payload = probe_as_dict(args.input)
    elif args.command == "normalize":
        payload = normalize_delivery(args.input, args.output, args.duration, args.fps).__dict__
    else:
        payload = extract_ranked_keyframes(args.input, args.output_dir, args.count, args.sample_fps)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
