"""
tag_question_types.py
Tags questions with skill_tags and skill_subtype using keyword matching.

Top-level taxonomy (8 types, noun forms):
  experience / frequency / description / preference /
  evaluation / analysis / comparison / hypothetical

Second-level subtypes (24 total, see SUBTYPE_RULES below).

Part 2 (default): targets topic.part3[]
Part 1 (--part 1): targets topic.questions[]

Modes:
  default       — only tags questions where skill_tags is empty
  --overwrite   — re-tags ALL questions (skill_tags + skill_subtype)
  --subtype-only — keeps existing skill_tags, adds/overwrites skill_subtype

Usage:
    python3 pipeline/tag_question_types.py merged_part2.json
    python3 pipeline/tag_question_types.py merged_part1.json --part 1
    python3 pipeline/tag_question_types.py merged_part2.json --overwrite
    python3 pipeline/tag_question_types.py merged_part2.json --subtype-only
    python3 pipeline/tag_question_types.py merged_part2.json --audit
"""

from __future__ import annotations

import json
import re
import sys
import subprocess
from pathlib import Path
from collections import Counter
from typing import Optional


# ---------------------------------------------------------------------------
# Top-level skill tag rules (shared by Part 1 and Part 2)
# Priority order: experience → frequency → description → preference →
#                 evaluation → analysis → comparison → hypothetical
# ---------------------------------------------------------------------------

