"""
tag_question_types.py
Tags questions with type_tags using keyword matching.

Part 2 (default): targets topic.part3[] with 4-type taxonomy
  (describe / analyze / evaluate / predict)
  Fallback: ["describe"]

Part 1 (--part 1): targets topic.questions[] with 7-type taxonomy
  (experience / frequency / description / preference / evaluation / comparison / hypothetical)
  Priority order: experience → frequency → description → preference → evaluation → comparison → hypothetical
  1–3 tags per question (all matching rule groups, capped at 3, in priority order)
  Unmatched → type_tags: [], saved to claude_p1_type_response.json for Claude batch
  After tagging, auto-runs json_to_txt.py on the input file.

Usage:
    python3 pipeline/tag_question_types.py merged_part2.json
    python3 pipeline/tag_question_types.py merged_part1.json --part 1
"""

import json
import re
import sys
import subprocess
from pathlib import Path


# ---------------------------------------------------------------------------
# Part 2 — 4-type taxonomy (unchanged)
# ---------------------------------------------------------------------------

RULES_PART2 = [
    ("describe", [
        r"^what (is|are|was|were|kind|type|do|did|can|other|examples|sorts)\b",
        r"^which\b",
        r"^how (many|much|often|long|far|frequently)\b",
        r"^tell me\b",
        r"^describe\b",
        r"^can you (describe|tell|explain)\b",
        r"^do (you|people|children|young|old|most)\b",
        r"^have you\b",
        r"^did you\b",
        r"^is there\b",
        r"^are there\b",
        r"^what (do|did) people\b",
        r"^what (activities|things|jobs|places|ways)\b",
        r"what.*in your country",
        r"what.*popular",
    ]),
    ("analyze", [
        r"\bwhy\b",
        r"\bhow (does|do|did|has|have)\b",
        r"what (causes?|reasons?|factors?)\b",
        r"what (impact|effect|influence|role)\b",
        r"(differences?|similarities?|distinctions?) between",
        r"how.{0,30}(affect|influence|impact|change|shape)",
        r"what (has|have).{0,20}changed",
        r"what (are|were) the (benefits?|advantages?|disadvantages?|drawbacks?|challenges?|problems?|consequences?|results?|effects?)",
        r"how come\b",
        r"in what way",
        r"to what extent",
    ]),
    ("evaluate", [
        r"do you think\b",
        r"what do you think\b",
        r"should\b",
        r"shouldn't\b",
        r"is it (important|necessary|good|bad|better|worse|right|wrong|fair|useful|harmful|beneficial|effective|appropriate|reasonable)\b",
        r"do you (agree|believe|support|prefer|consider)\b",
        r"would you (say|recommend|consider|prefer)\b",
        r"whether (or not|it is|people should)\b",
        r"(better|worse) (than|for|to)\b",
        r"(advantages? or disadvantages?|pros? (and|or) cons?)\b",
        r"good (or|and) bad\b",
        r"positive (and|or) negative\b",
        r"important (or|and)\b",
        r"necessary (or|and)\b",
        r"waste of time\b",
        r"worth\b",
        r"what (makes|would make).{0,20}(good|bad|better|ideal)\b",
    ]),
    ("predict", [
        r"\bwill\b",
        r"\bin the future\b",
        r"\breplace\b.{0,30}\bfuture\b",
    ]),
]


# ---------------------------------------------------------------------------
# Part 1 — 7-type taxonomy, priority order
# ---------------------------------------------------------------------------

