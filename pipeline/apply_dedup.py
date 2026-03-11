"""
apply_dedup.py
──────────────────────────────────────────────────────────────────────
Reads human-reviewed duplicates.txt and removes questions marked
[REMOVE] from merged_part1.json and merged_part2.json.

Matching: uses Part number + topic name + exact question text.

After removing, renumbers remaining questions and regenerates .txt
mirrors.

Usage:
    python3 pipeline/apply_dedup.py [--dry-run]
"""

import json, os, re, sys, subprocess

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(SCRIPT_DIR)

INPUT = os.path.join(REPO_ROOT, "human-in-the-loop", "duplicates.txt")
P1_FILE = os.path.join(REPO_ROOT, "merged_part1.json")
P2_FILE = os.path.join(REPO_ROOT, "merged_part2.json")

DRY_RUN = "--dry-run" in sys.argv


def parse_duplicates(path):
    """Parse duplicates.txt, return list of questions marked REMOVE."""
    removals = []

    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n")
            m = re.match(r"\[REMOVE\]\s*Part\s*(\d)\s*\|\s*(.+?)\s*\|\s*(.+?)(?:\s*\[.*?\])?\s*\(source:\s*\w+\)\s*$", line)
            if m:
                part = int(m.group(1))
                topic = m.group(2).strip()
                text = m.group(3).strip()
                removals.append({"part": part, "topic": topic, "text": text})

    return removals


def normalise(text):
    """Normalise question text for matching."""
    return re.sub(r"\s+", " ", text.lower().strip())


def apply_removals(data, removals, part):
    """Remove matched questions from data. Returns count removed."""
    # Build lookup: normalised topic → list of normalised texts to remove
    to_remove = {}
    for r in removals:
        if r["part"] != part:
            continue
        key = normalise(r["topic"])
        if key not in to_remove:
            to_remove[key] = []
        to_remove[key].append(normalise(r["text"]))

    if not to_remove:
        return 0

    total_removed = 0

    for topic in data:
        if part == 1:
            topic_name = normalise(topic.get("topic_en", ""))
            q_key = "questions"
        else:
            topic_name = normalise(topic.get("topic", topic.get("topic_en", "")))
            q_key = "part3"

        if topic_name not in to_remove:
            continue

        texts_to_remove = to_remove[topic_name]
        original = topic.get(q_key, [])
        filtered = [q for q in original if normalise(q["text"]) not in texts_to_remove]
        removed = len(original) - len(filtered)

        if removed > 0:
            # Renumber remaining questions
            for i, q in enumerate(filtered, 1):
                q["text"] = re.sub(r"^\d+[\.\)]\s*", f"{i}. ", q["text"])
            topic[q_key] = filtered
            total_removed += removed

    return total_removed


def main():
    if DRY_RUN:
        print("DRY RUN — no files will be written\n")

    if not os.path.exists(INPUT):
        sys.exit(f"ERROR: {INPUT} not found. Run dedup_cross_topic.py first.")

    removals = parse_duplicates(INPUT)
    if not removals:
        print("No [REMOVE] entries found in duplicates.txt. Nothing to do.")
        return

    print(f"Found {len(removals)} questions marked [REMOVE]")

    p1_data = json.load(open(P1_FILE, encoding="utf-8"))
    p2_data = json.load(open(P2_FILE, encoding="utf-8"))

    r1 = apply_removals(p1_data, removals, 1)
    r2 = apply_removals(p2_data, removals, 2)

    print(f"Part 1: {r1} questions removed")
    print(f"Part 2+3: {r2} questions removed")

    if DRY_RUN:
        print("\n(dry run — skipping file write)")
        return

    with open(P1_FILE, "w", encoding="utf-8") as f:
        json.dump(p1_data, f, ensure_ascii=False, indent=2)
    with open(P2_FILE, "w", encoding="utf-8") as f:
        json.dump(p2_data, f, ensure_ascii=False, indent=2)

    print(f"\n✓  Written: {P1_FILE}")
    print(f"✓  Written: {P2_FILE}")

    # Regenerate .txt mirrors
    txt_script = os.path.join(REPO_ROOT, "human-in-the-loop", "json_to_txt.py")
    if os.path.exists(txt_script):
        print("\nRegenerating .txt mirrors...")
        subprocess.run([sys.executable, txt_script, P1_FILE], check=True)
        subprocess.run([sys.executable, txt_script, P2_FILE], check=True)


if __name__ == "__main__":
    main()
