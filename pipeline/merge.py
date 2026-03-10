"""
merge.py
Generic merger — reads from staging folder and merges into project JSONs.

Reads:
    /Users/kathy/Documents/raw source/parsed/part1_to_merge.json
    /Users/kathy/Documents/raw source/parsed/part2_to_merge.json

Writes to (project root):
    merged_part1.json
    merged_part2.json

Usage (run from project root):
    python3 pipeline/merge.py

Requires: pip3 install thefuzz python-Levenshtein
"""

import json
import re
from pathlib import Path
from thefuzz import fuzz

PARSED_DIR = Path("/Users/kathy/Documents/raw source/parsed")
THRESHOLD = 85


def strip_leading_number(text):
    """Removes leading '1.' / '2)' numbering for clean comparison."""
    return re.sub(r'^\d+[\.\)]\s*', '', text).strip()


def find_matching_topic(name, existing, key):
    """
    Fuzzy-matches name against existing topics on field key.
    Returns index of best match above THRESHOLD, or -1.
    """
    best_score, best_idx = 0, -1
    for i, t in enumerate(existing):
        score = fuzz.ratio(name.lower().strip(), t.get(key, '').lower().strip())
        if score > best_score:
            best_score, best_idx = score, i
    return best_idx if best_score >= THRESHOLD else -1


def question_exists(new_text, existing_questions):
    """Returns True if a similar question already exists."""
    clean_new = strip_leading_number(new_text).lower()
    for q in existing_questions:
        if fuzz.ratio(clean_new, strip_leading_number(q['text']).lower()) >= THRESHOLD:
            return True
    return False


def renumber(questions):
    """Renumbers questions sequentially, stripping old numbers first."""
    for i, q in enumerate(questions, 1):
        q['text'] = f"{i}. {strip_leading_number(q['text'])}"
    return questions


def merge_part1(existing, new_topics):
    added_topics = added_questions = 0
    for new in new_topics:
        idx = find_matching_topic(new['topic_en'], existing, 'topic_en')
        if idx == -1:
            existing.append(new)
            added_topics += 1
            print(f"  [NEW TOPIC] {new['topic_en']}")
        else:
            qs = existing[idx]['questions']
            for q in new['questions']:
                if not question_exists(q['text'], qs):
                    qs.append(q)
                    added_questions += 1
            existing[idx]['questions'] = renumber(qs)
    print(f"Part 1: {added_topics} new topics, {added_questions} new questions added")
    return existing


def merge_part2(existing, new_topics):
    added_topics = added_questions = 0
    for new in new_topics:
        idx = find_matching_topic(new['topic'], existing, 'topic')
        if idx == -1:
            existing.append(new)
            added_topics += 1
            print(f"  [NEW TOPIC] {new['topic']}")
        else:
            qs = existing[idx]['part3']
            for q in new['part3']:
                if not question_exists(q['text'], qs):
                    qs.append(q)
                    added_questions += 1
            existing[idx]['part3'] = renumber(qs)
    print(f"Part 2+3: {added_topics} new topics, {added_questions} new questions added")
    return existing


def main():
    # Load staging files
    p1_staging = PARSED_DIR / "part1_to_merge.json"
    p2_staging = PARSED_DIR / "part2_to_merge.json"

    if not p1_staging.exists() or not p2_staging.exists():
        print("Error: staging files not found. Run the parser first.")
        return

    with open(p1_staging, encoding='utf-8') as f:
        new_part1 = json.load(f)
    with open(p2_staging, encoding='utf-8') as f:
        new_part2 = json.load(f)

    # Load existing merged files
    with open('merged_part1.json', encoding='utf-8') as f:
        part1 = json.load(f)
    with open('merged_part2.json', encoding='utf-8') as f:
        part2 = json.load(f)

    print("Merging Part 1...")
    part1 = merge_part1(part1, new_part1)

    print("\nMerging Part 2+3...")
    part2 = merge_part2(part2, new_part2)

    # Write back
    with open('merged_part1.json', 'w', encoding='utf-8') as f:
        json.dump(part1, f, ensure_ascii=False, indent=2)
    with open('merged_part2.json', 'w', encoding='utf-8') as f:
        json.dump(part2, f, ensure_ascii=False, indent=2)

    print("\nDone. Review merged files, then run json_to_txt.py to inspect before pushing.")


if __name__ == '__main__':
    main()
