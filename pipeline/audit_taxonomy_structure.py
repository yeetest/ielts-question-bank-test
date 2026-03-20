#!/usr/bin/env python3
"""
audit_taxonomy_structure.py

Structural audit of the 3-level taxonomy (L1 > L2 > L3) defined in
config/topic_taxonomy_v2_curated.yaml and used in merged JSON content_tags.

Checks:
  DUAL_HOME         L3 appears under >1 L2 bucket in YAML (ERROR)
  CROSS_L1          L3 appears under different L1s in YAML (ERROR)
  NAME_COLLISION    L3 name exactly matches an L2 bucket name (ERROR)
  CROSS_PARENT_NAME L3 name contains a non-parent L2 name (WARNING)
  BROAD_L3          L3 name has L2-level breadth patterns (WARNING)
  ORPHAN_CONTENT_L3 L3 in content_tags but absent from YAML (WARNING)
  LEGACY_FORMAT     L3 uses hyphenated format in content_tags (INFO)

Whitelist for intentional dual-homes lives in DUAL_HOME_WHITELIST below.
If a dual-homed L3 is NOT whitelisted, it is flagged as an error.

Usage:
  python3 pipeline/audit_taxonomy_structure.py
  python3 pipeline/audit_taxonomy_structure.py --quarter 2026-01-to-04
  python3 pipeline/audit_taxonomy_structure.py --strict   # exit 1 on any ERROR
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:
    print("ERROR: PyYAML required. pip install pyyaml", file=sys.stderr)
    sys.exit(2)

ROOT = Path(__file__).resolve().parent.parent
YAML_PATH = ROOT / "config" / "topic_taxonomy_v2_curated.yaml"

# Intentional dual-homes (l3 -> frozenset of allowed (l1, l2) pairs).
# Keep empty by default; add entries only after explicit human review.
DUAL_HOME_WHITELIST: dict[str, frozenset[tuple[str, str]]] = {}

# L3 name patterns that suggest L2-level breadth rather than specificity.
_BROAD_SUFFIXES = ("_experience", "_activity", "_growth", "_time")


def load_yaml(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_json(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as f:
        return json.load(f)


class Finding:
    __slots__ = ("severity", "code", "message", "details")

    def __init__(self, severity: str, code: str, message: str, details: str = ""):
        self.severity = severity
        self.code = code
        self.message = message
        self.details = details

    def __str__(self) -> str:
        prefix = f"[{self.severity}] {self.code}: {self.message}"
        return f"{prefix}\n    {self.details}" if self.details else prefix


def audit_yaml(yaml_data: dict[str, Any]) -> tuple[list[Finding], dict[str, list[tuple[str, str]]], set[str]]:
    """Audit the YAML hierarchy. Returns (findings, l3_all_homes, all_l2_set)."""
    findings: list[Finding] = []

    l3_all_homes: dict[str, list[tuple[str, str]]] = defaultdict(list)
    all_l2: set[str] = set()

    l1_block = yaml_data.get("l1", {}) or {}
    for l1_key, l1_val in l1_block.items():
        if not isinstance(l1_val, dict):
            continue
        for l2_key, l2_val in l1_val.items():
            all_l2.add(l2_key)
            if not isinstance(l2_val, dict):
                continue
            for l3_tag in l2_val.get("l3", []) or []:
                l3_all_homes[l3_tag].append((l1_key, l2_key))

    # Check 1: DUAL_HOME
    for l3, homes in sorted(l3_all_homes.items()):
        if len(homes) <= 1:
            continue
        whitelisted = DUAL_HOME_WHITELIST.get(l3)
        if whitelisted and frozenset(homes) == whitelisted:
            findings.append(Finding(
                "INFO", "DUAL_HOME_OK",
                f"l3={l3!r} dual-homed (whitelisted)",
                f"homes: {homes}",
            ))
        else:
            findings.append(Finding(
                "ERROR", "DUAL_HOME",
                f"l3={l3!r} appears under {len(homes)} L2 buckets",
                f"homes: {homes}",
            ))

    # Check 2: CROSS_L1
    for l3, homes in sorted(l3_all_homes.items()):
        l1s = {l1 for l1, _ in homes}
        if len(l1s) > 1:
            findings.append(Finding(
                "ERROR", "CROSS_L1",
                f"l3={l3!r} spans {len(l1s)} different L1 categories",
                f"L1s: {sorted(l1s)}, homes: {homes}",
            ))

    # Check 3: NAME_COLLISION — l3 name == l2 name
    for l3 in sorted(l3_all_homes):
        if l3 in all_l2:
            findings.append(Finding(
                "ERROR", "NAME_COLLISION",
                f"l3={l3!r} has the same name as an L2 bucket",
            ))

    # Check 4: CROSS_PARENT_NAME — l3 name contains a non-parent l2 name
    for l3, homes in sorted(l3_all_homes.items()):
        parent_l2s = {l2 for _, l2 in homes}
        for l2_name in all_l2:
            if l2_name in parent_l2s:
                continue
            if len(l2_name) < 4:
                continue
            if l2_name in l3 and l3 != l2_name:
                findings.append(Finding(
                    "WARNING", "CROSS_PARENT_NAME",
                    f"l3={l3!r} (under {list(parent_l2s)}) contains non-parent L2 name {l2_name!r}",
                ))

    # Check 5: BROAD_L3 — name suggests L2-level breadth
    for l3, homes in sorted(l3_all_homes.items()):
        parent_l2s = [l2 for _, l2 in homes]
        for suffix in _BROAD_SUFFIXES:
            if l3.endswith(suffix):
                stem = l3[: -len(suffix)]
                if stem and stem not in parent_l2s:
                    findings.append(Finding(
                        "WARNING", "BROAD_L3",
                        f"l3={l3!r} ends with {suffix!r}, suggesting L2-level breadth",
                        f"parent L2: {parent_l2s}",
                    ))
                    break

    return findings, dict(l3_all_homes), all_l2


def audit_content_tags(
    data: list[dict[str, Any]],
    part_key: str,
    yaml_l3_set: set[str],
) -> list[Finding]:
    """Audit content_tags.l3 values against YAML-known L3 tags."""
    findings: list[Finding] = []
    seen_orphans: set[str] = set()

    for topic in data:
        ct = topic.get("content_tags")
        if not isinstance(ct, dict):
            continue
        title = str(topic.get(part_key, "?")).strip()
        for l3_raw in ct.get("l3", []) or []:
            l3_raw = str(l3_raw).strip()
            if not l3_raw:
                continue
            canonical = l3_raw.replace("-", "_")

            if "-" in l3_raw and canonical in yaml_l3_set:
                findings.append(Finding(
                    "INFO", "LEGACY_FORMAT",
                    f"l3={l3_raw!r} uses hyphens; canonical={canonical!r}",
                    f"topic: {title}",
                ))
            elif l3_raw not in yaml_l3_set and canonical not in yaml_l3_set:
                if l3_raw not in seen_orphans:
                    seen_orphans.add(l3_raw)
                    findings.append(Finding(
                        "WARNING", "ORPHAN_CONTENT_L3",
                        f"l3={l3_raw!r} in content_tags but not in YAML",
                        f"first seen in: {title}",
                    ))

    return findings


def main() -> int:
    ap = argparse.ArgumentParser(description="Audit taxonomy structure")
    ap.add_argument("--quarter", metavar="ID", help="Quarter to scan content_tags")
    ap.add_argument("--strict", action="store_true", help="Exit 1 on any ERROR finding")
    ap.add_argument("--yaml", type=Path, default=YAML_PATH, help="Path to curated YAML")
    args = ap.parse_args()

    yaml_path = args.yaml if args.yaml.is_absolute() else ROOT / args.yaml
    yaml_data = load_yaml(yaml_path)

    findings, l3_homes, all_l2 = audit_yaml(yaml_data)
    yaml_l3_set = set(l3_homes.keys())

    # Content-tag audit
    if args.quarter:
        qdir = ROOT / "data" / "quarters" / args.quarter
        p1_path = qdir / "merged_part1.json"
        p2_path = qdir / "merged_part2.json"
    else:
        p1_path = ROOT / "merged_part1.json"
        p2_path = ROOT / "merged_part2.json"

    if p1_path.is_file():
        findings.extend(audit_content_tags(load_json(p1_path), "topic_en", yaml_l3_set))
    if p2_path.is_file():
        findings.extend(audit_content_tags(load_json(p2_path), "topic", yaml_l3_set))

    # Summary
    errors = [f for f in findings if f.severity == "ERROR"]
    warnings = [f for f in findings if f.severity == "WARNING"]
    infos = [f for f in findings if f.severity == "INFO"]

    print(f"=== Taxonomy Structure Audit ===")
    print(f"YAML: {yaml_path}")
    print(f"L2 buckets: {len(all_l2)}")
    print(f"L3 tags: {len(yaml_l3_set)}")
    print(f"Findings: {len(errors)} ERROR, {len(warnings)} WARNING, {len(infos)} INFO")
    print()

    for sev, group in [("ERROR", errors), ("WARNING", warnings), ("INFO", infos)]:
        if not group:
            continue
        print(f"--- {sev} ({len(group)}) ---")
        for f in group:
            print(f"  {f}")
        print()

    if args.strict and errors:
        print(f"STRICT: {len(errors)} error(s) found, exiting with code 1.")
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
