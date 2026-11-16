"""Copy an explicit tool-output image into an immutable revision directory.

Usage: python record_asset.py --job-dir JOB --figure-id FIG --revision 1
  --image TOOL_OUTPUT.png --prompt prompt.txt --tool image_gen.imagegen
  [--brief brief.json] [--reference ref.png (repeatable)] [--request tool-request.json]
  [--provider REPORTED_PROVIDER] [--model REPORTED_MODEL]
Writes JOB/assets/FIG/r1/{image.*,prompt.txt,asset.json,request.json,...}.
--request preserves a supplied original JSON tool request byte for byte; its
prompt must equal --prompt. Without it, request.json documents only caller-
declared recorder inputs. A CLI tool name does not prove the tool was executed.
Omitted provider/model remain "unknown". Exit: 0 = recorded; 2 = rejected.
Requires Pillow. No image modification, network access, or generation occurs.
"""

from __future__ import annotations

import argparse
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

from _common import InputError, copy_record, image_info, read_json, safe_id, text, within, write_json
from prepare_brief import critical_names, validate_brief


def record(args):
    safe_id(args.figure_id, "figure-id")
    if args.revision < 1:
        raise InputError("revision must be a positive integer")
    prompt_text = args.prompt.read_bytes().decode("utf-8")
    text(prompt_text, "prompt")
    info = image_info(args.image)
    suffixes = {"PNG": ".png", "JPEG": ".jpg", "WEBP": ".webp", "TIFF": ".tif", "BMP": ".bmp"}
    if info["format"] not in suffixes:
        raise InputError(f"Unsupported still-image format: {info['format']}")
    brief = validate_brief(read_json(args.brief)) if args.brief else None
    if args.request:
        original_request = read_json(args.request)
        if not isinstance(original_request, dict) or original_request.get("prompt") != prompt_text:
            raise InputError("The original tool-request JSON prompt must exactly match --prompt")
    for reference in args.reference:
        image_info(reference)
    job_dir = args.job_dir.resolve()
    job_dir.mkdir(parents=True, exist_ok=True)
    version_dir = within(job_dir, f"assets/{args.figure_id}/r{args.revision}")
    version_dir.parent.mkdir(parents=True, exist_ok=True)
    try:
        version_dir.mkdir()
    except FileExistsError as exc:
        raise InputError("Revision already exists; use a new revision number") from exc
    try:
        image_record = copy_record(args.image, version_dir, "image" + suffixes[info["format"]], image=True)
        prompt_record = copy_record(args.prompt, version_dir, "prompt.txt")
        brief_record = copy_record(args.brief, version_dir, "brief.json") if args.brief else None
        references = []
        for number, source in enumerate(args.reference, start=1):
            extension = suffixes.get(image_info(source)["format"], ".img")
            item = copy_record(source, version_dir, f"references/{number:02d}{extension}", image=True)
            item["source_name"] = source.name
            references.append(item)
        original = copy_record(args.request, version_dir, "tool-request.json") if args.request else None
        request = {
            "schema_version": 1,
            "record_scope": "caller_declared_recorder_inputs",
            "tool": args.tool,
            "provider": args.provider or "unknown",
            "model": args.model or "unknown",
            "prompt": prompt_text,
            "references": [{"path": ref["path"], "sha256": ref["sha256"]} for ref in references],
            "original_tool_request": original,
            "provenance_note": "The caller supplied this image as tool output; this recorder does not verify tool execution.",
        }
        write_json(version_dir / "request.json", request, exclusive=True)
        from _common import file_record
        asset = {
            "schema_version": 1,
            "figure_id": args.figure_id,
            "revision": args.revision,
            "created_utc": datetime.now(timezone.utc).isoformat(),
            "tool": args.tool,
            "provider": args.provider or "unknown",
            "model": args.model or "unknown",
            "image": image_record,
            "prompt": prompt_record,
            "brief": brief_record,
            "references": references,
            "request": file_record(version_dir / "request.json", "request.json"),
            "original_tool_request": original,
            "required_critical_checks": critical_names(brief) if brief else [],
            "semantic_validation": "not_performed; add hash-bound review.json after inspecting the image",
        }
        write_json(version_dir / "asset.json", asset, exclusive=True)
    except Exception:
        # This is solely the new directory created by this invocation.
        shutil.rmtree(version_dir)
        raise
    return version_dir


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--job-dir", required=True, type=Path)
    parser.add_argument("--figure-id", required=True)
    parser.add_argument("--revision", required=True, type=int)
    parser.add_argument("--image", required=True, type=Path, help="explicit local tool-output image")
    parser.add_argument("--prompt", required=True, type=Path)
    parser.add_argument("--tool", required=True, choices=["image_gen.imagegen"])
    parser.add_argument("--brief", type=Path)
    parser.add_argument("--reference", action="append", type=Path, default=[], help="repeat for multiple references")
    parser.add_argument("--request", type=Path, help="optional exact original tool-argument JSON")
    parser.add_argument("--provider")
    parser.add_argument("--model")
    args = parser.parse_args(argv)
    try:
        if args.provider is not None:
            text(args.provider, "provider")
        if args.model is not None:
            text(args.model, "model")
        directory = record(args)
    except (InputError, OSError, UnicodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(f"Recorded {directory}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
