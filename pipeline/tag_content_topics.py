"""
tag_new_topics.py
Tags topics in merged_part2.json where content_tags = [].

Step 1 — Python lookup: fuzzy-match untagged topics against already-tagged ones.
         If match >= 85%, copy tags directly. No Claude needed.
Step 2 — Claude batch: collect remaining unmatched topics, print ONE prompt.
         You paste the prompt into Claude Code, get JSON response, paste back.
         Script then writes tags back to merged_part2.json.

Usage:
    # Step 1+2 prompt generation:
    python3 pipeline/tag_new_topics.py merged_part2.json

    # After you get Claude's response, save it to claude_tag_response.json, then:
    python3 pipeline/tag_new_topics.py merged_part2.json --apply claude_tag_response.json

Requires: pip3 install thefuzz python-Levenshtein
"""

import json
import sys
import re
from pathlib import Path
from thefuzz import fuzz

THRESHOLD = 85


def fuzzy_copy_tags(untagged, tagged_topics):
    """
    For each untagged topic, try to find a tagged topic with similar name.
    Returns (copied_count, still_untagged list).
    """
    copied = 0
    still_untagged = []

    for topic in untagged:
        best_score, best_match = 0, None
        for tagged in tagged_topics:
            score = fuzz.ratio(
                topic['topic'].lower().strip(),
                tagged['topic'].lower().strip()
            )
            if score > best_score:
                best_score, best_match = score, tagged

        if best_score >= THRESHOLD and best_match:
            topic['content_tags'] = best_match['content_tags'][:]
            copied += 1
            print(f"  [COPIED] {topic['topic'][:60]} <- {best_match['topic'][:60]} ({best_score}%)")
        else:
            still_untagged.append(topic)

    return copied, still_untagged


def build_claude_prompt(untagged_topics, tags_txt_path):
    """
    Builds a single batched prompt for Claude to tag all remaining topics.
    """
    # Load existing tag vocabulary
    tags_vocab = ""
    if Path(tags_txt_path).exists():
        tags_vocab = open(tags_txt_path, encoding='utf-8').read().strip()

    topic_list = "\n".join(
        f"{i+1}. {t['topic']}" for i, t in enumerate(untagged_topics)
    )

    prompt = f"""You are tagging IELTS Speaking Part 2 topics for a question bank.

TAG SYSTEM:
Each topic gets a flat array of 2-4 tags.
- First tag: exactly one of: people / place / object / experience/activity
  - people: topics about a person (you, others, family, celebrities, etc.)
  - place: any location (indoor/outdoor, natural, architectural, etc.)
  - object: any tangible/intangible item (clothes, music, book, movie, technology, food, etc.)
  - experience/activity: anything that happened/is happening/will happen (events, habits, travel, hobbies, work, celebrations, etc.)
- Remaining 1-3 tags: most semantically meaningful words/phrases from the topic

NORMALIZATION RULES:
- Use mid-grain tags, not too specific: job/career/occupation -> work, film/movie -> movie
- Normalize similar sentiments: enjoyed/liked/loved -> likes_dislikes
- Use existing tags from the vocabulary below where possible
- Only create new tags when nothing in the vocabulary fits

EXISTING TAG VOCABULARY (use these first):
{tags_vocab}

TOPICS TO TAG (return JSON only, no other text):
{topic_list}

Return ONLY a JSON array like this:
[
  {{"topic": "exact topic string here", "content_tags": ["experience/activity", "music", "likes_dislikes"]}},
  ...
]
One entry per topic, in the same order as the list above.
"""
    return prompt


def apply_response(data, response_path):
    """Applies Claude's tag response back to merged_part2.json."""
    with open(response_path, encoding='utf-8') as f:
        raw = f.read().strip()

    # Strip markdown code fences if present
    raw = re.sub(r'^```json\s*', '', raw)
    raw = re.sub(r'^```\s*', '', raw)
    raw = re.sub(r'\s*```$', '', raw)

    new_tags = json.loads(raw)

    # Build lookup by topic name
    tag_map = {entry['topic'].lower().strip(): entry['content_tags'] for entry in new_tags}

    applied = 0
    for topic in data:
        key = topic['topic'].lower().strip()
        if key in tag_map:
            topic['content_tags'] = tag_map[key]
            applied += 1

    print(f"Applied tags to {applied} topics.")
    return data


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 tag_new_topics.py merged_part2.json [--apply response.json]")
        sys.exit(1)

    json_path = Path(sys.argv[1])
    tags_txt = "tags/tags.txt"

    with open(json_path, encoding='utf-8') as f:
        data = json.load(f)

    # --apply mode: write Claude's response back to JSON
    if len(sys.argv) == 4 and sys.argv[2] == '--apply':
        data = apply_response(data, sys.argv[3])
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"Updated {json_path}")
        return

    # Separate tagged vs untagged topics
    tagged = [t for t in data if t.get('content_tags')]
    untagged = [t for t in data if not t.get('content_tags')]

    print(f"Total topics: {len(data)}")
    print(f"Already tagged: {len(tagged)}")
    print(f"Untagged: {len(untagged)}\n")

    if not untagged:
        print("All topics already tagged. Nothing to do.")
        return

    # Step 1: fuzzy copy from existing tagged topics
    print("Step 1: Fuzzy-copying tags from similar existing topics...")
    copied, still_untagged = fuzzy_copy_tags(untagged, tagged)
    print(f"\nCopied: {copied}, Still untagged: {len(still_untagged)}")

    # Save copied tags back immediately
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    if not still_untagged:
        print("All topics tagged via lookup. Done.")
        return

    # Step 2: generate Claude prompt for remaining
    print(f"\nStep 2: {len(still_untagged)} topics need Claude tagging.")
    print("Copy the prompt below into Claude Code:\n")
    print("=" * 60)
    print(build_claude_prompt(still_untagged, tags_txt))
    print("=" * 60)
    print("\nPaste the prompt above into Claude Code. Add this at the end of your message:")
    print("  Save your JSON response as claude_tag_response.json in /Users/kathy/Documents/vibe coding/ielts-question-bank-test/")
    print("\nThen run:")
    print(f"  python3 pipeline/tag_new_topics.py {json_path} --apply claude_tag_response.json")


if __name__ == '__main__':
    main()
