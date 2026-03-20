#!/usr/bin/env python3
"""
export_runtime_taxonomy_v2.py

Deterministic export: assignment JSON (Part 1 + Part 2) → flat runtime taxonomy
consumed by js/data.js as topic_taxonomy_v2_final.json.

Does not read or modify merged_part*.json.

Typical usage after assign_primary_l3_v2.py:

  python3 pipeline/export_runtime_taxonomy_v2.py --quarter 2026-01-to-04

Or explicit paths:

  python3 pipeline/export_runtime_taxonomy_v2.py \\
    --assignment-p1 human-in-the-loop/topic_taxonomy_assignment_v2_part1.json \\
    --assignment-p2 human-in-the-loop/topic_taxonomy_assignment_v2_part2.json \\
    --out data/quarters/2026-01-to-04/topic_taxonomy_v2_final.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


def load_rows(path: Path) -> list[dict]:
    if not path.is_file():
        raise FileNotFoundError(f"Assignment file not found: {path}")
    with path.open(encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError(f"Expected JSON array in {path}")
    return data


def flatten_assignment_row(row: dict) -> dict:
    topic = (row.get("topic") or "").strip()
    prim = (row.get("taxonomy_v2") or {}).get("primary") or {}
    l1 = prim.get("l1")
    l2 = prim.get("l2")
    l3 = prim.get("l3")
    return {
        "topic": topic,
        "l1": l1 if l1 is not None else "",
        "l2": l2 if l2 is not None else "",
        "l3": l3 if l3 is not None else "",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Export flat topic_taxonomy_v2_final.json from assignment outputs.")
    ap.add_argument(
        "--quarter",
        metavar="ID",
        help="e.g. 2026-01-to-04 — sets default assignment paths under human-in-the-loop/ and "
        "output to data/quarters/<ID>/topic_taxonomy_v2_final.json",
    )
    ap.add_argument("--assignment-p1", type=Path, help="topic_taxonomy_assignment_v2_part1.json")
    ap.add_argument("--assignment-p2", type=Path, help="topic_taxonomy_assignment_v2_part2.json")
    ap.add_argument("--out", type=Path, help="Output path (flat taxonomy JSON)")
    args = ap.parse_args()

    if args.quarter:
        hitl = ROOT / "human-in-the-loop"
        p1 = args.assignment_p1 or (hitl / "topic_taxonomy_assignment_v2_part1.json")
        p2 = args.assignment_p2 or (hitl / "topic_taxonomy_assignment_v2_part2.json")
        out = args.out or (ROOT / "data" / "quarters" / args.quarter / "topic_taxonomy_v2_final.json")
    else:
        if not args.assignment_p1 or not args.assignment_p2 or not args.out:
            ap.error("Without --quarter, require --assignment-p1, --assignment-p2, and --out")
        p1 = args.assignment_p1
        p2 = args.assignment_p2
        out = args.out

    p1 = p1 if p1.is_absolute() else ROOT / p1
    p2 = p2 if p2.is_absolute() else ROOT / p2
    out = out if out.is_absolute() else ROOT / out

    rows_p1 = load_rows(p1)
    rows_p2 = load_rows(p2)

    flat: list[dict] = []
    seen: set[str] = set()

    for row in rows_p1:
        rec = flatten_assignment_row(row)
        if not rec["topic"]:
            print("warning: skipping Part 1 row with empty topic", file=sys.stderr)
            continue
        if rec["topic"] in seen:
            print(f"warning: duplicate topic key after Part 1: {rec['topic']!r}", file=sys.stderr)
        seen.add(rec["topic"])
        flat.append(rec)

    for row in rows_p2:
        rec = flatten_assignment_row(row)
        if not rec["topic"]:
            print("warning: skipping Part 2 row with empty topic", file=sys.stderr)
            continue
        if rec["topic"] in seen:
            print(f"warning: duplicate topic key (Part 2 collides): {rec['topic']!r}", file=sys.stderr)
        seen.add(rec["topic"])
        flat.append(rec)

    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as f:
        json.dump(flat, f, ensure_ascii=False, indent=2)
        f.write("\n")

    print(f"Wrote {len(flat)} rows to {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
