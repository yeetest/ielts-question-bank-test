"""
dedup_questions.py
Removes duplicate questions within each topic in merged_part1.json and merged_part2.json.
Keeps the best-quality version of each duplicate group.

Usage:
    python3 dedup_questions.py merged_part1.json
    python3 dedup_questions.py merged_part2.json

Requires: pip install thefuzz python-Levenshtein --break-system-packages
"""

import json
import sys
import re
from thefuzz import fuzz  # fuzzy string matching library


def clean_text(text):
    """Strips leading numbering like '1.', '2)', etc. and whitespace for comparison."""
    return re.sub(r'^\d+[\.\)]\s*', '', text).strip()


def score_question(text):
    """
    Scores a question for quality. Higher = better.
    Criteria: length, ends with '?', no leading number remnants.
    """
    score = len(text)  # longer is generally more complete
    if text.strip().endswith('?'):
        score += 20  # bonus for proper question format
    if not re.match(r'^\d+[\.\)]', text):
        score += 10  # bonus for no leading number
    return score


def best_in_group(group):
    """Given a list of question dicts, returns the one with the highest quality score."""
    return max(group, key=lambda q: score_question(q['text']))


def dedup_questions(questions, threshold=85):
    """
    Takes a list of question dicts, returns deduplicated list keeping best version.
    threshold: fuzzy match score 0-100, 85 = very similar but not necessarily identical
    """
    clusters = []  # list of groups, each group = list of similar question dicts
    used = set()   # indices already assigned to a cluster

    for i, q in enumerate(questions):
        if i in used:
            continue
        group = [q]
        used.add(i)
        clean_i = clean_text(q['text'])

        for j, q2 in enumerate(questions):
            if j in used:
                continue
            clean_j = clean_text(q2['text'])
            # fuzz.ratio compares two strings and returns similarity 0-100
            if fuzz.ratio(clean_i.lower(), clean_j.lower()) >= threshold:
                group.append(q2)
                used.add(j)

        clusters.append(group)

    # From each cluster, keep the best question
    deduped = [best_in_group(group) for group in clusters]
    removed = len(questions) - len(deduped)
    return deduped, removed


def process_file(filepath):
    """Loads JSON, deduplicates questions in each topic, writes back."""
    with open(filepath, encoding='utf-8') as f:
        data = json.load(f)

    total_removed = 0

    for topic in data:
        topic_name = topic.get('topic') or topic.get('topic_en', 'unknown')

        # Part 2+3 files use 'part3' key; Part 1 files use 'questions' key
        if 'part3' in topic:
            original = topic['part3']
            cleaned, removed = dedup_questions(original)
            topic['part3'] = cleaned
        elif 'questions' in topic:
            original = topic['questions']
            cleaned, removed = dedup_questions(original)
            topic['questions'] = cleaned
        else:
            continue

        if removed > 0:
            print(f"  [{removed} removed] {topic_name}")
            total_removed += removed

    # Write cleaned data back to the same file
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"\nDone. Total duplicates removed: {total_removed}")
    print(f"Cleaned file saved: {filepath}")


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 dedup_questions.py <jsonfile>")
        sys.exit(1)
    process_file(sys.argv[1])


if __name__ == '__main__':
    main()
