#!/usr/bin/env python3
"""
check_taxonomy_runtime_consistency.py

Pre-release check: merged Part 1/2 topics vs data/quarters/<Q>/topic_taxonomy_v2_final.json
coverage, plus optional content_tags vs taxonomy primary mismatch report.

Does not modify any files.

  python3 pipeline/check_taxonomy_runtime_consistency.py --quarter 2026-01-to-04
  python3 pipeline/check_taxonomy_runtime_consistency.py --quarter 2026-01-to-04 --strict
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


def norm_l1(s: str) -> str:
    return (s or "").strip().replace("/", "_")


def as_list(x) -> list[str]:
    if x is None:
        return []
    if isinstance(x, list):
        return [str(v).strip() for v in x if str(v).strip()]
    return [str(x).strip()] if str(x).strip() else []


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--quarter", required=True, metavar="ID", help="e.g. 2026-01-to-04")
    ap.add_argument(
        "--strict",
        action="store_true",
        help="Exit 1 if any merged topic lacks a taxonomy row or has empty taxonomy l1",
    )
    args = ap.parse_args()

    base = ROOT / "data" / "quarters" / args.quarter
    p1_path = base / "merged_part1.json"
    p2_path = base / "merged_part2.json"
    tax_path = base / "topic_taxonomy_v2_final.json"

    for p in (p1_path, p2_path, tax_path):
        if not p.is_file():
            print(f"ERROR: missing file {p}", file=sys.stderr)
            return 2

    p1 = json.loads(p1_path.read_text(encoding="utf-8"))
    p2 = json.loads(p2_path.read_text(encoding="utf-8"))
    tax_rows = json.loads(tax_path.read_text(encoding="utf-8"))
    tax_map = {(r.get("topic") or "").strip(): r for r in tax_rows}

    missing: list[str] = []
    empty_l1: list[str] = []

    for t in p1:
        k = (t.get("topic_en") or "").strip()
        if not k:
            continue
        row = tax_map.get(k)
        if row is None:
            missing.append(f"Part1: {k}")
        elif not str(row.get("l1") or "").strip():
            empty_l1.append(f"Part1: {k}")

    for t in p2:
        if t.get("part") != 2:
            continue
        k = (t.get("topic") or "").strip()
        if not k:
            continue
        row = tax_map.get(k)
        if row is None:
            missing.append(f"Part2: {k}")
        elif not str(row.get("l1") or "").strip():
            empty_l1.append(f"Part2: {k}")

    mismatch_layers = 0
    for t in p2:
        if t.get("part") != 2:
            continue
        k = (t.get("topic") or "").strip()
        row = tax_map.get(k)
        if not row:
            continue
        ct = t.get("content_tags") or {}
        if isinstance(ct, list):
            continue
        ct_l1 = norm_l1(str(ct.get("l1") or ""))
        ct_l2 = as_list(ct.get("l2"))
        ct_l3 = as_list(ct.get("l3"))
        t_l1 = norm_l1(str(row.get("l1") or ""))
        t_l2 = str(row.get("l2") or "").strip()
        t_l3 = str(row.get("l3") or "").strip()
        bad = False
        if t_l1 != ct_l1:
            bad = True
        if t_l2 and t_l2 not in ct_l2:
            bad = True
        if t_l3 and t_l3 not in ct_l3:
            bad = True
        if bad:
            mismatch_layers += 1

    print(f"Quarter: {args.quarter}")
    print(f"Taxonomy rows: {len(tax_rows)}")
    print(f"Merged topics missing taxonomy row: {len(missing)}")
    print(f"Taxonomy rows with empty l1: {len(empty_l1)}")
    print(f"Part2 topics with content_tags vs taxonomy primary mismatch (strict subset rule): {mismatch_layers}")
    if missing[:10]:
        for m in missing[:10]:
            print(f"  - {m}")
        if len(missing) > 10:
            print(f"  ... and {len(missing) - 10} more")
    if empty_l1[:5]:
        for m in empty_l1[:5]:
            print(f"  empty l1: {m}")

    if args.strict and (missing or empty_l1):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
