"""
export_questions_tags.py
Reads merged_part1.txt and merged_part2.txt and exports all questions
with their skill_tags and topic content_tags to questions_and_tags.txt.

Usage:
    python3 pipeline/export_questions_tags.py
"""

import re
from pathlib import Path

ROOT = Path(__file__).parent.parent


# ---------------------------------------------------------------------------
# Parsers
# ---------------------------------------------------------------------------

def parse_part1(filepath):
    topics = []
    current = None

    with open(filepath, encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n")

            m = re.match(r"^== (.+) ==$", line)
            if m:
                current = {"topic": m.group(1).strip(), "content_tags": [], "questions": []}
                topics.append(current)
                continue

            if current is None:
                continue

            m = re.match(r"^TAGS:\s*(.+)$", line)
            if m:
                current["content_tags"] = [t.strip() for t in m.group(1).split(",")]
                continue

            # Question: [source] N. text [type1, type2]
            m = re.match(r"^\[.+?\]\s+\d+[\.\)]\s+(.+?)\s+\[([^\]]+)\]\s*$", line)
            if m:
                text = m.group(1).strip()
                skill_tags = [t.strip() for t in m.group(2).split(",")]
                current["questions"].append({"text": text, "skill_tags": skill_tags})

    return topics


def parse_part2(filepath):
    topics = []
    current = None
    in_part3 = False

    with open(filepath, encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n")

            m = re.match(r"^== (.+) ==$", line)
            if m:
                current = {"topic": m.group(1).strip(), "content_tags": [], "part3": []}
                topics.append(current)
                in_part3 = False
                continue

            if current is None:
                continue

            m = re.match(r"^TAGS:\s*(.+)$", line)
            if m:
                current["content_tags"] = [t.strip() for t in m.group(1).split("|")]
                continue

            if line.strip() == "PART3:":
                in_part3 = True
                continue

            if not in_part3:
                continue

            # Part 3 question: [source][type1,type2] N. text
            m = re.match(r"^\[.+?\]\[([^\]]+)\]\s+\d+[\.\)]\s+(.+)$", line)
            if m:
                skill_tags = [t.strip() for t in m.group(1).split(",")]
                text = m.group(2).strip()
                current["part3"].append({"text": text, "skill_tags": skill_tags})

    return topics


# ---------------------------------------------------------------------------
# Writer
# ---------------------------------------------------------------------------

def write_output(part1_topics, part2_topics, outpath):
    lines = []

    lines.append("=" * 70)
    lines.append("PART 1 QUESTIONS")
    lines.append("=" * 70)

    for topic in part1_topics:
        content = ", ".join(topic["content_tags"]) if topic["content_tags"] else "—"
        lines.append(f'\n[{topic["topic"]}]')
        lines.append(f'  content tags: {content}')
        for q in topic["questions"]:
            type_str = ", ".join(q["skill_tags"]) if q["skill_tags"] else "—"
            lines.append(f'  Q: {q["text"]}')
            lines.append(f'     type: {type_str}')

    lines.append("\n")
    lines.append("=" * 70)
    lines.append("PART 3 QUESTIONS  (from Part 2 topics)")
    lines.append("=" * 70)

    for topic in part2_topics:
        content = ", ".join(topic["content_tags"]) if topic["content_tags"] else "—"
        lines.append(f'\n[{topic["topic"]}]')
        lines.append(f'  content tags: {content}')
        for q in topic["part3"]:
            type_str = ", ".join(q["skill_tags"]) if q["skill_tags"] else "—"
            lines.append(f'  Q: {q["text"]}')
            lines.append(f'     type: {type_str}')

    outpath.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Written {sum(len(t['questions']) for t in part1_topics)} Part 1 questions "
          f"and {sum(len(t['part3']) for t in part2_topics)} Part 3 questions → {outpath}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    hitl = ROOT / "human-in-the-loop"
    p1_txt = hitl / "merged_part1.txt"
    p2_txt = hitl / "merged_part2.txt"
    out = hitl / "questions_and_tags.txt"

    for path in (p1_txt, p2_txt):
        if not path.exists():
            print(f"ERROR: {path} not found. Run json_to_txt.py first.")
            return

    part1 = parse_part1(p1_txt)
    part2 = parse_part2(p2_txt)
    write_output(part1, part2, out)


if __name__ == "__main__":
    main()
