"""Verify recorded bytes and hash-bound review assertions, without judging pixels.

Usage: python validate_job.py --job-dir JOB [--report REPORT.json]
  [--stage approval|provenance]
Default report: JOB/validation-report.json. Every recorded version's integrity
is checked; the newest revision of each figure determines approval readiness.
An optional review.json lives next to asset.json and has image_sha256 plus
critical_checks and visual_checks lists. Each check has a unique name, status
(pass/fail/not_assessable), and a nonempty observation. Critical check names
from a brief are "<panel-id>: <critical_checks entry>". Both lists must contain
at least one check; every supplied critical check must be covered. All checks
must pass for approval. Observations are reviewer assertions, not independent
semantic verification. Missing review always stays needs_visual_review.
Exit: 0 = selected stage passes; 1 = approval still needs review or is blocked;
2 = missing artifacts, unsafe paths, invalid records/review, or altered bytes.
--stage provenance permits unreviewed images, without approving them.
Requires Pillow. This command never rewrites artifacts or review files.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from _common import InputError, check_file, read_json, safe_id, string_list, text, within, write_json
from prepare_brief import critical_names, validate_brief


def evaluate_review(version_dir, image_hash, required):
    review_path = within(version_dir, "review.json")
    if not review_path.exists():
        return {"status": "needs_visual_review", "review": None}
    review = read_json(review_path)
    if not isinstance(review, dict) or review.get("image_sha256") != image_hash:
        raise InputError("Review must be bound to the current image_sha256")
    checks = {}
    for group in ("critical_checks", "visual_checks"):
        entries = review.get(group)
        if not isinstance(entries, list) or not entries:
            raise InputError(f"review.{group} must be a nonempty list")
        names = set()
        for item in entries:
            if not isinstance(item, dict):
                raise InputError(f"review.{group}: every check must be an object")
            name = text(item.get("name"), "review check name")
            if name in names:
                raise InputError(f"Duplicate review check name: {name}")
            names.add(name)
            if item.get("status") not in ("pass", "fail", "not_assessable"):
                raise InputError(f"Invalid review status for {name}")
            observation = text(item.get("observation"), f"Observation for {name}")
            if observation.strip().casefold() in {"pass", "fail", "ok", "n/a", "na", "none", "..."}:
                raise InputError(f"Record an actual visual observation for {name}")
        checks[group] = entries
    observed = {item["name"] for item in checks["critical_checks"]}
    missing = set(required) - observed
    if missing:
        raise InputError("Missing required critical checks: " + "; ".join(sorted(missing)))
    blocked = [item["name"] for entries in checks.values() for item in entries if item["status"] != "pass"]
    return {"status": "blocked" if blocked else "approved", "review": "review.json", "blocking_checks": blocked}


def validate_version(version_dir, figure_id, revision):
    manifest = read_json(within(version_dir, "asset.json"))
    if not isinstance(manifest, dict) or manifest.get("schema_version") != 1:
        raise InputError("asset.json must use schema_version 1")
    if manifest.get("figure_id") != figure_id or manifest.get("revision") != revision:
        raise InputError("Asset identity does not match its owning directory")
    if manifest.get("tool") != "image_gen.imagegen":
        raise InputError("Unrecognized recorded tool")
    for key in ("provider", "model"):
        text(manifest.get(key), key)
    image_path = check_file(version_dir, manifest.get("image"), "image", image=True)
    prompt_path = check_file(version_dir, manifest.get("prompt"), "prompt")
    prompt = prompt_path.read_bytes().decode("utf-8")
    text(prompt, "prompt")
    request_path = check_file(version_dir, manifest.get("request"), "request")
    request = read_json(request_path)
    if not isinstance(request, dict) or request.get("schema_version") != 1:
        raise InputError("Invalid request record")
    if request.get("record_scope") != "caller_declared_recorder_inputs":
        raise InputError("Unrecognized request provenance scope")
    for key in ("tool", "provider", "model"):
        if request.get(key) != manifest[key]:
            raise InputError(f"Request/manifest {key} mismatch")
    if request.get("prompt") != prompt:
        raise InputError("The request does not contain the exact stored prompt")
    references = manifest.get("references")
    if not isinstance(references, list):
        raise InputError("references must be a list")
    for number, item in enumerate(references, start=1):
        check_file(version_dir, item, f"reference {number}", image=True)
    if request.get("references") != [{"path": item["path"], "sha256": item["sha256"]} for item in references]:
        raise InputError("Request/manifest reference mismatch")
    original = manifest.get("original_tool_request")
    if request.get("original_tool_request") != original:
        raise InputError("Original request provenance mismatch")
    if original is not None:
        original_request = read_json(check_file(version_dir, original, "original tool request"))
        if not isinstance(original_request, dict) or original_request.get("prompt") != prompt:
            raise InputError("Original tool-request prompt mismatch")
    required = string_list(manifest.get("required_critical_checks"), "required_critical_checks")
    if manifest.get("brief") is not None:
        brief = validate_brief(read_json(check_file(version_dir, manifest["brief"], "brief")))
        if required != critical_names(brief):
            raise InputError("Required critical checks differ from the recorded brief")
    elif required:
        raise InputError("Critical check names require the recorded source brief")
    result = {"figure_id": figure_id, "revision": revision, "image_sha256": manifest["image"]["sha256"],
              "image": image_path.name, "integrity": "valid"}
    result.update(evaluate_review(version_dir, result["image_sha256"], required))
    return result


def validate_job(job_dir, stage="approval"):
    job_dir = job_dir.resolve()
    results, errors = [], []
    try:
        assets = within(job_dir, "assets")
        if not assets.is_dir():
            raise InputError("No assets directory was recorded")
        for figure in sorted(assets.iterdir()):
            figure_id = safe_id(figure.name, "recorded figure-id")
            figure = within(job_dir, f"assets/{figure_id}")
            if not figure.is_dir():
                raise InputError(f"Expected a figure directory: {figure_id}")
            for version in sorted(figure.iterdir()):
                match = re.fullmatch(r"r([1-9][0-9]*)", version.name)
                if not match:
                    raise InputError(f"Unexpected version entry: {figure_id}/{version.name}")
                version = within(job_dir, f"assets/{figure_id}/{version.name}")
                revision = int(match.group(1))
                try:
                    results.append(validate_version(version, figure_id, revision))
                except (InputError, OSError, UnicodeError) as exc:
                    results.append({"figure_id": figure_id, "revision": revision, "status": "invalid", "integrity": "invalid"})
                    errors.append(f"{figure_id}/r{revision}: {exc}")
        if not results:
            raise InputError("No recorded versions found")
    except (InputError, OSError) as exc:
        errors.append(str(exc))
    latest = {}
    for result in results:
        key = result["figure_id"]
        if key not in latest or result["revision"] > latest[key]["revision"]:
            latest[key] = result
    statuses = {value["status"] for value in latest.values()}
    if errors:
        status, code = "invalid", 2
    elif statuses == {"approved"}:
        status, code = "approved", 0
    else:
        status = "blocked" if "blocked" in statuses else "needs_visual_review"
        code = 0 if stage == "provenance" else 1
    report = {
        "schema_version": 1, "stage": stage, "stage_passed": code == 0, "status": status,
        "semantics_verified_by_script": False,
        "review_scope": "Approval reflects recorded visual observations; this script checks records and bytes, not biological correctness.",
        "versions": results,
        "latest": {key: {"revision": value["revision"], "status": value["status"]} for key, value in latest.items()},
        "errors": errors,
    }
    return report, code


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--job-dir", required=True, type=Path)
    parser.add_argument("--report", type=Path, help="default: JOB/validation-report.json; must be outside assets/")
    parser.add_argument("--stage", choices=["approval", "provenance"], default="approval")
    args = parser.parse_args(argv)
    try:
        report_path = (args.report or args.job_dir / "validation-report.json").resolve()
        assets = (args.job_dir.resolve() / "assets").resolve()
        if report_path == assets or assets in report_path.parents:
            raise InputError("The report must be outside assets/ to preserve recorded versions")
        report, code = validate_job(args.job_dir, args.stage)
        write_json(report_path, report)
    except (InputError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(json.dumps({"report": str(report_path), "status": report["status"], "stage_passed": report["stage_passed"]}))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
