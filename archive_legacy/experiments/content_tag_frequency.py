"""
content_tag_frequency.py
Reads questions_and_tags.txt, counts occurrences of each content tag,
and writes content_tag_frequency.txt sorted highest to lowest.

Usage:
    python3 pipeline/content_tag_frequency.py
"""

import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).parent.parent
HITL = ROOT / "human-in-the-loop"
INPUT = HITL / "questions_and_tags.txt"
OUTPUT = HITL / "content_tag_frequency.txt"


def main():
    if not INPUT.exists():
        print(f"ERROR: {INPUT} not found. Run export_questions_tags.py first.")
        return

    counts = Counter()

    with open(INPUT, encoding="utf-8") as f:
        for line in f:
            m = re.match(r"^\s+content tags:\s*(.+)$", line)
            if m:
                tags = [t.strip() for t in m.group(1).split(",") if t.strip() and t.strip() != "—"]
                counts.update(tags)

    lines = ["Content Tag Frequency", "=" * 40, ""]
    for tag, count in counts.most_common():
        lines.append(f"{tag:<35} {count}")

    OUTPUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Written {len(counts)} unique tags → {OUTPUT}")


if __name__ == "__main__":
    main()
