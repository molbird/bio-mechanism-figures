"""Validate a mechanism brief and compile an imagegen-ready prompt.

Usage: python prepare_brief.py --input brief.json --out prompt.txt
Exit: 0 = written; 2 = invalid input or I/O error. UTF-8 JSON/text only.
Required top-level strings: objective, audience, layout, evidence_boundary,
output_role. Optional style string replaces the entire default style; optional
constraints is a list of strings. panels is a nonempty list of objects with
id, message, entities, relations, labels, critical_checks. Every entity has
id/label/compartment/appearance strings. Every relation has from/to/kind/meaning/
evidence strings and critical boolean. Endpoints are local to their panel.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from _common import InputError, read_json, safe_id, string_list, text


RELATIONS = {
    "activation": "solid directed arrow from source to target",
    "inhibition": "directed connector ending in a T-bar at the target",
    "transport": "directed movement arrow using the supplied source and target compartments",
    "binding": "physical contact or binding connector; direction only when explicitly supplied",
    "association": "non-directional association connector",
    "hypothesis": "dashed directed connector, visibly marked as proposed",
    "feedback": "returning directed arrow; use the supplied meaning to show its sign",
}
DEFAULT_STYLE = (
    "White background; simple flat biomedical illustration with colored structures. "
    "Default labels are English in black or white for contrast. Supplied exact labels "
    "take priority over the language default."
)


def validate_brief(brief):
    if not isinstance(brief, dict):
        raise InputError("Brief must be a JSON object")
    for field in ("objective", "audience", "layout", "evidence_boundary", "output_role"):
        text(brief.get(field), field)
    if "style" in brief and not isinstance(brief["style"], str):
        raise InputError("style must be a string (empty selects the default)")
    string_list(brief.get("constraints", []), "constraints")
    panels = brief.get("panels")
    if not isinstance(panels, list) or not panels:
        raise InputError("panels must be a nonempty list")
    panel_ids = set()
    for panel in panels:
        if not isinstance(panel, dict):
            raise InputError("Every panel must be an object")
        panel_id = safe_id(panel.get("id"), "panel.id")
        if panel_id.casefold() in panel_ids:
            raise InputError(f"Duplicate panel id: {panel_id}")
        panel_ids.add(panel_id.casefold())
        text(panel.get("message"), f"{panel_id}.message")
        entities = panel.get("entities")
        if not isinstance(entities, list) or not entities:
            raise InputError(f"{panel_id}.entities must be a nonempty list")
        ids = set()
        for entity in entities:
            if not isinstance(entity, dict):
                raise InputError(f"{panel_id}: every entity must be an object")
            entity_id = safe_id(entity.get("id"), "entity.id")
            if entity_id in ids:
                raise InputError(f"{panel_id}: duplicate entity id {entity_id}")
            ids.add(entity_id)
            for field in ("label", "compartment", "appearance"):
                text(entity.get(field), f"{panel_id}.{entity_id}.{field}")
        relations = panel.get("relations")
        if not isinstance(relations, list):
            raise InputError(f"{panel_id}.relations must be a list")
        for relation in relations:
            if not isinstance(relation, dict):
                raise InputError(f"{panel_id}: every relation must be an object")
            for field in ("from", "to", "kind"):
                text(relation.get(field), f"{panel_id}.relation.{field}")
            if relation.get("from") not in ids or relation.get("to") not in ids:
                raise InputError(f"{panel_id}: relation endpoint is not a local entity")
            if relation.get("kind") not in RELATIONS:
                raise InputError(f"{panel_id}: unknown relation kind {relation.get('kind')!r}")
            for field in ("meaning", "evidence"):
                text(relation.get(field), f"{panel_id}.relation.{field}")
            if not isinstance(relation.get("critical"), bool):
                raise InputError(f"{panel_id}.relation.critical must be boolean")
        string_list(panel.get("labels"), f"{panel_id}.labels")
        string_list(panel.get("critical_checks"), f"{panel_id}.critical_checks", nonempty=True)
    return brief


def critical_names(brief):
    return [f"{panel['id']}: {name}" for panel in brief["panels"] for name in panel["critical_checks"]]


def compile_prompt(brief):
    validate_brief(brief)
    lines = [
        f"Create a biomedical mechanism figure. Objective: {brief['objective']}",
        f"Audience: {brief['audience']}",
        f"Composition: {brief['layout']}",
        f"Style: {brief.get('style', '').strip() or DEFAULT_STYLE}",
        f"Output role: {brief['output_role']}",
        f"Evidence boundary: {brief['evidence_boundary']}",
        "Build the figure from the supplied entities, compartments, and relations. "
        "Keep identity, direction, relation type, and evidence status explicit. "
        "Use each exact label as supplied. Exact display labels are the on-figure text; "
        "IDs, messages, evidence descriptions, and checklists guide the drawing rather "
        "than becoming text unless included in those labels.",
    ]
    if len(brief["panels"]) > 1:
        lines.append(
            "Panel markers: unless the supplied brief explicitly specifies another "
            "marker convention, label subpanels with standalone uppercase English "
            "letters A, B, C, ... in reading order (left to right, then top to bottom). "
            "Use black letters alone in consistent positions: no lowercase, numbers, "
            "punctuation, parentheses, prefixes, enclosing circles, boxes or badge "
            "backgrounds. These display markers are separate from internal panel IDs "
            "and from numbered mechanistic steps."
        )
    for panel in brief["panels"]:
        lines.extend(["", f"Panel {panel['id']}: {panel['message']}", "Entities and placement:"])
        for entity in panel["entities"]:
            lines.append(f"- {entity['id']}: label {json.dumps(entity['label'], ensure_ascii=False)}; "
                         f"compartment: {entity['compartment']}; appearance: {entity['appearance']}.")
        lines.append("Relations (source -> target):")
        for relation in panel["relations"]:
            lines.append(f"- {relation['from']} -> {relation['to']}: {relation['kind']} "
                         f"({RELATIONS[relation['kind']]}); meaning: {relation['meaning']}; "
                         f"evidence: {relation['evidence']}; critical: {str(relation['critical']).lower()}.")
        exact = list(dict.fromkeys([item["label"] for item in panel["entities"]] + panel["labels"]))
        lines.append("Exact display labels: " + json.dumps(exact, ensure_ascii=False))
        lines.append("Critical visual checks: " + "; ".join(panel["critical_checks"]))
    if brief.get("constraints"):
        lines.extend(["", "Supplied constraints:"] + [f"- {item}" for item in brief["constraints"]])
    return "\n".join(lines) + "\n"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        prompt = compile_prompt(read_json(args.input))
        if args.out.resolve() == args.input.resolve():
            raise InputError("Output must differ from the input brief")
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(prompt, encoding="utf-8", newline="\n")
    except (InputError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(f"Wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
