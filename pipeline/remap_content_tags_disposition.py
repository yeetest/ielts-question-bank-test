#!/usr/bin/env python3
"""
remap_content_tags_disposition.py

Batch-fix content_tags where the Part 2 cue stresses disposition / trait / habit
but legacy tagging used people + relationship/profession buckets.

Rules are documented in docs/taxonomy_people_vs_personal_traits.md.

Usage:
  python3 pipeline/remap_content_tags_disposition.py --quarter 2026-01-to-04 --dry-run
  python3 pipeline/remap_content_tags_disposition.py --quarter 2026-01-to-04
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent

# Do not treat as "trait disposition" — relationship, identity, role, other L1 templates.
_EXCLUDE_PERSON_WHO = re.compile(
    r"\b("
    r"you know|your friend|good friend|family member|famous|sportsperson|successful sportsperson|"
    r"teacher|older than|younger than|important to you|natural world|look after the natural|"
    r"^a child who|^someone who"
    r")\b",
    re.I,
)

# "a person who …" tail suggests disposition / habit / capability (not exhaustive; extend in code).
_TRAIT_TAIL = re.compile(
    r"^a person who\s+(.+)$",
    re.I,
)

_TRAIT_SIGNALS = re.compile(
    r"(often\s+)?helps?\s+others|"
    r"makes?\s+plans?|planning|good\s+at\s+planning|"
    r"solved\s+a\s+problem|smart\s+way|"
    r"\b(patient|honest|creative|kind|kindness|disciplined|organized|organised|reliable|generous|"
    r"shy|optimistic|pessimistic|hardworking|lazy|outgoing)\b",
    re.I,
)

_FAMILY_BUSINESS = re.compile(
    r"^a person you know who.*\b(family business|a shop)\b",
    re.I,
)


def norm_l1(s: str) -> str:
    return (s or "").strip().replace("/", "_")


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def remap_trait_person_who(topic: dict[str, Any]) -> tuple[bool, str]:
    """Returns (changed, reason)."""
    title = str(topic.get("topic") or "").strip()
    if not title:
        return False, ""

    ct = topic.get("content_tags")
    if not isinstance(ct, dict):
        return False, ""

    l1 = norm_l1(str(ct.get("l1") or ""))
    if l1 != "people":
        return False, ""

    m = _TRAIT_TAIL.match(title)
    if not m:
        return False, ""

    tail = m.group(1) or ""
    if _EXCLUDE_PERSON_WHO.search(title) or _EXCLUDE_PERSON_WHO.search(tail):
        return False, ""

    if not _TRAIT_SIGNALS.search(tail):
        return False, ""

    l3: list[str] = []
    tl = tail.lower()
    if re.search(r"helps?\s+others|help others", tl):
        l3 = ["kindness"]
    elif re.search(r"plan|planning", tl):
        l3 = ["discipline"]
    elif re.search(r"solved\s+a\s+problem|smart\s+way", tl):
        l3 = ["creativity"]
    else:
        l3 = []

    ct["l1"] = "abstract_concepts"
    ct["l2"] = ["personal_traits"]
    ct["l3"] = l3
    return True, "trait_disposition_person_who"


def fix_problem_solver_tags(topic: dict[str, Any]) -> tuple[bool, str]:
    """Normalise hyphenated l3; fix l2 to traits + growth for assign (problem_solving lives under growth)."""
    title = str(topic.get("topic") or "").strip().lower()
    if "solved a problem" not in title or "smart way" not in title:
        return False, ""

    ct = topic.get("content_tags")
    if not isinstance(ct, dict):
        return False, ""

    l3 = [str(x).strip() for x in (ct.get("l3") or []) if str(x).strip()]
    l3 = ["problem_solving" if x == "problem-solving" else x for x in l3]
    if "problem_solving" not in l3:
        l3 = uniq_keep(l3 + ["problem_solving"])
    before = (list(ct.get("l2") or []), list(ct.get("l3") or []))
    ct["l1"] = "abstract_concepts"
    ct["l2"] = ["personal_traits", "personal_growth"]
    ct["l3"] = uniq_keep(l3)
    after = (ct["l2"], ct["l3"])
    return before != after, "problem_solver_canonical"


def uniq_keep(seq: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for x in seq:
        k = x.lower()
        if k in seen:
            continue
        seen.add(k)
        out.append(x)
    return out


def fix_family_business_tags(topic: dict[str, Any]) -> tuple[bool, str]:
    """Obvious mis-tag (leisure/shopping) → people + work/family context."""
    title = str(topic.get("topic") or "").strip()
    if not _FAMILY_BUSINESS.match(title):
        return False, ""

    ct = topic.get("content_tags")
    if not isinstance(ct, dict):
        return False, ""

    # Only fix clearly wrong L1 (not already people with sensible tags)
    l1 = norm_l1(str(ct.get("l1") or ""))
    if l1 == "people":
        return False, ""

    ct["l1"] = "people"
    ct["l2"] = ["close_bonds", "professions"]
    ct["l3"] = ["family_activity", "business_owner"]
    return True, "family_business_mis_tag"


def run_part2(path: Path, *, dry_run: bool) -> dict[str, Any]:
    data = load_json(path)
    stats = {"trait_remap": 0, "problem_fix": 0, "family_business": 0, "log": []}

    for topic in data:
        if topic.get("part") != 2:
            continue

        ok, reason = fix_family_business_tags(topic)
        if ok:
            stats["family_business"] += 1
            stats["log"].append(f"FAMILY_BUSINESS {topic.get('topic')!r} -> {reason}")

        ok, reason = fix_problem_solver_tags(topic)
        if ok:
            stats["problem_fix"] += 1
            stats["log"].append(f"PROBLEM_SOLVER {topic.get('topic')!r} -> {reason}")

        ok, reason = remap_trait_person_who(topic)
        if ok:
            stats["trait_remap"] += 1
            stats["log"].append(f"TRAIT_REMAP {topic.get('topic')!r} -> {reason}")

    if not dry_run and (stats["trait_remap"] or stats["problem_fix"] or stats["family_business"]):
        save_json(path, data)

    return stats


def main() -> int:
    ap = argparse.ArgumentParser(description="Remap content_tags for disposition vs people mis-tags")
    ap.add_argument("--quarter", metavar="ID", required=True)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    path = ROOT / "data" / "quarters" / args.quarter / "merged_part2.json"
    if not path.is_file():
        print(f"ERROR: {path} not found", file=sys.stderr)
        return 2

    stats = run_part2(path, dry_run=args.dry_run)
    print(f"Quarter: {args.quarter} dry_run={args.dry_run}")
    print(f"  trait_remap: {stats['trait_remap']}")
    print(f"  problem_solver_fix: {stats['problem_fix']}")
    print(f"  family_business_fix: {stats['family_business']}")
    for line in stats["log"]:
        print(line)
    if not args.dry_run and (stats["trait_remap"] or stats["problem_fix"] or stats["family_business"]):
        print(f"Wrote: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
