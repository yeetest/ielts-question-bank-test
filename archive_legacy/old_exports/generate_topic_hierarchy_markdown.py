#!/usr/bin/env python3
"""
generate_topic_hierarchy_markdown.py

Builds a topic hierarchy markdown file from current JSON data:
  L1 -> L2 -> L3 -> question/content items

Input:
  - merged_part1.json
  - merged_part2.json

Output (overwrite each run):
  - human-in-the-loop/topic_hierarchy.md

Usage:
  python3 pipeline/generate_topic_hierarchy_markdown.py
"""

from __future__ import annotations

import json
import re
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
PART1_PATH = ROOT / "merged_part1.json"
PART2_PATH = ROOT / "merged_part2.json"
OUT_PATH = ROOT / "human-in-the-loop" / "topic_hierarchy.md"

MISSING_L1 = "uncategorized_l1"
MISSING_L2 = "uncategorized_l2"
MISSING_L3 = "uncategorized_l3"


@dataclass(frozen=True)
class Item:
    item_id: int
    label: str


def load_json(path: Path):
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def strip_leading_number(text: str) -> str:
    return re.sub(r"^\s*\d+[\.\)]\s*", "", text or "").strip()


def topic_tags(topic: dict) -> tuple[str, list[str], list[str]]:
    """
    Returns normalized (l1, l2_list, l3_list).
    Supports both structured and legacy flat content_tags.
    """
    ct = topic.get("content_tags")

    if isinstance(ct, dict):
        l1 = (ct.get("l1") or "").strip() or MISSING_L1
        l2 = [str(x).strip() for x in (ct.get("l2") or []) if str(x).strip()]
        l3 = [str(x).strip() for x in (ct.get("l3") or []) if str(x).strip()]
        return l1, (l2 or [MISSING_L2]), (l3 or [MISSING_L3])

    if isinstance(ct, list) and ct:
        l1 = str(ct[0]).strip() or MISSING_L1
        tail = [str(x).strip() for x in ct[1:] if str(x).strip()]
        return l1, (tail or [MISSING_L2]), [MISSING_L3]

    return MISSING_L1, [MISSING_L2], [MISSING_L3]


def collect_items(part1: list[dict], part2: list[dict]) -> list[tuple[str, list[str], list[str], Item]]:
    """
    Flatten questions/content into (l1, l2_list, l3_list, Item).
    Part 1 uses topic.questions.
    Part 2 uses topic.part3; if no part3 exists, falls back to cue_card.prompt as content item.
    """
    rows: list[tuple[str, list[str], list[str], Item]] = []
    next_id = 1

    for topic in part1:
        l1, l2_list, l3_list = topic_tags(topic)
        topic_name = topic.get("topic_en", "").strip() or "unknown_topic"
        for q in topic.get("questions", []):
            text = strip_leading_number(q.get("text", ""))
            if not text:
                continue
            label = f"Question {next_id:04d}: {text} (Part 1 · {topic_name})"
            rows.append((l1, l2_list, l3_list, Item(next_id, label)))
            next_id += 1

    for topic in part2:
        l1, l2_list, l3_list = topic_tags(topic)
        topic_name = topic.get("topic", "").strip() or topic.get("topic_en", "").strip() or "unknown_topic"
        part3 = topic.get("part3", [])

        if part3:
            for q in part3:
                text = strip_leading_number(q.get("text", ""))
                if not text:
                    continue
                label = f"Question {next_id:04d}: {text} (Part 3 · {topic_name})"
                rows.append((l1, l2_list, l3_list, Item(next_id, label)))
                next_id += 1
        else:
            prompt = strip_leading_number((topic.get("cue_card") or {}).get("prompt", ""))
            if prompt:
                label = f"Content {next_id:04d}: {prompt} (Part 2 Cue Card · {topic_name})"
                rows.append((l1, l2_list, l3_list, Item(next_id, label)))
                next_id += 1

    return rows


def build_tree(rows: list[tuple[str, list[str], list[str], Item]]):
    """
    Tree shape:
      tree[l1][l2][l3] -> dict[item_id, label]
    """
    tree = defaultdict(lambda: defaultdict(lambda: defaultdict(dict)))

    for l1, l2_list, l3_list, item in rows:
        for l2 in l2_list:
            for l3 in l3_list:
                tree[l1][l2][l3][item.item_id] = item.label

    return tree


def render_markdown(tree) -> str:
    lines = ["# Topic Hierarchy", ""]

    for l1 in sorted(tree.keys()):
        lines.append(f"- {l1}")
        l2_map = tree[l1]
        for l2 in sorted(l2_map.keys()):
            lines.append(f"  - {l2}")
            l3_map = l2_map[l2]
            for l3 in sorted(l3_map.keys()):
                lines.append(f"    - {l3}")
                items = l3_map[l3]
                for item_id in sorted(items.keys()):
                    lines.append(f"      - {items[item_id]}")

    lines.append("")
    return "\n".join(lines)


def main():
    if not PART1_PATH.exists() or not PART2_PATH.exists():
        raise FileNotFoundError("merged_part1.json or merged_part2.json not found in project root.")

    part1 = load_json(PART1_PATH)
    part2 = load_json(PART2_PATH)

    rows = collect_items(part1, part2)
    tree = build_tree(rows)
    markdown = render_markdown(tree)

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(markdown, encoding="utf-8")

    print(f"Wrote {OUT_PATH}")
    print(f"Items exported: {len(rows)}")
    print(f"L1 count: {len(tree)}")


if __name__ == "__main__":
    main()
