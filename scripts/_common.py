"""Small shared I/O helpers; no generation, editing, or network operations."""

from __future__ import annotations

import hashlib
import json
import re
import shutil
from pathlib import Path, PurePosixPath


class InputError(ValueError):
    """Invalid user input or a broken recorded artifact."""


def _unique_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise InputError(f"Duplicate JSON key: {key}")
        result[key] = value
    return result


def read_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"), object_pairs_hook=_unique_pairs)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise InputError(f"Cannot read JSON {path.name}: {exc}") from exc


def write_json(path: Path, value, *, exclusive=False):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x" if exclusive else "w", encoding="utf-8", newline="\n") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def text(value, name):
    if not isinstance(value, str) or not value.strip():
        raise InputError(f"{name} must be a nonempty string")
    return value


def string_list(value, name, *, nonempty=False):
    if not isinstance(value, list) or (nonempty and not value):
        raise InputError(f"{name} must be {'a nonempty' if nonempty else 'a'} list of strings")
    for item in value:
        text(item, name)
    if len(set(value)) != len(value):
        raise InputError(f"{name} contains duplicate strings")
    return value


def safe_id(value, name="id"):
    text(value, name)
    reserved = {"CON", "PRN", "AUX", "NUL", *[f"COM{i}" for i in range(1, 10)],
                *[f"LPT{i}" for i in range(1, 10)]}
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", value) or value.upper() in reserved:
        raise InputError(f"{name} must be a safe 1-64 character ASCII identifier")
    return value


def within(root: Path, relative: str) -> Path:
    """Resolve a recorded relative path without traversal or linked descendants."""
    text(relative, "recorded path")
    normalized = relative.replace("\\", "/")
    parts = PurePosixPath(normalized).parts
    if ":" in normalized or not parts or normalized.startswith("/") or any(
            part in {".", ".."} for part in parts):
        raise InputError(f"Unsafe recorded path: {relative}")
    root = root.resolve()
    candidate = root.joinpath(*parts)
    cursor = root
    for part in parts:
        cursor = cursor / part
        if cursor.is_symlink():
            raise InputError(f"Linked descendant is not allowed: {relative}")
    try:
        candidate.resolve().relative_to(root)
    except ValueError as exc:
        raise InputError(f"Path leaves its owning directory: {relative}") from exc
    return candidate


def sha256(path: Path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def image_info(path: Path):
    from PIL import Image

    try:
        with Image.open(path) as picture:
            result = {"width": picture.width, "height": picture.height, "format": picture.format}
            if getattr(picture, "n_frames", 1) != 1:
                raise InputError("Only a single still image can be recorded")
            picture.verify()
    except (OSError, ValueError, Image.DecompressionBombError) as exc:
        raise InputError(f"Cannot read image {path.name}: {exc}") from exc
    return result


def file_record(path: Path, relative: str):
    return {"path": relative, "sha256": sha256(path), "bytes": path.stat().st_size}


def copy_record(source: Path, version_dir: Path, relative: str, *, image=False):
    target = within(version_dir, relative)
    target.parent.mkdir(parents=True, exist_ok=True)
    with source.open("rb") as reader, target.open("xb") as writer:
        shutil.copyfileobj(reader, writer)
    result = file_record(target, relative)
    if image:
        result.update(image_info(target))
    return result


def check_file(version_dir: Path, record, name, *, image=False):
    if not isinstance(record, dict):
        raise InputError(f"{name} must be a file record")
    path = within(version_dir, record.get("path"))
    if not path.is_file():
        raise InputError(f"Missing {name}: {record.get('path')}")
    if not re.fullmatch(r"[0-9a-f]{64}", str(record.get("sha256", ""))):
        raise InputError(f"Invalid SHA-256 in {name}")
    if sha256(path) != record["sha256"] or path.stat().st_size != record.get("bytes"):
        raise InputError(f"Hash/size mismatch in {name}: {record['path']}")
    if image:
        actual = image_info(path)
        if any(record.get(key) != value for key, value in actual.items()):
            raise InputError(f"Image dimensions/format mismatch in {name}")
    return path
