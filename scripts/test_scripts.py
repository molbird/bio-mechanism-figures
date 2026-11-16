"""Behavioral tests with tiny deterministic PNG fixtures, never generated art.

Run: python -m unittest discover -s scripts -p test_scripts.py -v
Optional BIO_FIGURE_TEST_TMP selects the temporary test parent directory.
"""

from __future__ import annotations

import contextlib
import copy
import io
import json
import os
import struct
import tempfile
import unittest
import zlib
from pathlib import Path

import prepare_brief
import record_asset
import validate_job
from _common import InputError, read_json, sha256, write_json


def png_fixture(width=3, height=2):
    def chunk(kind, payload):
        return struct.pack("!I", len(payload)) + kind + payload + struct.pack("!I", zlib.crc32(kind + payload))
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack("!IIBBBBB", width, height, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress((b"\0" + b"\xff\xff\xff" * width) * height)) + chunk(b"IEND", b""))


def brief_fixture():
    return {
        "objective": "Show a supplied transport relation", "audience": "Biomedical researchers",
        "layout": "One panel with two explicit neighboring compartments", "style": "",
        "evidence_boundary": "Only the supplied transport is asserted", "output_role": "Draft for visual review",
        "constraints": ["Preserve exact labels"],
        "panels": [{
            "id": "A", "message": "M moves from the extracellular space to the cytosol",
            "entities": [
                {"id": "outside", "label": "M (outside)", "compartment": "extracellular space", "appearance": "blue circle"},
                {"id": "inside", "label": "M (inside)", "compartment": "cytosol", "appearance": "blue circle"}],
            "relations": [{"from": "outside", "to": "inside", "kind": "transport", "meaning": "entry of M",
                           "evidence": "Supplied mechanism", "critical": True}],
            "labels": ["Extracellular", "Cytosol"], "critical_checks": ["M enters the cytosol"]}],
    }


