"""
renumber_questions.py
Renumbers questions sequentially within each topic, starting from 1.
Strips any existing leading numbers from question text first.

Usage:
    python3 renumber_questions.py merged_part1.json
    python3 renumber_questions.py merged_part2.json
"""

import json
import sys
import re
from pathlib import Path


def strip_leading_number(text):
    """Removes leading numbering like '1.', '2)', '3 ' from question text."""
    return re.sub(r'^\d+[\.\)]\s*', '', text).strip()


def renumber_questions(questions):
    """Strips old numbers from text and adds clean sequential numbering."""
    for i, q in enumerate(questions, start=1):
        # Strip old number from text
        q['text'] = strip_leading_number(q['text'])
        # Add clean number back
        q['text'] = f"{i}. {q['text']}"
    return questions


def process_file(filepath):
    with open(filepath, encoding='utf-8') as f:
        data = json.load(f)

    total_topics = 0

    for topic in data:
        # Part 2+3 uses 'part3', Part 1 uses 'questions'
        if 'part3' in topic:
            topic['part3'] = renumber_questions(topic['part3'])
            total_topics += 1
        elif 'questions' in topic:
            topic['questions'] = renumber_questions(topic['questions'])
            total_topics += 1

    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"Renumbered {total_topics} topics in {filepath}")


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 renumber_questions.py <jsonfile>")
        sys.exit(1)
    process_file(sys.argv[1])


if __name__ == '__main__':
    main()
