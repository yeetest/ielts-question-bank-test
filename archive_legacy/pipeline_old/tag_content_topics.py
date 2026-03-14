"""
tag_content_topics.py
Tags topics with content_tags where content_tags is missing or empty.

Step 1 — Fuzzy lookup: match untagged topics against already-tagged ones.
         If match >= 85%, copy tags directly. No Claude needed.
Step 2 — Claude batch: print ONE prompt for remaining untagged topics.
         Paste prompt into Claude, get JSON response, save file, then --apply.

Supports both Part 1 and Part 2.
  Part 1 uses topic field: topic_en   (short abstract nouns, 2-3 tags)
  Part 2 uses topic field: topic      (full sentence prompts, 2-4 tags)

Usage:
    # Step 1 + generate Step 2 prompt:
    python3 pipeline/tag_content_topics.py merged_part2.json
    python3 pipeline/tag_content_topics.py merged_part1.json --part 1

    # After saving Claude's JSON response:
    python3 pipeline/tag_content_topics.py merged_part2.json --apply claude_tag_response.json
    python3 pipeline/tag_content_topics.py merged_part1.json --part 1 --apply claude_tag_response.json

Requires: pip3 install thefuzz python-Levenshtein
"""

import json
import sys
import re
from pathlib import Path
from thefuzz import fuzz

THRESHOLD = 85


def topic_name(topic, part):
    """Return the topic string for a given part."""
    return topic['topic_en'] if part == 1 else topic['topic']


def fuzzy_copy_tags(untagged, tagged_topics, part):
    """
    For each untagged topic, try to find a tagged topic with similar name.
    Returns (copied_count, still_untagged list).
    """
    copied = 0
    still_untagged = []

    for topic in untagged:
        best_score, best_match = 0, None
        name = topic_name(topic, part).lower().strip()
        for tagged in tagged_topics:
            score = fuzz.ratio(name, topic_name(tagged, part).lower().strip())
            if score > best_score:
                best_score, best_match = score, tagged

        if best_score >= THRESHOLD and best_match:
            topic['content_tags'] = best_match['content_tags'][:]
            copied += 1
            print(f"  [COPIED] {name[:55]} <- {topic_name(best_match, part)[:55]} ({best_score}%)")
        else:
            still_untagged.append(topic)

    return copied, still_untagged


def build_claude_prompt(untagged_topics, tags_txt_path, part):
    """Builds a single batched prompt for Claude to tag all remaining topics."""
    tags_vocab = ""
    if Path(tags_txt_path).exists():
        tags_vocab = open(tags_txt_path, encoding='utf-8').read().strip()

    topic_list = "\n".join(
        f"{i+1}. {topic_name(t, part)}" for i, t in enumerate(untagged_topics)
    )

    if part == 1:
        part_header = "IELTS Speaking Part 1"
        tag_count = "2-3 tags"
        tag_count_detail = "- Remaining 1-2 tags: most semantically meaningful word(s) from the topic name"
        topic_note = """NOTE: Part 1 topics are short abstract nouns or phrases (e.g. "Food", "Reading", "Shoes").
- If the topic is an activity or habit (Reading, Walking, Chatting, Typing, Hobby) → use experience/activity even though it looks like a noun.
- Keep thematic tags to 1-2 — these topics are abstract so fewer tags are more precise."""
        json_key = "topic_en"
    else:
        part_header = "IELTS Speaking Part 2"
        tag_count = "2-4 tags"
        tag_count_detail = "- Remaining 1-3 tags: most semantically meaningful words/phrases from the topic"
        topic_note = ""
        json_key = "topic"

    prompt = f"""You are tagging {part_header} topics for a question bank.

TAG SYSTEM:
Each topic gets a flat array of {tag_count}.
- First tag: exactly one of: people / place / object / experience/activity
  - people: topics about a person (you, others, family, celebrities, etc.)
  - place: any location (indoor/outdoor, natural, architectural, etc.)
  - object: any tangible/intangible item (clothes, music, book, movie, technology, food, etc.)
  - experience/activity: anything that happened/is happening/will happen (events, habits, travel, hobbies, work, celebrations, etc.)
{tag_count_detail}
{topic_note}

NORMALIZATION RULES:
- Use mid-grain tags, not too specific: job/career/occupation -> work, film/movie -> movies
- Normalize similar sentiments: enjoyed/liked/loved -> likes_dislikes
- Use existing tags from the vocabulary below where possible
- Only create new tags when nothing in the vocabulary fits

EXISTING TAG VOCABULARY (use these first):
{tags_vocab}

TOPICS TO TAG (return JSON only, no other text):
{topic_list}

Return ONLY a JSON array like this:
[
  {{"{json_key}": "exact topic string here", "content_tags": ["experience/activity", "music", "likes_dislikes"]}},
  ...
]
One entry per topic, in the same order as the list above.
"""
    return prompt, json_key