class HelpersTest(unittest.TestCase):
    def setUp(self):
        root = os.environ.get("BIO_FIGURE_TEST_TMP")
        if root:
            Path(root).mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=root)
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.image = self.root / "explicit-test-fixture.png"
        self.image.write_bytes(png_fixture())
        self.brief = self.root / "brief.json"
        write_json(self.brief, brief_fixture())
        self.prompt = self.root / "prompt.txt"
        self.prompt.write_text(prepare_brief.compile_prompt(brief_fixture()), encoding="utf-8", newline="\n")
        self.job = self.root / "job"

    def call(self, function, args):
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            return function(args)

    def record(self, revision=1, figure="example", extra=()):
        return self.call(record_asset.main, ["--job-dir", str(self.job), "--figure-id", figure,
            "--revision", str(revision), "--image", str(self.image), "--prompt", str(self.prompt),
            "--brief", str(self.brief), "--tool", "image_gen.imagegen", *extra])

    def version(self, revision=1):
        return self.job / "assets" / "example" / f"r{revision}"

    def review(self, revision=1, *, status="pass", observation="The arrow visibly enters the explicitly labeled cytosol."):
        manifest = read_json(self.version(revision) / "asset.json")
        result = {
            "image_sha256": manifest["image"]["sha256"],
            "critical_checks": [{"name": name, "status": status, "observation": observation}
                                for name in manifest["required_critical_checks"]],
            "visual_checks": [{"name": "labels", "status": "pass", "observation": "Both supplied M labels are legible at the inspected size."}],
        }
        write_json(self.version(revision) / "review.json", result)
        return result

    def test_compile_preserves_supplied_labels_and_compartments(self):
        output = prepare_brief.compile_prompt(brief_fixture())
        for value in ('"M (outside)"', "extracellular space", "cytosol", "transport", "entry of M"):
            self.assertIn(value, output)
        self.assertNotIn("nucleus", output.casefold())
        self.assertEqual(prepare_brief.compile_prompt(brief_fixture()), output)

    def test_custom_style_replaces_default(self):
        brief = brief_fixture()
        brief["style"] = "Dark background with hand-drawn orange forms and Chinese labels"
        prompt = prepare_brief.compile_prompt(brief)
        self.assertIn(brief["style"], prompt)
        self.assertNotIn(prepare_brief.DEFAULT_STYLE, prompt)

    def test_duplicate_ids_panels_unknown_kind_and_bad_endpoints_rejected(self):
        for modification in ("entity", "panel", "unknown", "endpoint", "endpoint_type", "missing", "traversal"):
            brief = brief_fixture()
            panel = brief["panels"][0]
            if modification == "entity":
                panel["entities"].append(copy.deepcopy(panel["entities"][0]))
            elif modification == "panel":
                brief["panels"].append(copy.deepcopy(panel))
            elif modification == "unknown":
                panel["relations"][0]["kind"] = "magic"
            elif modification == "endpoint":
                panel["relations"][0]["to"] = "missing"
            elif modification == "endpoint_type":
                panel["relations"][0]["from"] = []
            elif modification == "missing":
                del brief["evidence_boundary"]
            else:
                panel["id"] = "../escape"
            with self.subTest(modification=modification), self.assertRaises(InputError):
                prepare_brief.validate_brief(brief)

    def test_duplicate_json_keys_rejected(self):
        self.brief.write_text('{"objective":"one","objective":"two"}', encoding="utf-8")
        with self.assertRaises(InputError):
            read_json(self.brief)

    def test_prepare_cli_and_no_input_overwrite(self):
        output = self.root / "compiled.txt"
        self.assertEqual(self.call(prepare_brief.main, ["--input", str(self.brief), "--out", str(output)]), 0)
        self.assertEqual(output.read_text(encoding="utf-8"), self.prompt.read_text(encoding="utf-8"))
        original = self.brief.read_bytes()
        self.assertEqual(self.call(prepare_brief.main, ["--input", str(self.brief), "--out", str(self.brief)]), 2)
        self.assertEqual(self.brief.read_bytes(), original)

    def test_record_byte_identical_png_and_unknown_model(self):
        before = self.image.read_bytes()
        self.assertEqual(self.record(), 0)
        manifest = read_json(self.version() / "asset.json")
        self.assertEqual((manifest["image"]["width"], manifest["image"]["height"]), (3, 2))
        self.assertEqual(manifest["image"]["sha256"], sha256(self.image))
        self.assertEqual((self.version() / "image.png").read_bytes(), before)
        self.assertEqual((self.version() / "prompt.txt").read_bytes(), self.prompt.read_bytes())
        self.assertEqual(manifest["model"], "unknown")
        self.assertEqual(manifest["provider"], "unknown")

    def test_existing_revision_never_overwritten(self):
        self.assertEqual(self.record(), 0)
        saved = (self.version() / "image.png").read_bytes()
        self.image.write_bytes(png_fixture(4, 5))
        self.assertEqual(self.record(), 2)
        self.assertEqual((self.version() / "image.png").read_bytes(), saved)

    def test_traversal_figure_ids_rejected(self):
        for figure in ("../escape", "..\\escape", "/escape", "C:escape", "CON"):
            with self.subTest(figure=figure):
                self.assertEqual(self.record(figure=figure), 2)
        self.assertFalse(self.job.exists())

    def test_unreviewed_stays_pending_even_in_provenance_stage(self):
        self.assertEqual(self.record(), 0)
        report, code = validate_job.validate_job(self.job)
        self.assertEqual((report["status"], code), ("needs_visual_review", 1))
        report, code = validate_job.validate_job(self.job, "provenance")
        self.assertEqual((report["status"], code), ("needs_visual_review", 0))
        self.assertFalse(report["semantics_verified_by_script"])

    def test_hash_bound_observations_can_record_approval(self):
        self.assertEqual(self.record(), 0)
        self.review()
        report, code = validate_job.validate_job(self.job)
        self.assertEqual((report["status"], code), ("approved", 0))
        self.assertFalse(report["semantics_verified_by_script"])

    def test_changed_image_bytes_are_rejected(self):
        self.assertEqual(self.record(), 0)
        self.review()
        with (self.version() / "image.png").open("ab") as handle:
            handle.write(b"changed")
        report, code = validate_job.validate_job(self.job)
        self.assertEqual(code, 2)
        self.assertTrue(any("Hash/size mismatch" in value for value in report["errors"]))

    def test_stale_review_hash_is_rejected(self):
        self.assertEqual(self.record(), 0)
        review = self.review()
        review["image_sha256"] = "0" * 64
        write_json(self.version() / "review.json", review)
        self.assertEqual(validate_job.validate_job(self.job)[1], 2)

    def test_empty_all_pass_and_invalid_review_are_rejected(self):
        self.assertEqual(self.record(), 0)
        for mutation in ("empty", "generic", "status", "missing", "duplicate"):
            review = self.review()
            if mutation in ("empty", "generic"):
                review["critical_checks"][0]["observation"] = " " if mutation == "empty" else "pass"
            elif mutation == "status":
                review["critical_checks"][0]["status"] = "probably"
            elif mutation == "missing":
                review["critical_checks"][0]["name"] = "An unrelated check"
            else:
                review["critical_checks"].append(copy.deepcopy(review["critical_checks"][0]))
            write_json(self.version() / "review.json", review)
            with self.subTest(mutation=mutation):
                self.assertEqual(validate_job.validate_job(self.job)[1], 2)

    def test_failed_or_unassessable_checks_block_approval(self):
        self.assertEqual(self.record(), 0)
        for status in ("fail", "not_assessable"):
            self.review(status=status, observation="The destination is obscured and cannot be assessed.")
            report, code = validate_job.validate_job(self.job)
            self.assertEqual((report["status"], code), ("blocked", 1))

    def test_manifest_path_traversal_rejected(self):
        self.assertEqual(self.record(), 0)
        manifest = read_json(self.version() / "asset.json")
        for path in ("../prompt.txt", "..\\prompt.txt", "C:\\outside.txt", "/outside.txt"):
            manifest["prompt"]["path"] = path
            write_json(self.version() / "asset.json", manifest)
            with self.subTest(path=path):
                self.assertEqual(validate_job.validate_job(self.job)[1], 2)

    def test_reference_and_exact_original_request_preserved(self):
        original = self.root / "request.json"
        original.write_text(json.dumps({"prompt": self.prompt.read_text(encoding="utf-8"),
                            "transparent_background": False}, ensure_ascii=False), encoding="utf-8")
        self.assertEqual(self.record(extra=["--reference", str(self.image), "--request", str(original)]), 0)
        manifest = read_json(self.version() / "asset.json")
        self.assertEqual(manifest["references"][0]["sha256"], sha256(self.image))
        self.assertEqual((self.version() / "tool-request.json").read_bytes(), original.read_bytes())
        self.assertEqual(validate_job.validate_job(self.job, "provenance")[1], 0)

    def test_exact_prompt_preserves_crlf_and_unicode(self):
        exact = "Supplied label: β-catenin\r\nSupplied layout: 左侧\r\n"
        self.prompt.write_bytes(exact.encode("utf-8"))
        original = self.root / "request.json"
        write_json(original, {"prompt": exact})
        self.assertEqual(self.record(extra=["--request", str(original)]), 0)
        self.assertEqual((self.version() / "prompt.txt").read_bytes(), exact.encode("utf-8"))
        self.assertEqual(read_json(self.version() / "request.json")["prompt"], exact)
        self.assertEqual(validate_job.validate_job(self.job, "provenance")[1], 0)

    def test_missing_prompt_is_an_integrity_error(self):
        self.assertEqual(self.record(), 0)
        (self.version() / "prompt.txt").unlink()
        report, code = validate_job.validate_job(self.job, "provenance")
        self.assertEqual(code, 2)
        self.assertTrue(any("Missing prompt" in value for value in report["errors"]))

    def test_mismatched_original_request_rejected_without_partial_version(self):
        original = self.root / "request.json"
        write_json(original, {"prompt": "different prompt"})
        self.assertEqual(self.record(extra=["--request", str(original)]), 2)
        self.assertFalse(self.version().exists())

    def test_latest_revision_controls_approval_but_all_bytes_are_checked(self):
        self.assertEqual(self.record(), 0)
        self.review(status="fail", observation="The first draft has the direction reversed.")
        self.assertEqual(self.record(revision=2), 0)
        self.review(revision=2)
        self.assertEqual(validate_job.validate_job(self.job)[1], 0)
        (self.version() / "prompt.txt").write_text("Changed historical prompt", encoding="utf-8")
        self.assertEqual(validate_job.validate_job(self.job)[1], 2)

    def test_report_cannot_overwrite_recorded_assets(self):
        self.assertEqual(self.record(), 0)
        image = self.version() / "image.png"
        before = image.read_bytes()
        self.assertEqual(self.call(validate_job.main, ["--job-dir", str(self.job), "--report", str(image)]), 2)
        self.assertEqual(image.read_bytes(), before)
        self.assertEqual(self.call(validate_job.main, ["--job-dir", str(self.job), "--stage", "provenance"]), 0)
        self.assertTrue((self.job / "validation-report.json").is_file())


if __name__ == "__main__":
    unittest.main()
