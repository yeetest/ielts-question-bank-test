"""
rewrite_content_tags.py
──────────────────────────────────────────────────────────────────────
Rewrites content_tags in merged_part1.json and merged_part2.json from
a flat list to the new 3-layer structured format.

OLD format (flat list):
  "content_tags": ["experience/activity", "music", "likes_dislikes"]

NEW format (structured object):
  "content_tags": {"l1": "experience/activity",
                   "l2": ["music"],
                   "l3": ["likes_dislikes"]},
  "qualifier_tags": []

Rules
─────
• Position 0 of the old list  → l1  (must be one of the 4 L1 categories)
• Each remaining tag is classified by TAG_HIERARCHY into l2 / l3 / qualifier
• If an L3 tag is present but its L2 parent is NOT already in l2, the parent
  is automatically inferred and added (so the path is always complete)
• Qualifier tags are removed from content_tags and placed in qualifier_tags
• Tags that are L1 in the hierarchy but appear in non-0 positions are treated
  as L2 (they were used thematically in the old system)
• Unknown tags (not in TAG_HIERARCHY) are kept in l2 with a warning

Usage
─────
  python3 pipeline/rewrite_content_tags.py [--dry-run]

  --dry-run   Print the proposed changes without writing to disk.

After running, regenerate .txt mirrors:
  python3 pipeline/json_to_txt.py merged_part1.json
  python3 pipeline/json_to_txt.py merged_part2.json
"""

from __future__ import annotations
import json
import os
import sys

SCRIPT_DIR  = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT   = os.path.dirname(SCRIPT_DIR)
P1_FILE     = os.path.join(REPO_ROOT, "merged_part1.json")
P2_FILE     = os.path.join(REPO_ROOT, "merged_part2.json")

DRY_RUN = "--dry-run" in sys.argv

# ══════════════════════════════════════════════════════════════════
# COMPLETE TAG HIERARCHY
# ══════════════════════════════════════════════════════════════════
# Format: tag → (layer, l2_parent_or_None)
#   layer 1 = L1 category root
#   layer 2 = thematic cluster (L2)
#   layer 3 = specific tag (L3)
#   layer 0 = qualifier (goes to qualifier_tags, not content_tags)

TAG_HIERARCHY: dict[str, tuple[int, str | None]] = {

    # ── L1 roots ─────────────────────────────────────────────────
    "people":              (1, None),
    "place":               (1, None),
    "object":              (1, None),
    "experience/activity": (1, None),

    # ── L2 under people ──────────────────────────────────────────
    "family":        (2, "people"),
    "friendship":    (2, "people"),
    "celebrity":     (2, "people"),
    "influence":     (2, "people"),
    "admiration":    (2, "people"),
    "talent":        (2, "people"),
    "intelligence":  (2, "people"),
    "happiness":     (2, "people"),
    "child":         (2, "people"),

    # ── L3 under people L2s ───────────────────────────────────────
    "conflict_resolution": (3, "family"),
    "helping_others":      (3, "friendship"),
    "collaboration":       (3, "friendship"),
    "problem-solving":     (3, "intelligence"),

    # ── L2 under place ───────────────────────────────────────────
    "home":         (2, "place"),
    "travel":       (2, "place"),
    "nature":       (2, "place"),
    "architecture": (2, "place"),

    # ── L3 under place L2s ────────────────────────────────────────
    "everyday_life": (3, "home"),
    "adventure":     (3, "travel"),
    "international": (3, "travel"),
    "navigation":    (3, "travel"),
    "animals":       (3, "nature"),
    "conservation":  (3, "nature"),

    # ── L2 under object ──────────────────────────────────────────
    "books":      (2, "object"),
    "heirloom":   (2, "object"),
    "toy":        (2, "object"),
    "phone":      (2, "object"),
    "money":      (2, "object"),
    "technology": (2, "object"),

    # ── L3 under object L2s ───────────────────────────────────────
    "app":          (3, "technology"),
    "social_media": (3, "technology"),

    # ── L2 under experience/activity ─────────────────────────────
    "art":          (2, "experience/activity"),
    "music":        (2, "experience/activity"),
    "reading":      (2, "experience/activity"),
    "movies":       (2, "experience/activity"),
    "food":         (2, "experience/activity"),
    "work":         (2, "experience/activity"),
    "sports":       (2, "experience/activity"),
    "shopping":     (2, "experience/activity"),
    "learning":     (2, "experience/activity"),
    "science":      (2, "experience/activity"),
    "creativity":   (2, "experience/activity"),
    "culture":      (2, "experience/activity"),
    "communication":(2, "experience/activity"),
    "media":        (2, "experience/activity"),
    "celebration":  (2, "experience/activity"),
    "disruption":   (2, "experience/activity"),
    "mistake":      (2, "experience/activity"),
    "service":      (2, "experience/activity"),
    "achievement":  (2, "experience/activity"),
    "passion":      (2, "experience/activity"),
    "aspiration":   (2, "experience/activity"),
    "anticipation": (2, "experience/activity"),
    "childhood":    (2, "experience/activity"),
    "habit":        (2, "experience/activity"),

    # ── L3 under experience/activity L2s ─────────────────────────
    "self-learning":    (3, "learning"),
    "curiosity":        (3, "learning"),
    "stories":          (3, "culture"),
    "language":         (3, "culture"),
    "advice":           (3, "communication"),
    "social_event":     (3, "celebration"),
    "first_time":       (3, "celebration"),
    "restriction":      (3, "disruption"),
    "planning":         (3, "achievement"),
    "self-improvement": (3, "achievement"),
    "decision":         (3, "achievement"),
    "likes_dislikes":   (3, "passion"),
    "nostalgia":        (3, "childhood"),

    # ── Qualifiers (→ qualifier_tags, not content_tags) ──────────
    "memorable":   (0, None),
    "sentimental": (0, None),
    "peaceful":    (0, None),
    "useful":      (0, None),
    "interesting": (0, None),
}

