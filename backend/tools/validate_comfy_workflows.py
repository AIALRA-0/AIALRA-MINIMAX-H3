"""Validate API-format ComfyUI workflows against a running ComfyUI instance."""

from __future__ import annotations

import argparse
import json
import sys
import urllib.request
from pathlib import Path
from typing import Any


def _fetch_object_info(base_url: str) -> dict[str, Any]:
    with urllib.request.urlopen(f"{base_url.rstrip('/')}/object_info", timeout=30) as response:
        return json.load(response)


def _is_connection(value: Any) -> bool:
    return (
        isinstance(value, list)
        and len(value) == 2
        and isinstance(value[0], str)
        and isinstance(value[1], int)
    )


def _is_template_value(value: Any) -> bool:
    return isinstance(value, str) and (
        "PLACEHOLDER" in value or (value.startswith("{") and value.endswith("}"))
    )


def validate_workflow(path: Path, object_info: dict[str, Any]) -> list[str]:
    workflow = json.loads(path.read_text(encoding="utf-8"))
    errors: list[str] = []
    if not isinstance(workflow, dict) or not workflow:
        return ["workflow must be a non-empty JSON object"]

    output_nodes = 0
    for node_id, node in workflow.items():
        class_type = node.get("class_type")
        inputs = node.get("inputs", {})
        schema = object_info.get(class_type)
        if schema is None:
            errors.append(f"node {node_id}: unknown class_type {class_type!r}")
            continue
        if schema.get("output_node"):
            output_nodes += 1

        declared = schema.get("input", {})
        required = declared.get("required", {})
        optional = declared.get("optional", {})
        for name in required:
            if name not in inputs:
                errors.append(f"node {node_id} ({class_type}): missing required input {name!r}")

        for name, value in inputs.items():
            input_schema = required.get(name) or optional.get(name)
            if input_schema is None or _is_connection(value) or _is_template_value(value):
                continue
            if (
                isinstance(input_schema, list)
                and input_schema
                and isinstance(input_schema[0], list)
                and value not in input_schema[0]
            ):
                errors.append(
                    f"node {node_id} ({class_type}): {name}={value!r} is not an installed option"
                )

        for name, value in inputs.items():
            if not _is_connection(value):
                continue
            source_id = value[0]
            if source_id not in workflow:
                errors.append(f"node {node_id} ({class_type}): input {name!r} references missing node {source_id}")

    if output_nodes == 0:
        errors.append("workflow has no output node")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("workflows", nargs="+", type=Path)
    parser.add_argument("--comfy-url", default="http://127.0.0.1:8188")
    args = parser.parse_args()

    object_info = _fetch_object_info(args.comfy_url)
    failed = False
    for path in args.workflows:
        errors = validate_workflow(path, object_info)
        if errors:
            failed = True
            print(f"[fail] {path}")
            for error in errors:
                print(f"  - {error}")
        else:
            print(f"[ok] {path}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
