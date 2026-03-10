"""
auto_tag_questions.py
Tags each question in merged_part2.json with type_tags where type_tags = [].
Uses keyword matching — no AI needed.

Tag definitions:
- describe: factual recall, listing, reporting what exists — what, which, how many, how often, tell me about
- analyze: causal/relational reasoning — why, how does X affect Y, what causes, what impact, what effect, differences, similarities
- evaluate: judgment, opinion, recommendation — good/bad, should/shouldn't, agree/disagree, advantages/disadvantages, whether or not, what do you think, better/worse, important or not
- predict: future-oriented — will, in the future, what changes will, what do you think will happen

Tag order: describe → analyze → evaluate → predict
A question can have multiple tags.

Usage:
    python3 pipeline/auto_tag_questions.py merged_part2.json
"""

import json, re, sys

RULES = [
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
        r"a or b\b",
        r"important (or|and)\b",
        r"necessary (or|and)\b",
        r"waste of time\b",
        r"worth\b",
        r"what (makes|would make).{0,20}(good|bad|better|ideal)\b",
    ]),
    ("predict", [
        r"\bwill\b",
        r"in the future\b",
        r"what changes? will\b",
        r"what do you think will\b",
        r"what would happen\b",
        r"what.{0,20}(likely|probably|going to)\b",
        r"do you think.{0,30}will\b",
    ]),
]


def tag_question(text):
    """Returns ordered list of type tags for a question."""
    text_lower = re.sub(r'^\d+[\.\)]\s*', '', text.lower().strip())
    tags = []
    for tag, patterns in RULES:
        for pattern in patterns:
            if re.search(pattern, text_lower):
                if tag not in tags:
                    tags.append(tag)
                break
    if not tags:
        tags = ["describe"]  # fallback
    return tags


def process_file(filepath):
    with open(filepath, encoding='utf-8') as f:
        data = json.load(f)

    tagged = 0
    for topic in data:
        for q in topic.get('part3', []):
            if not q.get('type_tags'):
                q['type_tags'] = tag_question(q['text'])
                tagged += 1

    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"Tagged {tagged} questions in {filepath}")


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 auto_tag_questions.py merged_part2.json")
        sys.exit(1)
    process_file(sys.argv[1])


if __name__ == '__main__':
    main()