# The 4 valid L1 values
L1_CATEGORIES = {"people", "place", "object", "experience/activity"}


# ── helpers ────────────────────────────────────────────────────────
def classify_tag(tag: str) -> tuple[int, str | None]:
    """Return (layer, parent) for a tag, defaulting to (2, None) if unknown."""
    return TAG_HIERARCHY.get(tag, (2, None))


def migrate_topic(old_tags: list[str], topic_label: str) -> dict:
    """
    Convert a flat content_tags list to the new structured format.
    Returns {"content_tags": {"l1":..., "l2":[...], "l3":[...]},
             "qualifier_tags": [...],
             "warnings": [...]}
    """
    warnings: list[str] = []
    l1 = None
    l2: list[str] = []
    l3: list[str] = []
    qualifiers: list[str] = []

    for i, tag in enumerate(old_tags):
        layer, parent = classify_tag(tag)

        if layer == 0:
            qualifiers.append(tag)
            continue

        if i == 0:
            # First tag is always the primary L1 category
            if tag not in L1_CATEGORIES:
                warnings.append(
                    f"Position-0 tag '{tag}' is not an L1 category — "
                    f"treating as L1 anyway"
                )
            l1 = tag
            continue

        # Non-zero positions
        if layer == 1:
            # A second L1-depth tag used thematically → treat as L2
            warnings.append(
                f"Tag '{tag}' is L1-depth but appears at non-0 position — "
                f"placing in l2"
            )
            if tag not in l2:
                l2.append(tag)

        elif layer == 2:
            if tag not in l2:
                l2.append(tag)

        elif layer == 3:
            if tag not in l3:
                l3.append(tag)
            # Auto-infer L2 parent
            if parent and parent not in l2:
                l2.append(parent)
                warnings.append(
                    f"Auto-added L2 parent '{parent}' for L3 tag '{tag}'"
                )

        else:
            # layer == 2 default for unknowns
            warnings.append(f"Unknown tag '{tag}' — placed in l2")
            if tag not in l2:
                l2.append(tag)

    if l1 is None and old_tags:
        l1 = old_tags[0]
        warnings.append(f"No L1 tag found, defaulted to first tag '{l1}'")

    return {
        "content_tags": {"l1": l1, "l2": l2, "l3": l3},
        "qualifier_tags": qualifiers,
        "warnings": warnings,
    }


# ── main ──────────────────────────────────────────────────────────
def process_file(path: str, topic_key: str) -> tuple[list, dict]:
    """Load JSON, migrate all topics, return (updated_data, report)."""
    data = json.load(open(path, encoding="utf-8"))
    report: dict = {"total": len(data), "changed": 0, "warnings": []}

    for topic in data:
        label = topic.get(topic_key) or topic.get("topic_en") or topic.get("topic", "?")
        old_ct = topic.get("content_tags", [])

        # Skip topics already in new format
        if isinstance(old_ct, dict):
            continue

        result = migrate_topic(old_ct, label)
        topic["content_tags"] = result["content_tags"]
        topic["qualifier_tags"] = result["qualifier_tags"]

        if result["warnings"]:
            for w in result["warnings"]:
                report["warnings"].append(f"  [{label[:45]}] {w}")

        report["changed"] += 1

    return data, report


def print_report(filename: str, data: list, report: dict, topic_key: str) -> None:
    print(f"\n{'═' * 65}")
    print(f"  {filename}")
    print(f"{'═' * 65}")
    print(f"  Topics processed : {report['changed']} / {report['total']}")

    if report["warnings"]:
        print(f"  Warnings ({len(report['warnings'])}):")
        for w in report["warnings"]:
            print(f"   ⚠  {w}")

    print(f"\n  Sample output (first 5 topics):")
    for topic in data[:5]:
        label = topic.get(topic_key, "?")[:45]
        ct = topic.get("content_tags", {})
        qt = topic.get("qualifier_tags", [])
        print(f"    [{label}]")
        print(f"      l1 : {ct.get('l1')}")
        print(f"      l2 : {ct.get('l2')}")
        print(f"      l3 : {ct.get('l3')}")
        if qt:
            print(f"      qualifiers: {qt}")


def main():
    if DRY_RUN:
        print("DRY RUN — no files will be written\n")

    p1_data, p1_report = process_file(P1_FILE, "topic_en")
    p2_data, p2_report = process_file(P2_FILE, "topic")

    print_report("merged_part1.json", p1_data, p1_report, "topic_en")
    print_report("merged_part2.json", p2_data, p2_report, "topic")

    total_warnings = len(p1_report["warnings"]) + len(p2_report["warnings"])
    print(f"\n{'─' * 65}")
    print(f"  Total warnings : {total_warnings}")

    if DRY_RUN:
        print("\n  (dry run — skipping file write)")
        return

    with open(P1_FILE, "w", encoding="utf-8") as f:
        json.dump(p1_data, f, ensure_ascii=False, indent=2)
    with open(P2_FILE, "w", encoding="utf-8") as f:
        json.dump(p2_data, f, ensure_ascii=False, indent=2)

    print("\n✓  Written: merged_part1.json, merged_part2.json")
    print("   Next: regenerate .txt mirrors")
    print("     python3 human-in-the-loop/json_to_txt.py merged_part1.json")
    print("     python3 human-in-the-loop/json_to_txt.py merged_part2.json")


if __name__ == "__main__":
    main()