RULES_PART2 = [
    ("experience", [
        r"^have you\b",
        r"^did you\b",
        r"^what did you\b",
        r"^when did you\b",
        r"^when was\b",
        r"^can you remember\b",
    ]),
    ("frequency", [
        r"^how often\b",
        r"\bdo you usually\b",
        r"\bdo you often\b",
        r"\bevery day\b",
        r"\bhow (frequently|regularly)\b",
    ]),
    ("description", [
        r"^what (is|are|was|were|kind|type|do|did|can|other|examples|sorts)\b",
        r"^which\b",
        r"^how (many|much|long|far)\b",
        r"^tell me\b",
        r"^describe\b",
        r"^can you (describe|tell|explain)\b",
        r"^do (you|people|children|young|old|most)\b",
        r"^is there\b",
        r"^are there\b",
        r"^what (do|did) people\b",
        r"^what (activities|things|jobs|places|ways)\b",
        r"what.*in your country",
        r"what.*popular",
        r"^who (is|are|do)\b",
        r"^where (is|are|do|did)\b",
    ]),
    ("preference", [
        r"\bdo you like\b",
        r"\bdo you prefer\b",
        r"\bwhat (is|was|were) your favou?rite\b",
        r"\bdo you enjoy\b",
        r"\bwhich do you prefer\b",
        r"\bdo you mind\b",
    ]),
    ("evaluation", [
        r"do you think\b",
        r"what do you think\b",
        r"should\b",
        r"shouldn't\b",
        r"is it (important|necessary|good|bad|better|worse|right|wrong|fair|useful|harmful|beneficial|effective|appropriate|reasonable)\b",
        r"do you (agree|believe|support|prefer|consider)\b",
        r"would you (say|recommend|consider)\b",
        r"whether (or not|it is|people should)\b",
        r"(advantages? or disadvantages?|pros? (and|or) cons?)\b",
        r"good (or|and) bad\b",
        r"positive (and|or) negative\b",
        r"important (or|and)\b",
        r"necessary (or|and)\b",
        r"waste of time\b",
        r"worth\b",
        r"what (makes|would make).{0,20}(good|bad|better|ideal)\b",
    ]),
    ("analysis", [
        r"^why\b",
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
    ("comparison", [
        r"\bwhat are the differences\b",
        r"\bare there (any )?differences\b",
        r"\bhas.{0,30}changed\b",
        r"\bhave.{0,30}changed\b",
        r"\bchanges?.{0,20}(taken place|in this|in your|recently)\b",
        r"\bcompared\b",
        r"\b(better|worse) than\b",
        r"\bdifference between\b",
        r"\bsimilarities?\b",
    ]),
    ("hypothetical", [
        r"\bwould you like\b",
        r"\bif you\b",
        r"\bwould you want\b",
        r"\bwould you (prefer|rather|choose)\b",
        r"\bimagine\b",
        r"\bdo you want to\b",
        r"\bwill\b",
        r"\bin the future\b",
        r"\breplace\b.{0,30}\bfuture\b",
    ]),
]


RULES_PART1 = [
    ("experience", [
        r"^have you\b",
        r"^did you\b",
        r"^what did you\b",
        r"^when did you\b",
        r"^when was\b",
        r"^can you remember\b",
        r"^what made you\b",
    ]),
    ("frequency", [
        r"^how often\b",
        r"\bdo you usually\b",
        r"\bdo you often\b",
        r"\bevery day\b",
        r"\bdo you spend\b",
        r"\bdo you always\b",
        r"\bhow (frequently|regularly)\b",
        r"do you.{0,20}\ba lot\b",
    ]),
    ("description", [
        r"^what (is|are|was|were)\b",
        r"^what (city|place|room|name|subject|language|technology|part|work)\b",
        r"^who (is|are|helps|do)\b",
        r"^how do (you|people|they|we|others)\b",
        r"^how long\b",
        r"^when do you\b",
        r"^where (is|are|do|did)\b",
        r"^is there\b",
        r"^is (the|this|that)\b",
        r"^are there\b",
        r"^are (the|team|most|many)\b",
        r"\bare.{0,30}popular\b",
        r"\bis.{0,30}popular\b",
        r"^do you have\b",
        r"^do you know\b",
        r"^do you keep\b",
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
        r"\bdo you take\b",
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
    ]),
    ("analysis", [
        r"^why\b",
        r"^how (does|do|did|has|have|is|are|can)\b",
        r"\bwhat (causes?|reasons?|factors?)\b",
        r"\bwhat (impact|effect|influence|role)\b",
        r"(differences?|similarities?|distinctions?) between",
        r"how.{0,30}(affect|influence|impact|change|shape)",
        r"what (has|have).{0,20}changed",
        r"what (are|were) the (benefits?|advantages?|disadvantages?|drawbacks?|challenges?|problems?|consequences?|results?|effects?)",
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
        r"\bdo you want to\b",
        r"\bhave any plans\b",
        r"\bplans for.{0,15}(next|future|year)\b",
        r"\blooking forward to\b",
        r"\bwill\b",
    ]),
]


# ---------------------------------------------------------------------------
# Second-level subtype rules
# For each top-level skill tag, subtypes are checked in order; first match wins.
# Last entry per skill is the default (empty pattern list = catch-all).
# ---------------------------------------------------------------------------

SUBTYPE_RULES: dict[str, list[tuple[str, list[str]]]] = {
    "experience": [
        ("memory_recall", [
            r"can you remember\b",
            r"what made you\b",
            r"when you were (young|a child|little|small|growing)",
            r"(childhood|as a child)",
        ]),
        ("personal_event", []),
    ],
    "frequency": [
        ("regularity", [
            r"^how often\b",
            r"how (frequently|regularly)\b",
            r"how much (time|money)\b",
            r"how many\b",
        ]),
        ("habit", []),
    ],
    "description": [
        ("listing", [
            r"what (kinds?|types?|sorts?) (of|do)\b",
            r"what (activities|things|jobs|places|ways|methods)\b",
            r"what.*popular\b",
            r"what (do|does|did) people\b",
            r"what can (people|children|we|you)\b",
            r"what (are|were) (some|the main|common)\b",
        ]),
        ("process", [
            r"^how do (you|people|they|we|others)\b",
            r"^how long\b",
            r"^how (many|much|far)\b",
            r"in what way\b",
        ]),
        ("context", [
            r"^where\b",
            r"^when\b",
            r"^who\b",
            r"on what occasion\b",
            r"^is there\b",
            r"^are there\b",
        ]),
        ("features", []),
    ],
    "preference": [
        ("choice", [
            r"do you prefer\b",
            r"which do you prefer\b",
            r"which.*better\b",
            r"favou?rite\b",
            r"or\b",
        ]),
        ("like_dislike", []),
    ],
    "evaluation": [
        ("importance", [
            r"\b(important|necessary|essential|vital|crucial)\b",
        ]),
        ("recommendation", [
            r"\bshould\b",
            r"\bshouldn't\b",
            r"what (should|can|could)\b",
            r"what (makes|would make)\b",
        ]),
        ("judgment", [
            r"\b(good|bad|better|worse|right|wrong|fair|useful|harmful|beneficial|effective|appropriate|reasonable)\b",
            r"(advantages? or disadvantages?|pros? (and|or) cons?)\b",
            r"positive (and|or) negative\b",
            r"waste of time\b",
            r"\bworth\b",
        ]),
        ("agreement", []),
    ],
    "analysis": [
        ("cause_reason", [
            r"^why\b",
            r"what (causes?|reasons?|factors?)\b",
            r"how come\b",
        ]),
        ("pros_cons", [
            r"what (are|were) the (benefits?|advantages?|disadvantages?|drawbacks?|challenges?|problems?|consequences?|results?|effects?)\b",
        ]),
        ("effect_impact", [
            r"what (impact|effect|influence|role)\b",
            r"how.{0,30}(affect|influence|impact|change|shape)\b",
            r"what (has|have).{0,20}changed\b",
            r"to what extent\b",
        ]),
        ("mechanism", []),
    ],
    "comparison": [
        ("difference", [
            r"(differences?|distinctions?) between\b",
            r"what are the differences\b",
            r"are there (any )?differences\b",
            r"difference between\b",
            r"similarities?\b",
        ]),
        ("change_over_time", [
            r"has.{0,30}changed\b",
            r"have.{0,30}changed\b",
            r"changes?.{0,20}(taken place|in this|in your|recently)\b",
            r"\bcompared\b",
        ]),
        ("ranking", []),
    ],
    "hypothetical": [
        ("future_plan", [
            r"do you want to\b",
            r"plans? for\b",
            r"have any plans\b",
            r"looking forward to\b",
        ]),
        ("prediction", [
            r"\bwill\b",
            r"in the future\b",
            r"replace.{0,30}future\b",
        ]),
        ("conditional", []),
    ],
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def clean(text: str) -> str:
    """Strip leading question number and lowercase."""
    return re.sub(r'^\d+[\.\)]\s*', '', text.lower().strip())


def assign_subtype(text: str, primary_tag: str) -> tuple[str, str]:
    """
    Returns (subtype, confidence).
    confidence is "high" if an explicit pattern matched,
    "default" if the catch-all default was used.
    """
    t = clean(text)
    rules = SUBTYPE_RULES.get(primary_tag)
    if not rules:
        return "", "none"

    for subtype, patterns in rules:
        if not patterns:
            return subtype, "default"
        for p in patterns:
            if re.search(p, t):
                return subtype, "high"

    return rules[-1][0], "default"


def tag_p2(text: str) -> list[str]:
    t = clean(text)
    tags = []
    for tag, patterns in RULES_PART2:
        for p in patterns:
            if re.search(p, t):
                if tag not in tags:
                    tags.append(tag)
                break
    return tags if tags else ["description"]


def tag_p1(text: str) -> tuple[list[str], bool]:
    """
    Returns (tags, unclear).
    Iterates all rule groups in priority order, collects every group that
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
# Audit report
# ---------------------------------------------------------------------------

class AuditCollector:
    def __init__(self):
        self.entries: list[dict] = []
        self.top_counts = Counter()
        self.sub_counts = Counter()
        self.confidence_counts = Counter()

    def record(self, part: str, topic: str, q_text: str,
               skill_tags: list, subtype: str, confidence: str):
        primary = skill_tags[0] if skill_tags else "none"
        self.top_counts[primary] += 1
        self.sub_counts[f"{primary}.{subtype}"] += 1
        self.confidence_counts[confidence] += 1
        if confidence != "high":
            self.entries.append({
                "part": part,
                "topic": topic,
                "text": q_text.strip(),
                "skill_tags": skill_tags,
                "subtype": subtype,
                "confidence": confidence,
            })

    def write_report(self, path: Path):
        lines = ["# Skill Subtype Audit Report\n"]

        lines.append("## Top-level coverage\n")
        for tag, count in self.top_counts.most_common():
            lines.append(f"- {tag}: {count}")

        lines.append("\n## Subtype coverage\n")
        for key, count in sorted(self.sub_counts.items()):
            lines.append(f"- {key}: {count}")

        lines.append(f"\n## Confidence\n")
        for c, count in self.confidence_counts.most_common():
            lines.append(f"- {c}: {count}")

        lines.append(f"\n## Low-confidence / default cases ({len(self.entries)})\n")
        lines.append("These used fallback defaults or had no subtype. Review for accuracy.\n")
        for e in self.entries:
            lines.append(f"- **[{e['part']}]** `{e['skill_tags']}` → `{e['subtype']}` ({e['confidence']})")
            lines.append(f"  {e['text']}")
            lines.append(f"  topic: {e['topic']}")
            lines.append("")

        path.write_text("\n".join(lines), encoding="utf-8")
        print(f"Audit report: {path}")


# ---------------------------------------------------------------------------
# Processors
# ---------------------------------------------------------------------------

def process_part2(filepath: str, *, overwrite: bool = False,
                  subtype_only: bool = False, audit: AuditCollector | None = None):
    with open(filepath, encoding='utf-8') as f:
        data = json.load(f)

    tagged = 0
    subtyped = 0
    for topic in data:
        topic_name = topic.get("topic", topic.get("topic_en", "?"))
        for q in topic.get('part3', []):
            if overwrite or not q.get('skill_tags'):
                q['skill_tags'] = tag_p2(q['text'])
                tagged += 1
            if overwrite or subtype_only or 'skill_subtype' not in q:
                primary = q['skill_tags'][0] if q.get('skill_tags') else ""
                sub, conf = assign_subtype(q['text'], primary)
                q['skill_subtype'] = sub
                subtyped += 1
                if audit:
                    audit.record("p3", topic_name, q['text'],
                                 q.get('skill_tags', []), sub, conf)

    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")

    print(f"Part 3: tagged {tagged}, subtyped {subtyped} in {filepath}")


def process_part1(filepath: str, *, overwrite: bool = False,
                  subtype_only: bool = False, audit: AuditCollector | None = None):
    with open(filepath, encoding='utf-8') as f:
        data = json.load(f)

    tagged = 0
    subtyped = 0
    unclear_batch = []

    for topic in data:
        topic_name = topic.get('topic_en', 'unknown')
        for i, q in enumerate(topic.get('questions', [])):
            if overwrite or not q.get('skill_tags'):
                tags, unclear = tag_p1(q['text'])
                q['skill_tags'] = tags
                if unclear:
                    unclear_batch.append({
                        "topic_en": topic_name,
                        "question_index": i,
                        "text": q['text'],
                    })
                else:
                    tagged += 1

            if overwrite or subtype_only or 'skill_subtype' not in q:
                primary = q['skill_tags'][0] if q.get('skill_tags') else ""
                sub, conf = assign_subtype(q['text'], primary)
                q['skill_subtype'] = sub
                subtyped += 1
                if audit:
                    audit.record("p1", topic_name, q['text'],
                                 q.get('skill_tags', []), sub, conf)

    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")

    print(f"Part 1: tagged {tagged}, subtyped {subtyped} in {filepath}")

    if unclear_batch:
        batch_path = Path(filepath).resolve().parent / 'claude_p1_type_response.json'
        with open(batch_path, 'w', encoding='utf-8') as f:
            json.dump(unclear_batch, f, ensure_ascii=False, indent=2)
        print(f"{len(unclear_batch)} unclear questions saved to {batch_path}")
    else:
        print("No unclear questions — all matched.")

    txt_script = Path(__file__).parent.parent / 'human-in-the-loop' / 'json_to_txt.py'
    if txt_script.exists():
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
        print("  python3 pipeline/tag_question_types.py merged_part2.json --overwrite")
        print("  python3 pipeline/tag_question_types.py merged_part2.json --subtype-only")
        print("  python3 pipeline/tag_question_types.py merged_part2.json --audit")
        sys.exit(1)

    filepath = sys.argv[1]
    part = 2
    if '--part' in sys.argv:
        idx = sys.argv.index('--part')
        if idx + 1 < len(sys.argv):
            part = int(sys.argv[idx + 1])

    overwrite = '--overwrite' in sys.argv
    subtype_only = '--subtype-only' in sys.argv
    do_audit = '--audit' in sys.argv or overwrite or subtype_only

    audit = AuditCollector() if do_audit else None

    if part == 1:
        process_part1(filepath, overwrite=overwrite,
                      subtype_only=subtype_only, audit=audit)
    else:
        process_part2(filepath, overwrite=overwrite,
                      subtype_only=subtype_only, audit=audit)

    if audit:
        report_path = Path(__file__).parent.parent / 'human-in-the-loop' / 'skill_subtype_audit.md'
        audit.write_report(report_path)


if __name__ == '__main__':
    main()
