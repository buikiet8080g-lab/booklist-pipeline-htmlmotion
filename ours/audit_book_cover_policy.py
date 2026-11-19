#!/usr/bin/env python3
# 01/06 闸门：书封必须是真实核验资产，禁 model_generated / 禁图片阶段贴图修补（迁移自 booklist-pipeline-Lite）。
from __future__ import annotations

import argparse
import json
from pathlib import Path


FORBIDDEN_KEYS = {
    "cover_composite_required",
    "cover_composite_reason",
    "cover_composite_method",
}
FORBIDDEN_VALUE_MARKERS = (
    "deterministic_flat_cover_composite",
    "book_cover_composite",
    "cover_composite_with",
)


def load_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return None


def truthy(value: object) -> bool:
    if value is True:
        return True
    return str(value or "").strip().lower() in {"true", "yes", "1", "required"}


def walk(value: object, location: str):
    yield location, value
    if isinstance(value, dict):
        for key, item in value.items():
            yield from walk(item, f"{location}.{key}")
    elif isinstance(value, list):
        for index, item in enumerate(value):
            yield from walk(item, f"{location}[{index}]")


def forbidden_composite_reasons(item: dict) -> list[str]:
    reasons = [key for key in FORBIDDEN_KEYS if key in item]
    for key, value in item.items():
        if isinstance(value, (dict, list)):
            continue
        normalized = str(value or "").strip().lower()
        if any(marker in normalized for marker in FORBIDDEN_VALUE_MARKERS):
            reasons.append(key)
    return sorted(set(reasons))


def validate_required_slot(item: dict) -> list[str]:
    missing: list[str] = []
    if not str(item.get("book_cover_reference_asset_id") or "").strip():
        missing.append("book_cover_reference_asset_id")
    references = item.get("reference_images")
    if not isinstance(references, list) or not any(str(value).strip() for value in references):
        missing.append("reference_images")
    if item.get("cover_visibility_qc") != "required_for_book_cover_slots":
        missing.append("cover_visibility_qc")
    if item.get("cover_visibility_qc_status") != "passed":
        missing.append("cover_visibility_qc_status")
    if item.get("book_cover_failure_action") != "regenerate":
        missing.append("book_cover_failure_action")
    return missing


def audit_project(project: Path) -> dict:
    metadata = project / "metadata"
    forbidden: list[dict] = []
    invalid_slots: list[dict] = []
    required_slot_count = 0

    for path in sorted(metadata.rglob("*.json")) if metadata.exists() else []:
        if path.name == "book-cover-policy-audit.json":
            continue
        payload = load_json(path)
        if payload is None:
            continue
        relative = str(path.relative_to(project))
        for location, value in walk(payload, relative):
            if not isinstance(value, dict):
                continue
            reasons = forbidden_composite_reasons(value)
            if reasons:
                forbidden.append({"location": location, "reasons": reasons})
            if truthy(value.get("book_cover_required")):
                required_slot_count += 1
                missing = validate_required_slot(value)
                if missing:
                    invalid_slots.append({"location": location, "missing": missing})

    status = "passed" if not forbidden and not invalid_slots else "failed"
    return {
        "status": status,
        "policy": {
            "source_image_book_cover_composite_forbidden": True,
            "book_cover_failure_action": "regenerate",
            "book_cover_overlay_only_in_07": True,
        },
        "required_slot_count": required_slot_count,
        "invalid_required_slots": invalid_slots,
        "forbidden_composite_count": len(forbidden),
        "forbidden_composites": forbidden,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Audit Lite book-cover generation policy.")
    parser.add_argument("--project-dir", required=True, type=Path)
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("metadata/book-cover-policy-audit.json"),
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    project = args.project_dir.expanduser().resolve()
    result = audit_project(project)
    output = args.out if args.out.is_absolute() else project / args.out
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
