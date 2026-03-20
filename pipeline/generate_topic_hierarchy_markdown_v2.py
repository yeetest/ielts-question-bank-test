#!/usr/bin/env python3
"""
generate_topic_hierarchy_markdown_v2.py

Reads v2 taxonomy views and generates markdown:
- Main tree uses primary path only
- Secondary tags are exported as a separate Secondary Index appendix
"""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
P1_VIEW = ROOT / "human-in-the-loop" / "topic_taxonomy_view_v2_part1.json"
P2_VIEW = ROOT / "human-in-the-loop" / "topic_taxonomy_view_v2_part2.json"
OUT_MD = ROOT / "human-in-the-loop" / "topic_hierarchy_v2.md"


def load_json(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def ensure_inputs_exist():
    missing = [str(p) for p in (P1_VIEW, P2_VIEW) if not p.exists()]
    if missing:
        msg = [
            "Missing required v2 taxonomy view file(s):",
            *[f"- {m}" for m in missing],
            "",
            "Run first:",
            "python pipeline/build_topic_taxonomy_view_v2.py",
        ]
        raise FileNotFoundError("\n".join(msg))


def norm(value: Any, fallback: str) -> str:
    if value is None:
        return fallback
    text = str(value).strip()
    return text if text else fallback


def build_primary_tree(rows: list[dict[str, Any]]):
    # tree[l1][l2][l3] -> set(topics)
    tree: dict[str, dict[str, dict[str, set[str]]]] = defaultdict(lambda: defaultdict(lambda: defaultdict(set)))
    for row in rows:
        topic = norm(row.get("topic"), "unknown_topic")
        primary = row.get("taxonomy_v2", {}).get("primary", {})
        l1 = norm(primary.get("l1"), "uncategorized_l1")
        l2 = norm(primary.get("l2"), "uncategorized_l2")
        l3 = norm(primary.get("l3"), "no_l3")
        tree[l1][l2][l3].add(topic)
    return tree


def build_secondary_index(rows: list[dict[str, Any]]):
    index_l2: dict[str, set[str]] = defaultdict(set)
    index_l3: dict[str, set[str]] = defaultdict(set)

    for row in rows:
        topic = norm(row.get("topic"), "unknown_topic")
        secondary = row.get("taxonomy_v2", {}).get("secondary", {})
        for l2 in secondary.get("l2", []):
            name = norm(l2, "")
            if name:
                index_l2[name].add(topic)
        for l3 in secondary.get("l3", []):
            name = norm(l3, "")
            if name:
                index_l3[name].add(topic)

    return index_l2, index_l3


def render_markdown(rows: list[dict[str, Any]]) -> str:
    tree = build_primary_tree(rows)
    sec_l2, sec_l3 = build_secondary_index(rows)

    lines: list[str] = ["# Topic Hierarchy V2", ""]

    for l1 in sorted(tree.keys()):
        lines.append(f"- {l1}")
        for l2 in sorted(tree[l1].keys()):
            lines.append(f"  - {l2}")
            for l3 in sorted(tree[l1][l2].keys()):
                lines.append(f"    - {l3}")
                for topic in sorted(tree[l1][l2][l3]):
                    lines.append(f"      - {topic}")

    lines.extend(["", "# Secondary Index", ""])

    lines.append("## l2")
    for l2 in sorted(sec_l2.keys()):
        lines.append(f"- {l2}")
        for topic in sorted(sec_l2[l2]):
            lines.append(f"  - {topic}")

    lines.extend(["", "## l3"])
    for l3 in sorted(sec_l3.keys()):
        lines.append(f"- {l3}")
        for topic in sorted(sec_l3[l3]):
            lines.append(f"  - {topic}")

    lines.append("")
    return "\n".join(lines)


def main():
    ensure_inputs_exist()
    rows = load_json(P1_VIEW) + load_json(P2_VIEW)
    markdown = render_markdown(rows)
    OUT_MD.parent.mkdir(parents=True, exist_ok=True)
    OUT_MD.write_text(markdown, encoding="utf-8")

    print("Wrote markdown to: human-in-the-loop/topic_hierarchy_v2.md")
    print(f"Topics exported: {len(rows)}")


if __name__ == "__main__":
    main()

