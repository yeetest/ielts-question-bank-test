"""
tag_time_frames.py
Tags questions with a single time_frame value: "past", "present", or "future".

Applies to both Part 1 (questions[]) and Part 2 (part3[]).
Priority: past signals checked first, then future signals, default = present.

Usage:
    python3 pipeline/tag_time_frames.py merged_part1.json --part 1
    python3 pipeline/tag_time_frames.py merged_part2.json
    python3 pipeline/tag_time_frames.py merged_part1.json --part 1 --dry-run
    python3 pipeline/tag_time_frames.py merged_part1.json --part 1 --overwrite
"""

import json
import re
import sys
import subprocess
from pathlib import Path


# ---------------------------------------------------------------------------
# Past signals — checked first (highest priority)
# ---------------------------------------------------------------------------
PAST_PATTERNS = [
    # Past simple
    r"\bdid you\b",
    r"\bdid your\b",
    r"\bwhat did\b",
    r"\bwhen did\b",
    r"\bwhere did\b",
    r"\bhow did\b",
    r"\bwho did\b",
    r"\bwas (the|it|there|your|that|this)\b",
    r"\bwere (you|they|there|the)\b",

    # Present perfect (asking about past experience — personal "have you" only)
    r"\bhave you ever\b",
    r"\bhave you been\b",
    r"\bhave you tried\b",
    r"\bhave you (had|seen|visited|learned|heard|read|met|done|made|bought|experienced|changed|borrowed)\b",

    # Past-referring phrases
    r"\bwhen you were\b",
    r"\bas a child\b",
    r"\bin your childhood\b",
    r"\bused to\b",
    r"\bgrew up\b",
    r"\bgrowing up\b",
    r"\bthe last time\b",
    r"\bthe first time\b",
    r"\bwhat made you\b",
    r"\bcan you remember\b",
    r"\ban experience (that|where|when)\b",  # "Do you have an experience that..."
]

# Past patterns that should NOT trigger if the question is a comparison/evaluation
# (e.g. "more than in the past", "has changed" in analytical context)
# These are excluded from past detection.
PAST_EXCLUSIONS = [
    r"\bin the past\b",           # often used in comparison: "more than in the past"
    r"\bhas .{0,20}changed\b",   # "has technology changed" = present evaluation
    r"\bhave .{0,20}changed\b",  # "have things changed" = present evaluation
    r"\bbefore\b",               # "before giving advice" = sequence, not past time
]


# ---------------------------------------------------------------------------
# Future signals — checked second
# ---------------------------------------------------------------------------
FUTURE_PATTERNS = [
    # Future tense ("going to" excluded — too ambiguous with "going to [place]")
    r"\bwill\b",
    r"\bin the future\b",

    # Plans
    r"\bplans? for\b",
    r"\bplan to\b",
    r"\bnext (five|ten|few|couple)?\s*(years?|months?|stage)\b",

    # Hypothetical / subjunctive (only unreal conditionals, not "if you live in...")
    r"\bwould you like\b",
    r"\bif you could\b",
    r"\bif you were\b",
    r"\bif you had\b",
    r"\bif you (didn't|did not|weren't|could not|couldn't)\b",
    r"\bimagine\b",
    r"\bwould you (want|prefer|rather|choose|consider)\b",

    # Desire / aspiration
    r"\bwant to\b",
    r"\bwould like to\b",
    r"\bhope to\b",
    r"\blooking forward to\b",
    r"\bwish\b",
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def clean(text):
    """Strip leading question number and lowercase."""
    return re.sub(r'^\d+[\.\)]\s*', '', text.lower().strip())


def classify_time_frame(text):
    """Returns 'past', 'future', or 'present'."""
    t = clean(text)

    # Check past first (strong signals only)
    for p in PAST_PATTERNS:
        if re.search(p, t):
            return "past"

    # Check future second
    for p in FUTURE_PATTERNS:
        if re.search(p, t):
            return "future"

    # Default
    return "present"


# ---------------------------------------------------------------------------
# Processors
# ---------------------------------------------------------------------------

def process_file(filepath, part, dry_run=False, overwrite=False):
    with open(filepath, encoding='utf-8') as f:
        data = json.load(f)

    stats = {"past": 0, "present": 0, "future": 0}
    tagged = 0
    skipped = 0
    samples = {"past": [], "present": [], "future": []}

    for topic in data:
        topic_name = topic.get('topic_en', topic.get('topic', 'unknown'))
        questions_key = 'questions' if part == 1 else 'part3'

        for q in topic.get(questions_key, []):
            if q.get('time_frame') and not overwrite:
                skipped += 1
                continue

            tf = classify_time_frame(q['text'])
            q['time_frame'] = tf
            stats[tf] += 1
            tagged += 1

            # Collect samples (up to 5 per category)
            if len(samples[tf]) < 5:
                samples[tf].append(f"  [{topic_name}] {q['text']}")

    # Print summary
    print(f"\n{'[DRY RUN] ' if dry_run else ''}Time frame tagging — Part {part}")
    print(f"  Tagged: {tagged}  |  Skipped (already tagged): {skipped}")
    print(f"  past: {stats['past']}  |  present: {stats['present']}  |  future: {stats['future']}")

    for tf in ['past', 'present', 'future']:
        if samples[tf]:
            print(f"\n  Sample {tf}:")
            for s in samples[tf]:
                print(s)

    if not dry_run:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"\nWrote {filepath}")

        # Auto-regenerate .txt mirror
        txt_script = Path(__file__).parent.parent / 'human-in-the-loop' / 'json_to_txt.py'
        if txt_script.exists():
            print("Regenerating .txt mirror...")
            subprocess.run([sys.executable, str(txt_script), str(filepath)], check=True)
    else:
        print("\nNo changes written (dry run).")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python3 pipeline/tag_time_frames.py merged_part1.json --part 1")
        print("  python3 pipeline/tag_time_frames.py merged_part2.json")
        print("  Add --dry-run to preview without writing")
        print("  Add --overwrite to re-tag already tagged questions")
        sys.exit(1)

    filepath = sys.argv[1]
    part = 2
    if '--part' in sys.argv:
        idx = sys.argv.index('--part')
        if idx + 1 < len(sys.argv):
            part = int(sys.argv[idx + 1])

    dry_run = '--dry-run' in sys.argv
    overwrite = '--overwrite' in sys.argv

    process_file(filepath, part, dry_run=dry_run, overwrite=overwrite)


if __name__ == '__main__':
    main()