def apply_response(data, response_path, part):
    """Applies Claude's tag response back to the JSON file."""
    with open(response_path, encoding='utf-8') as f:
        raw = f.read().strip()

    # Strip markdown code fences if present
    raw = re.sub(r'^```json\s*', '', raw, flags=re.MULTILINE)
    raw = re.sub(r'^```\s*', '', raw, flags=re.MULTILINE)
    raw = re.sub(r'\s*```$', '', raw.strip())

    new_tags = json.loads(raw)

    json_key = 'topic_en' if part == 1 else 'topic'
    tag_map = {entry[json_key].lower().strip(): entry['content_tags'] for entry in new_tags}

    applied = 0
    for topic in data:
        key = topic_name(topic, part).lower().strip()
        if key in tag_map:
            topic['content_tags'] = tag_map[key]
            applied += 1

    print(f"Applied tags to {applied} topics.")
    return data


def main():
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python3 pipeline/tag_content_topics.py merged_part2.json")
        print("  python3 pipeline/tag_content_topics.py merged_part1.json --part 1")
        print("  python3 pipeline/tag_content_topics.py merged_part2.json --apply claude_tag_response.json")
        print("  python3 pipeline/tag_content_topics.py merged_part1.json --part 1 --apply claude_tag_response.json")
        sys.exit(1)

    args = sys.argv[1:]
    json_path = Path(args[0])
    part = 1 if '--part' in args and args[args.index('--part') + 1] == '1' else 2
    tags_txt = Path(json_path).resolve().parent / 'tags' / 'tags.txt'

    with open(json_path, encoding='utf-8') as f:
        data = json.load(f)

    # --apply mode
    if '--apply' in args:
        response_path = args[args.index('--apply') + 1]
        data = apply_response(data, response_path, part)
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"Updated {json_path}")
        # Regenerate .txt mirror
        import subprocess
        txt_script = Path(__file__).parent.parent / 'human-in-the-loop' / 'json_to_txt.py'
        subprocess.run([sys.executable, str(txt_script), str(json_path)], check=True)
        return

    # Separate tagged vs untagged
    tagged = [t for t in data if t.get('content_tags')]
    untagged = [t for t in data if not t.get('content_tags')]

    print(f"Part {part} | Total topics: {len(data)}")
    print(f"Already tagged: {len(tagged)}")
    print(f"Untagged: {len(untagged)}\n")

    if not untagged:
        print("All topics already tagged. Nothing to do.")
        return

    # Step 1: fuzzy copy
    print("Step 1: Fuzzy-copying tags from similar existing topics...")
    copied, still_untagged = fuzzy_copy_tags(untagged, tagged, part)
    print(f"\nCopied: {copied}, Still untagged: {len(still_untagged)}")

    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    if not still_untagged:
        print("All topics tagged via lookup. Done.")
        return

    # Step 2: generate Claude prompt
    print(f"\nStep 2: {len(still_untagged)} topics need Claude tagging.")
    print("Copy the prompt below into Claude:\n")
    print("=" * 60)
    prompt, _ = build_claude_prompt(still_untagged, tags_txt, part)
    print(prompt)
    print("=" * 60)
    print("\nSave Claude's JSON response as claude_tag_response.json, then run:")
    print(f"  python3 pipeline/tag_content_topics.py {json_path} {'--part 1 ' if part == 1 else ''}--apply claude_tag_response.json")


if __name__ == '__main__':
    main()
