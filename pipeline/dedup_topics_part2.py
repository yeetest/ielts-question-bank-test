#!/usr/bin/env python3
"""
dedup_topics_part2.py
──────────────────────────────────────────────────────────────────────
Topic-level near-duplicate merge for Part 2 merged JSON (one survivor per cluster).

Problem solved: two cue-card topics that differ only in phrasing (e.g. "TV/online …
enjoy watching" vs "TV or online … like to watch") become two grid cards; this
script merges them into one record using explicit keep-best rules, then merges
Part 3 questions with fuzzy dedup (same spirit as dedup_questions.py).

Usage:
  python3 pipeline/dedup_topics_part2.py --quarter 2026-01-to-04 --dry-run
  python3 pipeline/dedup_topics_part2.py --quarter 2026-01-to-04
  python3 pipeline/dedup_topics_part2.py path/to/merged_part2.json

Requires: thefuzz (same as dedup_questions.py)

Keep-best (survivor) priority, in order:
  1. More Part 3 questions
  2. More cue-card bullet lines (you_should_say)
  3. Richer content_tags (more l3, then more l2)
  4. Non-empty season field
  5. Higher aggregate source tier (tongzhuo > laokaoya > yasige > other)
  6. Shorter topic string (slightly prefer compact exam-style titles when tied)

Merged record:
  - topic / cue_card.prompt: survivor's wording
  - you_should_say: survivor first, then unique bullets from duplicates
  - part3: concatenate all, then fuzzy dedup via dedup_questions.dedup_questions
  - content_tags: survivor l1; union of l2 / l3 lists (order preserved, de-duped)
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

from thefuzz import fuzz

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from dedup_questions import dedup_questions  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent

SOURCE_TIER = {"tongzhuo": 4, "laokaoya": 3, "yasige": 2}


def topic_fingerprint(raw: str) -> str:
    """Normalize wording so near-identical cue titles cluster together."""
    t = raw.lower().strip()
    t = t.replace("/", " ")
    t = re.sub(r"\s+", " ", t)
    t = re.sub(r"\byou like to watch\b", "you watch", t)
    t = re.sub(r"\byou enjoy watching\b", "you watch", t)
    t = re.sub(r"\byou love to watch\b", "you watch", t)
    t = re.sub(r"\byou love watching\b", "you watch", t)
    t = re.sub(r"\bor\b", " ", t)
    t = re.sub(r"[^a-z0-9 ]+", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t


def topic_similarity(a: str, b: str) -> int:
    fa, fb = topic_fingerprint(a), topic_fingerprint(b)
    return max(fuzz.ratio(fa, fb), fuzz.ratio(a.lower().strip(), b.lower().strip()))


def source_score(topic: dict[str, Any]) -> int:
    return sum(SOURCE_TIER.get(str(q.get("source") or "").lower(), 0) for q in topic.get("part3") or [])


def content_tags_richness(ct: Any) -> tuple[int, int]:
    if not isinstance(ct, dict):
        return 0, 0
    l3 = ct.get("l3") or []
    l2 = ct.get("l2") or []
    return (len(l3) if isinstance(l3, list) else 0), (len(l2) if isinstance(l2, list) else 0)


def survivor_score(topic: dict[str, Any]) -> tuple:
    p3 = len(topic.get("part3") or [])
    ys = len((topic.get("cue_card") or {}).get("you_should_say") or [])
    l3n, l2n = content_tags_richness(topic.get("content_tags"))
    season_ok = 1 if str(topic.get("season") or "").strip() else 0
    src = source_score(topic)
    title = str(topic.get("topic") or "")
    # Higher tuple is better; last component shorter title wins on tie (min length)
    return (p3, ys, l3n, l2n, season_ok, src, -len(title))


def pick_survivor(cluster: list[dict[str, Any]]) -> dict[str, Any]:
    return max(cluster, key=survivor_score)


def uniq_extend(base: list[str], extra: list[str]) -> list[str]:
    seen = {x.strip().lower() for x in base if x and str(x).strip()}
    out = list(base)
    for x in extra:
        if not x or not str(x).strip():
            continue
        k = str(x).strip().lower()
        if k in seen:
            continue
        seen.add(k)
        out.append(str(x).strip())
    return out


def merge_content_tags(winner: dict[str, Any], others: list[dict[str, Any]]) -> None:
    wct = winner.get("content_tags")
    if not isinstance(wct, dict):
        return
    l1 = str(wct.get("l1") or "").strip()
    l2: list[str] = []
    l3: list[str] = []
    for key in ("l2", "l3"):
        raw = wct.get(key) or []
        if isinstance(raw, list):
            if key == "l2":
                l2 = [str(x).strip() for x in raw if str(x).strip()]
            else:
                l3 = [str(x).strip() for x in raw if str(x).strip()]
    for t in others:
        ct = t.get("content_tags")
        if not isinstance(ct, dict):
            continue
        ol2 = ct.get("l2") or []
        ol3 = ct.get("l3") or []
        if isinstance(ol2, list):
            l2 = uniq_extend(l2, [str(x).strip() for x in ol2 if str(x).strip()])
        if isinstance(ol3, list):
            l3 = uniq_extend(l3, [str(x).strip() for x in ol3 if str(x).strip()])
    wct["l1"] = l1 or (others[0].get("content_tags") or {}).get("l1", "")
    wct["l2"] = l2
    wct["l3"] = l3


def merge_cluster(cluster: list[dict[str, Any]], *, part3_threshold: int) -> dict[str, Any]:
    winner = pick_survivor(cluster)
    losers = [t for t in cluster if t is not winner]
    cc_w = winner.get("cue_card") or {}
    ys = list(cc_w.get("you_should_say") or [])
    for t in losers:
        cc = t.get("cue_card") or {}
        ys = uniq_extend(ys, list(cc.get("you_should_say") or []))
    winner["cue_card"] = {
        "prompt": str(cc_w.get("prompt") or "").strip(),
        "you_should_say": ys,
    }
    all_p3: list[dict[str, Any]] = []
    for t in cluster:
        all_p3.extend(list(t.get("part3") or []))
    deduped, _ = dedup_questions(all_p3, threshold=part3_threshold)
    winner["part3"] = deduped
    merge_content_tags(winner, losers)
    # Prefer non-empty season from any cluster member if winner empty
    if not str(winner.get("season") or "").strip():
        for t in losers:
            s = str(t.get("season") or "").strip()
            if s:
                winner["season"] = s
                break
    return winner


def cluster_indices(topics: list[dict[str, Any]], threshold: int) -> list[list[int]]:
    n = len(topics)
    parent = list(range(n))

    def find(i: int) -> int:
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    def union(i: int, j: int) -> None:
        ri, rj = find(i), find(j)
        if ri != rj:
            parent[rj] = ri

    titles = [str(t.get("topic") or "").strip() for t in topics]
    for i in range(n):
        if not titles[i]:
            continue
        for j in range(i + 1, n):
            if not titles[j]:
                continue
            if topic_similarity(titles[i], titles[j]) >= threshold:
                union(i, j)

    buckets: dict[int, list[int]] = {}
    for i in range(n):
        r = find(i)
        buckets.setdefault(r, []).append(i)
    return [sorted(v) for v in buckets.values() if len(v) > 1]


def run(path: Path, *, threshold: int, part3_threshold: int, dry_run: bool) -> int:
    data = json.loads(path.read_text(encoding="utf-8"))
    clusters = cluster_indices(data, threshold)
    if not clusters:
        print("No topic clusters above threshold; nothing to merge.")
        return 0

    print(f"File: {path}")
    print(f"Topic similarity threshold: {threshold} (thefuzz ratio)")
    print(f"Part3 merge dedup threshold: {part3_threshold}")
    for c in clusters:
        titles = [data[i].get("topic") for i in c]
        print(f"  CLUSTER ({len(c)}): {titles}")

    remove_idx: set[int] = set()
    for c in clusters:
        cluster_topics = [data[i] for i in c]
        surv = pick_survivor(cluster_topics)
        keep_i = c[cluster_topics.index(surv)]
        for i in c:
            if i != keep_i:
                remove_idx.add(i)

    if dry_run:
        print(f"\nDRY-RUN: would remove {len(remove_idx)} topics (merge into survivors in each cluster).")
        return len(remove_idx)

    for c in clusters:
        cluster_topics = [data[i] for i in c]
        merge_cluster(cluster_topics, part3_threshold=part3_threshold)

    new_data = [topic for i, topic in enumerate(data) if i not in remove_idx]
    path.write_text(json.dumps(new_data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"\nWrote {path}: removed {len(remove_idx)} duplicate topics, {len(new_data)} topics remain.")
    return len(remove_idx)


def main() -> int:
    ap = argparse.ArgumentParser(description="Merge near-duplicate Part 2 topics in merged_part2.json")
    ap.add_argument("--quarter", metavar="ID", help="data/quarters/<ID>/merged_part2.json")
    ap.add_argument("path", nargs="?", type=Path, help="merged_part2.json path")
    ap.add_argument("--threshold", type=int, default=90, help="Min fuzz ratio to merge two topics (default 90)")
    ap.add_argument(
        "--part3-threshold",
        type=int,
        default=85,
        help="Fuzzy threshold when deduping merged Part3 lists (default 85)",
    )
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    if args.quarter and args.path:
        ap.error("Use either --quarter or a path argument, not both.")
    if args.quarter:
        path = ROOT / "data" / "quarters" / args.quarter / "merged_part2.json"
    elif args.path:
        path = args.path if args.path.is_absolute() else ROOT / args.path
    else:
        ap.error("Pass --quarter <id> or merged_part2.json path")

    if not path.is_file():
        print(f"ERROR: {path} not found", file=sys.stderr)
        return 2

    run(path, threshold=args.threshold, part3_threshold=args.part3_threshold, dry_run=args.dry_run)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
