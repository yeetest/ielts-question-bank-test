#!/usr/bin/env python3
"""
backfill_content_tags_l3_from_assignment.py

1) When content_tags.l3 is missing or [], append assignment primary.l3 (unchanged).
2) Global legacy pass: append curated YAML spellings for known legacy tokens
   (traveling→travel, learning→learning_growth, decision→decision_making) and
   self_improvement when only hyphenated self-improvement appears — append-only, no deletes.
Does not touch runtime taxonomy JSON.

Typical (after assign):

  python3 pipeline/backfill_content_tags_l3_from_assignment.py --quarter 2026-01-to-04 --dry-run
  python3 pipeline/backfill_content_tags_l3_from_assignment.py --quarter 2026-01-to-04
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent

# Same map as assign_primary_l3_v2.LEGACY_CONTENT_L3_TO_CURATED — append YAML spellings for subset check.
LEGACY_CONTENT_L3_TO_CURATED = {
    "traveling": "travel",
    "learning": "learning_growth",
    "decision": "decision_making",
}


def norm_l3_key(s: str) -> str:
    return str(s or "").strip().lower().replace("-", "_")


def as_l3_list(ct: dict) -> list[str]:
    raw = ct.get("l3")
    if raw is None:
        return []
    if isinstance(raw, list):
        return [str(x).strip() for x in raw if str(x).strip()]
    return [str(raw).strip()] if str(raw).strip() else []


def append_legacy_canonical_l3(ct: dict[str, Any]) -> tuple[list[str], int]:
    """
    Append curated spellings when card uses legacy tokens (e.g. traveling → travel).
    Also append self_improvement when only self-improvement appears. Does not remove entries.
    Returns (log lines, number of appends).
    """
    lst = as_l3_list(ct)
    if not lst:
        return [], 0
    new = list(lst)
    seen = set(new)
    log: list[str] = []
    added = 0
    for raw in lst:
        k = norm_l3_key(raw)
        canon = LEGACY_CONTENT_L3_TO_CURATED.get(k)
        if canon and canon not in seen:
            new.append(canon)
            seen.add(canon)
            added += 1
            log.append(f"LEGACY_CANON append {canon!r} (from {raw!r})")
    if any(norm_l3_key(x) == "self_improvement" for x in new) and "self_improvement" not in new:
        new.append("self_improvement")
        seen.add("self_improvement")
        added += 1
        log.append("LEGACY_CANON append 'self_improvement' (hyphen/alias cluster)")
    if added:
        ct["l3"] = new
    return log, added


def load_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def save_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")


def resolve_path(p: Path) -> Path:
    return p if p.is_absolute() else ROOT / p


def assignment_primary_l3(row: dict) -> str | None:
    prim = (row.get("taxonomy_v2") or {}).get("primary") or {}
    l3 = prim.get("l3")
    if l3 is None:
        return None
    s = str(l3).strip()
    return s if s else None


def needs_l3_backfill(ct: Any) -> bool:
    if not isinstance(ct, dict):
        return False
    l3 = ct.get("l3")
    if l3 is None:
        return True
    if isinstance(l3, list) and len(l3) == 0:
        return True
    return False


def backfill_part(
    topics: list[dict],
    *,
    part: int,
    assign_rows: list[dict],
    dry_run: bool,
) -> dict[str, Any]:
    by_topic: dict[str, dict] = {}
    for row in assign_rows:
        k = (row.get("topic") or "").strip()
        if k:
            by_topic[k] = row

    scanned = 0
    filled = 0
    had_l3_already = 0
    eligible_empty_l3 = 0
    skip_bad_ct = 0
    skip_no_assignment = 0
    skip_assign_l3_empty = 0
    skip_already_present = 0
    log_fill: list[str] = []
    log_skip: list[str] = []

    for topic in topics:
        if part == 2 and topic.get("part") != 2:
            continue
        key = (topic.get("topic_en") if part == 1 else topic.get("topic")) or ""
        key = str(key).strip()
        if not key:
            continue

        scanned += 1
        ct = topic.get("content_tags")
        if not isinstance(ct, dict):
            skip_bad_ct += 1
            log_skip.append(f"SKIP not_object_content_tags part{part} topic={key!r}")
            continue
        if not needs_l3_backfill(ct):
            had_l3_already += 1
            continue

        eligible_empty_l3 += 1
        row = by_topic.get(key)
        if not row:
            skip_no_assignment += 1
            log_skip.append(f"SKIP no_assignment part{part} topic={key!r}")
            continue

        p3 = assignment_primary_l3(row)
        if not p3:
            skip_assign_l3_empty += 1
            log_skip.append(f"SKIP assignment_l3_empty part{part} topic={key!r}")
            continue

        current = as_l3_list(ct)
        if p3 in current:
            skip_already_present += 1
            continue

        new_l3 = current + [p3]
        if not dry_run:
            ct["l3"] = new_l3
        filled += 1
        log_fill.append(f"FILL part{part} topic={key!r} append_l3={p3!r}")

    skipped_total = skip_bad_ct + skip_no_assignment + skip_assign_l3_empty + skip_already_present
    return {
        "scanned": scanned,
        "filled": filled,
        "had_l3_already": had_l3_already,
        "eligible_empty_l3": eligible_empty_l3,
        "skipped_total": skipped_total,
        "skip_bad_ct": skip_bad_ct,
        "skip_no_assignment": skip_no_assignment,
        "skip_assign_l3_empty": skip_assign_l3_empty,
        "skip_already_present": skip_already_present,
        "log_fill": log_fill,
        "log_skip": log_skip,
    }


def run_legacy_canonical_pass(
    topics: list[dict],
    *,
    part: int,
    dry_run: bool,
) -> tuple[int, list[str]]:
    """Append canonical l3 peers for legacy spellings; returns (append_count, log lines)."""
    total = 0
    logs: list[str] = []
    for topic in topics:
        if part == 2 and topic.get("part") != 2:
            continue
        key = (topic.get("topic_en") if part == 1 else topic.get("topic")) or ""
        key = str(key).strip()
        if not key:
            continue
        ct = topic.get("content_tags")
        if not isinstance(ct, dict) or not as_l3_list(ct):
            continue
        if dry_run:
            probe: dict[str, Any] = {"l3": list(as_l3_list(ct))}
            log_lines, n = append_legacy_canonical_l3(probe)
        else:
            log_lines, n = append_legacy_canonical_l3(ct)
        if n:
            total += n
            for line in log_lines:
                logs.append(f"part{part} topic={key!r} {line}")
    return total, logs


def main() -> int:
    ap = argparse.ArgumentParser(description="Backfill content_tags.l3 from assignment primary.l3 when l3 empty.")
    ap.add_argument("--quarter", metavar="ID", help="Use data/quarters/<ID>/merged_*.json and default assignment paths")
    ap.add_argument("--merged-part1", type=Path, default=None)
    ap.add_argument("--merged-part2", type=Path, default=None)
    ap.add_argument("--assignment-p1", type=Path, default=None)
    ap.add_argument("--assignment-p2", type=Path, default=None)
    ap.add_argument("--dry-run", action="store_true", help="Print audit only; do not write merged JSON")
    args = ap.parse_args()

    if args.quarter:
        q = ROOT / "data" / "quarters" / args.quarter
        p1 = resolve_path(args.merged_part1 or (q / "merged_part1.json"))
        p2 = resolve_path(args.merged_part2 or (q / "merged_part2.json"))
        hitl = ROOT / "human-in-the-loop"
        a1 = resolve_path(args.assignment_p1 or (hitl / "topic_taxonomy_assignment_v2_part1.json"))
        a2 = resolve_path(args.assignment_p2 or (hitl / "topic_taxonomy_assignment_v2_part2.json"))
    else:
        if not all([args.merged_part1, args.merged_part2, args.assignment_p1, args.assignment_p2]):
            ap.error("Pass --quarter or all of --merged-part1 --merged-part2 --assignment-p1 --assignment-p2")
        p1 = resolve_path(args.merged_part1)
        p2 = resolve_path(args.merged_part2)
        a1 = resolve_path(args.assignment_p1)
        a2 = resolve_path(args.assignment_p2)

    for label, pp in (
        ("merged_part1", p1),
        ("merged_part2", p2),
        ("assignment_p1", a1),
        ("assignment_p2", a2),
    ):
        if not pp.is_file():
            print(f"ERROR: missing {label}: {pp}", file=sys.stderr)
            return 2

    data_p1 = load_json(p1)
    data_p2 = load_json(p2)
    rows_p1 = load_json(a1)
    rows_p2 = load_json(a2)

    r1 = backfill_part(data_p1, part=1, assign_rows=rows_p1, dry_run=args.dry_run)
    r2 = backfill_part(data_p2, part=2, assign_rows=rows_p2, dry_run=args.dry_run)

    scanned = r1["scanned"] + r2["scanned"]
    filled = r1["filled"] + r2["filled"]
    had_l3 = r1["had_l3_already"] + r2["had_l3_already"]
    elig = r1["eligible_empty_l3"] + r2["eligible_empty_l3"]

    print("=== backfill_content_tags_l3_from_assignment ===")
    print(f"dry_run: {args.dry_run}")
    print(f"merged_part1: {p1}")
    print(f"merged_part2: {p2}")
    print(f"assignment_p1: {a1}")
    print(f"assignment_p2: {a2}")
    print()
    print(f"topics scanned (part1+part2, valid key): {scanned}")
    print(f"already had non-empty l3 (not eligible): {had_l3}")
    print(f"eligible (content_tags.l3 empty): {elig}")
    print(f"backfilled (appended l3): {filled}")
    print(f"skipped among eligible-empty-l3 (no fill): {elig - filled}")
    print("  Part1: bad_ct={} no_assign={} assign_l3_empty={} already_present={}".format(
        r1["skip_bad_ct"], r1["skip_no_assignment"], r1["skip_assign_l3_empty"], r1["skip_already_present"]
    ))
    print("  Part2: bad_ct={} no_assign={} assign_l3_empty={} already_present={}".format(
        r2["skip_bad_ct"], r2["skip_no_assignment"], r2["skip_assign_l3_empty"], r2["skip_already_present"]
    ))
    print()
    for line in r1["log_fill"] + r2["log_fill"]:
        print(line)
    for line in r1["log_skip"] + r2["log_skip"]:
        print(line)

    leg1, log_leg1 = run_legacy_canonical_pass(data_p1, part=1, dry_run=args.dry_run)
    leg2, log_leg2 = run_legacy_canonical_pass(data_p2, part=2, dry_run=args.dry_run)
    legacy_appends = leg1 + leg2
    print()
    print(f"legacy_canonical appends (total tokens added): {legacy_appends}")
    for line in log_leg1 + log_leg2:
        print(line)

    if not args.dry_run and (filled > 0 or legacy_appends > 0):
        save_json(p1, data_p1)
        save_json(p2, data_p2)
        print()
        print(f"Wrote: {p1}")
        print(f"Wrote: {p2}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
