#!/usr/bin/env python3
"""
remap_content_tags_disposition.py

Batch-fix content_tags where the Part 2 cue is mis-tagged:
  1. Trait/disposition cues wrongly under people → abstract_concepts/personal_traits
  2. Work/business activity cues wrongly under people → experience/activity/work

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

# --- Work / study activity detection ---

# "a person [you know] who [verb] for/at/in [work context noun]" patterns
_WORK_CONTEXT_TAIL = re.compile(
    r"(?:enjoys?\s+)?(?:working|works?|employed|running|managing|operating)\s+"
    r"(?:for|at|in)\s+.*\b(?:business|company|shop|store|factory|office|firm|enterprise|"
    r"organi[sz]ation|startup|restaurant|bakery|caf[eé]|market|clinic|salon|studio|agency)\b",
    re.I,
)

_STUDY_CONTEXT_TAIL = re.compile(
    r"(?:enjoys?\s+)?(?:studying|studies|study|learning|teaches|teaching)\s+"
    r"(?:at|in)\s+.*\b(?:school|university|college|academy|institute|class|course)\b",
    re.I,
)

# Exclusion for work/study remap: genuine person-identity cues that happen to mention work/study
_EXCLUDE_WORK_REMAP = re.compile(
    r"\b(famous|sportsperson|teacher|older\s+than|younger\s+than|admire|natural world)\b",
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


def remap_work_activity_person_who(topic: dict[str, Any]) -> tuple[bool, str]:
    """Remap 'a person [you know] who works/enjoys working for [business]' etc.
    from people → experience/activity when the cue focuses on the work/study
    activity itself, not on describing who the person is."""
    title = str(topic.get("topic") or "").strip()
    if not title:
        return False, ""

    ct = topic.get("content_tags")
    if not isinstance(ct, dict):
        return False, ""

    l1 = norm_l1(str(ct.get("l1") or ""))
    if l1 != "people":
        return False, ""

    m = re.match(r"^a person\b.*?\bwho\s+(.+)$", title, re.I)
    if not m:
        return False, ""

    tail = m.group(1) or ""

    if _EXCLUDE_WORK_REMAP.search(title):
        return False, ""

    if _WORK_CONTEXT_TAIL.search(tail):
        ct["l1"] = "experience/activity"
        ct["l2"] = ["work"]
        ct["l3"] = ["workplace_experience"]
        return True, "work_activity_person_who"

    if _STUDY_CONTEXT_TAIL.search(tail):
        ct["l1"] = "experience/activity"
        ct["l2"] = ["study"]
        ct["l3"] = []
        return True, "study_activity_person_who"

    return False, ""


def run_part2(path: Path, *, dry_run: bool) -> dict[str, Any]:
    data = load_json(path)
    stats = {"work_activity": 0, "trait_remap": 0, "problem_fix": 0, "log": []}

    for topic in data:
        if topic.get("part") != 2:
            continue

        ok, reason = remap_work_activity_person_who(topic)
        if ok:
            stats["work_activity"] += 1
            stats["log"].append(f"WORK_ACTIVITY {topic.get('topic')!r} -> {reason}")

        ok, reason = fix_problem_solver_tags(topic)
        if ok:
            stats["problem_fix"] += 1
            stats["log"].append(f"PROBLEM_SOLVER {topic.get('topic')!r} -> {reason}")

        ok, reason = remap_trait_person_who(topic)
        if ok:
            stats["trait_remap"] += 1
            stats["log"].append(f"TRAIT_REMAP {topic.get('topic')!r} -> {reason}")

    if not dry_run and (stats["work_activity"] or stats["trait_remap"] or stats["problem_fix"]):
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
    print(f"  work_activity_remap: {stats['work_activity']}")
    print(f"  trait_remap: {stats['trait_remap']}")
    print(f"  problem_solver_fix: {stats['problem_fix']}")
    for line in stats["log"]:
        print(line)
    if not args.dry_run and (stats["work_activity"] or stats["trait_remap"] or stats["problem_fix"]):
        print(f"Wrote: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
