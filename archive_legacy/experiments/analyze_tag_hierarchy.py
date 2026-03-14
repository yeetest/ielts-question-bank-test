"""
analyze_tag_hierarchy.py
──────────────────────────────────────────────────────────────────────
Reads TAG_HIERARCHY from rewrite_content_tags.py and outputs the full
3-layer nested hierarchy to layered_content_tags.txt.

Also loads tags/tags.txt to pull in tag descriptions.

Output: layered_content_tags.txt (repo root)
"""

from __future__ import annotations
import sys
import os

SCRIPT_DIR  = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT   = os.path.dirname(SCRIPT_DIR)
TAGS_FILE   = os.path.join(REPO_ROOT, "tags", "tags.txt")
OUTPUT_FILE = os.path.join(REPO_ROOT, "human-in-the-loop", "layered_content_tags.txt")

# ── import hierarchy from rewrite_content_tags ────────────────────
sys.path.insert(0, SCRIPT_DIR)
from rewrite_content_tags import TAG_HIERARCHY, L1_CATEGORIES

# ── load tag descriptions from tags.txt ───────────────────────────
def load_descriptions(path: str) -> dict[str, str]:
    descs: dict[str, str] = {}
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            tag_part = line.split("#")[0].strip()
            comment  = line.partition("#")[2].strip()
            # Remove layer annotations like [family] from comment
            import re
            comment = re.sub(r"^\[.*?\]\s*", "", comment)
            if tag_part:
                descs[tag_part] = comment
    return descs


def main():
    descs = load_descriptions(TAGS_FILE)

    # ── build tree ─────────────────────────────────────────────────
    # l1_tree[l1] = {l2: [l3, ...]}
    l1_tree: dict[str, dict[str, list[str]]] = {}
    qualifiers: list[str] = []

    for tag, (layer, parent) in TAG_HIERARCHY.items():
        if layer == 0:
            qualifiers.append(tag)
        elif layer == 1:
            if tag not in l1_tree:
                l1_tree[tag] = {}
        elif layer == 2:
            p = parent or "(none)"
            if p not in l1_tree:
                l1_tree[p] = {}
            if tag not in l1_tree[p]:
                l1_tree[p][tag] = []
        elif layer == 3:
            # Find L2 parent's L1 grandparent
            l2_info = TAG_HIERARCHY.get(parent, (None, None))
            l1 = l2_info[1] or "(none)"
            if l1 not in l1_tree:
                l1_tree[l1] = {}
            if parent not in l1_tree[l1]:
                l1_tree[l1][parent] = []
            l1_tree[l1][parent].append(tag)

    # ── write output ───────────────────────────────────────────────
    W = 70
    lines: list[str] = []

    def desc(tag: str) -> str:
        d = descs.get(tag, "")
        return f"  # {d}" if d else ""

    lines += [
        "LAYERED CONTENT TAGS  —  Nested Hierarchy",
        "=" * W,
        "Layer 1  — 4 fixed category roots (one per topic)",
        "Layer 2  — thematic cluster (domain / sub-domain)",
        "Layer 3  — specific / concrete tag (under an L2)",
        "Qualifiers — stored in qualifier_tags, not content_tags",
        "",
        "  L1_tag",
        "    ├── L2_tag          # description",
        "    │    ├── L3_tag     # description",
        "    │    └── L3_tag",
        "    └── L2_tag",
        "",
    ]

    FIXED_ORDER = ["people", "place", "object", "experience/activity"]

    for l1 in FIXED_ORDER:
        c1 = desc(l1)
        lines.append(f"  {l1}{c1}")

        l2_items = sorted(l1_tree.get(l1, {}).items(),
                          key=lambda kv: kv[0])

        for i2, (l2, l3_list) in enumerate(l2_items):
            is_last_l2 = (i2 == len(l2_items) - 1)
            conn2 = "└──" if is_last_l2 else "├──"
            c2 = desc(l2)
            lines.append(f"    {conn2} {l2}{c2}")

            l3_sorted = sorted(l3_list)
            indent3 = "         " if is_last_l2 else "    │    "

            for i3, l3 in enumerate(l3_sorted):
                is_last_l3 = (i3 == len(l3_sorted) - 1)
                conn3 = "└──" if is_last_l3 else "├──"
                c3 = desc(l3)
                lines.append(f"{indent3}{conn3} {l3}{c3}")

        lines.append("")

    # Qualifiers section
    lines += [
        "─" * W,
        "QUALIFIERS  (qualifier_tags field — separate from content_tags)",
        "─" * W,
        "  These describe the tone or quality of a topic.",
        "  They do not fit the L1→L2→L3 hierarchy.",
        "",
    ]
    for q in sorted(qualifiers):
        c = desc(q)
        lines.append(f"  {q}{c}")
    lines.append("")

    # Tag counts
    all_l1 = [t for t, (l, _) in TAG_HIERARCHY.items() if l == 1]
    all_l2 = [t for t, (l, _) in TAG_HIERARCHY.items() if l == 2]
    all_l3 = [t for t, (l, _) in TAG_HIERARCHY.items() if l == 3]

    lines += [
        "─" * W,
        "SUMMARY",
        "─" * W,
        f"  Layer 1 (roots)   : {len(all_l1)} tags",
        f"  Layer 2 (clusters): {len(all_l2)} tags",
        f"  Layer 3 (specific): {len(all_l3)} tags",
        f"  Qualifiers        : {len(qualifiers)} tags",
        f"  Total             : {len(TAG_HIERARCHY)} tags",
        "",
    ]

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"✓  Written → {OUTPUT_FILE}")
    print(f"   L1:{len(all_l1)}  L2:{len(all_l2)}  L3:{len(all_l3)}  qualifiers:{len(qualifiers)}")


if __name__ == "__main__":
    main()