RULES_PART1 = [
    ("experience", [
        r"^have you\b",                         # "Have you seen/been/learned/heard" (was "have you ever")
        r"^did you\b",
        r"^what did you\b",
        r"^when did you\b",
        r"^when was\b",                          # "When was the last time you..."
        r"^can you remember\b",                  # "Can you remember the dreams you had?"
        r"^what made you\b",                     # "What made you happy when you were little?"
    ]),
    ("frequency", [
        r"^how often\b",
        r"\bdo you usually\b",
        r"\bdo you often\b",
        r"\bevery day\b",
        r"\bdo you spend\b",
        r"\bdo you always\b",
        r"\bhow (frequently|regularly)\b",
        r"do you.{0,20}\ba lot\b",               # "Do you walk a lot?"
    ]),
    ("description", [
        r"^what (is|are|was|were)\b",
        r"^what (city|place|room|name|subject|language|technology|part|work)\b", # "What city do you live in?"
        r"^who (is|are|helps|do)\b",              # "Who do you live with?"
        r"^how do (you|people|they|we|others)\b",
        r"^how long\b",
        r"^when do you\b",
        r"^where (is|are|do|did)\b",
        r"^is there\b",
        r"^is (the|this|that)\b",                 # "Is the city friendly?", "Is that a big city?"
        r"^are there\b",
        r"^are (the|team|most|many)\b",            # "Are the people friendly?", "Are team sports popular?"
        r"\bare.{0,30}popular\b",                  # "Is/Are … popular in your culture?"
        r"\bis.{0,30}popular\b",
        r"^do you have\b",
        r"^do you know\b",
        r"^do you keep\b",                         # "Do you keep plants at home?"
        r"^do you work\b",
        r"^do you live\b",
        r"^what (kind|type|subjects?|technology|requirements?|do you do)\b",
        r"^what kind\b",
        r"^what type\b",
        r"^describe\b",
        r"^please describe\b",
        r"^can you describe\b",
        r"^tell me\b",
        r"^what (do|does) your\b",
        r"^what (does|do).{0,20}look like\b",
    ]),
    ("preference", [
        r"\bdo you like\b",
        r"\bdo you prefer\b",
        r"\bwhat (is|was|were) your favou?rite\b",
        r"\bdo you enjoy\b",
        r"\bwhich do you prefer\b",
        r"\bdo you mind\b",
        r"\bdo you take\b",                        # "Do you take photos of buildings?"
    ]),
    ("evaluation", [
        r"\bdo you think\b",
        r"\bis it important\b",
        r"\bwhat do you consider\b",
        r"\bdo you think you'?re good\b",
        r"\bshould\b",
        r"\bdo you (agree|believe)\b",
        r"\bis.{0,30}(important|necessary|good|bad|right|wrong|fair|useful|beneficial|interesting)\b",
        r"\bare.{0,30}(important|necessary|good|bad|right|wrong|fair|useful|beneficial)\b",
        r"\bworth\b",
        r"\bwhat (makes|would make)\b",
        r"^why\b",                                # "Why do people like ...?" (not trailing "Why?/Why not?")
    ]),
    ("comparison", [
        r"\bwhat are the differences\b",
        r"\bare there (any )?differences\b",
        r"\bhas.{0,30}changed\b",
        r"\bhave.{0,30}changed\b",
        r"\bchanges?.{0,20}(taken place|in this|in your|recently)\b",
        r"\bcompared\b",
        r"\b(better|worse) than\b",
        r"\bdifference between\b",
        r"\bunlike\b",
        r"\bsame as\b",
        r"\bsimilarities?\b",
    ]),
    ("hypothetical", [
        r"\bwould you like\b",
        r"\bif you\b",
        r"\bif you had\b",
        r"\bwould you want\b",
        r"\bwould you (prefer|rather|choose)\b",
        r"\bimagine\b",
        r"\bdo you want to\b",                   # "Do you want to change your major?"
        r"\bhave any plans\b",                   # "Do you have any plans for..."
        r"\bplans for.{0,15}(next|future|year)\b",
        r"\blooking forward to\b",               # "Are you looking forward to working?"
        r"\bwill\b",                             # future questions (no predict type in Part 1)
    ]),
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def clean(text):
    """Strip leading question number and lowercase."""
    return re.sub(r'^\d+[\.\)]\s*', '', text.lower().strip())


def tag_p2(text):
    t = clean(text)
    tags = []
    for tag, patterns in RULES_PART2:
        for p in patterns:
            if re.search(p, t):
                if tag not in tags:
                    tags.append(tag)
                break
    return tags if tags else ["describe"]


def tag_p1(text):
    """
    Returns (tags, unclear).
    Iterates all 7 rule groups in priority order, collects every group that
    matches (up to 3 tags total). If nothing matches, returns ([], True).
    """
    t = clean(text)
    tags = []
    for tag, patterns in RULES_PART1:
        for p in patterns:
            if re.search(p, t):
                tags.append(tag)
                break
        if len(tags) == 3:
            break
    if not tags:
        return [], True
    return tags, False


# ---------------------------------------------------------------------------
# Processors
# ---------------------------------------------------------------------------

def process_part2(filepath):
    with open(filepath, encoding='utf-8') as f:
        data = json.load(f)

    tagged = 0
    for topic in data:
        for q in topic.get('part3', []):
            if not q.get('type_tags'):
                q['type_tags'] = tag_p2(q['text'])
                tagged += 1

    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"Tagged {tagged} Part 3 questions in {filepath}")


def process_part1(filepath):
    with open(filepath, encoding='utf-8') as f:
        data = json.load(f)

    tagged = 0
    unclear_batch = []

    for topic in data:
        topic_name = topic.get('topic_en', 'unknown')
        for i, q in enumerate(topic.get('questions', [])):
            if not q.get('type_tags'):
                tags, unclear = tag_p1(q['text'])
                q['type_tags'] = tags
                if unclear:
                    unclear_batch.append({
                        "topic_en": topic_name,
                        "question_index": i,
                        "text": q['text'],
                    })
                else:
                    tagged += 1

    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"Tagged {tagged} Part 1 questions in {filepath}")

    if unclear_batch:
        batch_path = Path(filepath).resolve().parent / 'claude_p1_type_response.json'
        with open(batch_path, 'w', encoding='utf-8') as f:
            json.dump(unclear_batch, f, ensure_ascii=False, indent=2)
        print(f"{len(unclear_batch)} unclear questions saved to {batch_path}")
    else:
        print("No unclear questions — all matched.")

    # Auto-regenerate .txt mirror
    txt_script = Path(__file__).parent.parent / 'human-in-the-loop' / 'json_to_txt.py'
    print(f"\nRegenerating .txt mirror...")
    subprocess.run([sys.executable, str(txt_script), str(filepath)], check=True)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python3 pipeline/tag_question_types.py merged_part2.json")
        print("  python3 pipeline/tag_question_types.py merged_part1.json --part 1")
        sys.exit(1)

    filepath = sys.argv[1]
    part = 2
    if '--part' in sys.argv:
        idx = sys.argv.index('--part')
        if idx + 1 < len(sys.argv):
            part = int(sys.argv[idx + 1])

    if part == 1:
        process_part1(filepath)
    else:
        process_part2(filepath)


if __name__ == '__main__':
    main()
