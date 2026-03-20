#!/usr/bin/env python3
"""
ingest_pipeline.py
Ingests a new question bank file into the IELTS question bank.

Pipeline order:
  1. Parse raw file (JSON or TXT)
  2. Clean  (strip Chinese chars, fix spacing, strip numbering)
  3. Format  to exact schema of merged_part1.json / merged_part2.json
  4. Tag topics  (content_tags: category, substance, frame_angle)  — Part 2 only
  5. Tag questions (skill_tags)  — Part 3 only
  6. Write temp_review.txt for human inspection
  7. On approval, merge into existing JSON and optionally commit

Usage:
  python pipeline/ingest_pipeline.py <input_file> --part 1|2 --source tongzhuo|laokaoya [--season "2026-Jan-Apr"] [--merge]
"""

import argparse
import json
import os
import re
import sys

# ── PATHS ─────────────────────────────────────────────────────────────────────
BASE        = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PART1_PATH  = os.path.join(BASE, "merged_part1.json")
PART2_PATH  = os.path.join(BASE, "merged_part2.json")
TAGS_FILE   = os.path.join(BASE, "tags", "content_tags.json")
REVIEW_PATH = os.path.join(BASE, "temp_review.txt")

DEFAULT_SEASON = "2026-Jan-Apr"

# ── STEP 2: CLEAN ─────────────────────────────────────────────────────────────
CHINESE_RE   = re.compile(r'[\u4e00-\u9fff\u3000-\u303f\uff00-\uffef]+')
NUMBERING_RE = re.compile(r'^\s*\d+[\.\)、]\s*')
ZERO_WIDTH   = re.compile(r'[\u200b\u200c\u200d\ufeff]')

def clean_text(text: str) -> str:
    text = ZERO_WIDTH.sub('', text)
    text = CHINESE_RE.sub('', text)
    text = NUMBERING_RE.sub('', text)   # strip leading numbering like "1." "1)" "1、"
    text = re.sub(r'\s+', ' ', text).strip()
    return text


# ── STEP 4: TAG TOPICS ────────────────────────────────────────────────────────
def load_taxonomy():
    with open(TAGS_FILE, encoding="utf-8") as f:
        return json.load(f)

CATEGORY_RULES = {
    "people":     {"person", "friend", "someone", "sportsperson", "child",
                   "people", "musician", "artist", "athlete"},
    "experience": {"time", "occasion", "event", "dinner", "journey", "trip",
                   "activity", "decision", "habit"},
    "place":      {"place", "building", "park"},
}
CATEGORY_OVERRIDES = {
    "sportsperson":            "people",
    "great dinner":            "experience",
    "area/subject of science": "object",
}
FRAME_KEY_RULES = [
    (re.compile(r"would like to|want to",              re.I), "aspiration"),
    (re.compile(r"when you\b|a time you\b|a time when", re.I), "past_experience"),
    (re.compile(r"\b(who|that)\s+\w+s\b",              re.I), "trait"),
    (re.compile(r"you admire|you look up to",           re.I), "admire"),
    (re.compile(r"\bwithout\b",                        re.I), "challenge"),
    (re.compile(r"for the first time|first time",       re.I), "first_time"),
    (re.compile(r"\bimportant\b|has been kept",         re.I), "valued"),
    (re.compile(r"\binteresting\b|\benjoy\b",           re.I), "enjoyment"),
    (re.compile(r"in a foreign country|in another country", re.I), "foreign"),
]

def assign_category(head_lemma, prompt):
    p_lower = prompt.lower()
    for trigger, cat in CATEGORY_OVERRIDES.items():
        if trigger in p_lower:
            return cat
    for cat, keywords in CATEGORY_RULES.items():
        if head_lemma in keywords or any(kw in p_lower for kw in keywords):
            return cat
    return "object"

def assign_frame_key(prompt):
    for pattern, tag in FRAME_KEY_RULES:
        if pattern.search(prompt):
            return tag
    return "null"

def tag_topic(prompt: str, taxonomy: dict) -> dict:
    """Assign content_tags to a Part 2 topic."""
    # Try spaCy for substance; fall back to first noun word
    try:
        import spacy
        nlp = tag_topic._nlp
        text = re.sub(r"^Describe\s+(?:a|an|the)\s+", "", prompt, flags=re.I).strip()
        text = re.sub(r"^Describe\s+", "", text, flags=re.I).strip()
        doc    = nlp(text)
        chunks = list(doc.noun_chunks)
        head_lemma = chunks[0].root.lemma_.lower() if chunks else (doc[0].lemma_.lower() if doc else text.split()[0].lower())

        substance_docs = getattr(tag_topic, '_substance_docs', None)
        if substance_docs is None:
            substance_docs = {s: nlp(s) for s in taxonomy["substance"]}
            tag_topic._substance_docs = substance_docs

        lemma_doc  = nlp(head_lemma)
        best_label = head_lemma
        best_score = -1.0
        for label, label_doc in substance_docs.items():
            score = lemma_doc.similarity(label_doc)
            if score > best_score:
                best_score = score
                best_label = label
        substance = best_label
    except Exception:
        # Fallback: pick first word after stripping "Describe a/an/the"
        text = re.sub(r"^Describe\s+(?:a|an|the)\s+", "", prompt, flags=re.I).strip()
        head_lemma = text.split()[0].lower() if text else "item"
        # Rough substance: match against taxonomy list
        substance = head_lemma if head_lemma in taxonomy["substance"] else "item"

    category  = assign_category(head_lemma, prompt)
    frame_key = assign_frame_key(prompt)

    return {"category": category, "substance": substance, "frame_angle": frame_key}


# Lazy-load spaCy once
def _init_spacy():
    try:
        import spacy
        if not hasattr(tag_topic, '_nlp'):
            print("Loading spaCy model...")
            tag_topic._nlp = spacy.load("en_core_web_md")
    except ImportError:
        pass


# ── STEP 5: TAG QUESTIONS ─────────────────────────────────────────────────────
TAGS_ORDER = ["experience", "frequency", "description", "preference", "evaluation", "analyze", "comparison", "hypothetical"]
TAG_DESCRIPTIONS = {
    "experience":   "past personal actions or events — what you did, saw, tried, or remember",
    "frequency":    "how often or how regularly something happens",
    "description":  "stating current facts, what exists now, what people do, listing things",
    "preference":   "personal likes, dislikes, favorites, enjoyment",
    "evaluation":   "forming judgments, pros and cons, should or shouldn't, agreeing or disagreeing",
    "analyze":      "explaining why something happens, how something works, cause and effect",
    "comparison":   "differences, changes over time, contrasts between things",
    "hypothetical": "future-oriented, imagined scenarios, plans, wishes, predictions",
}
KEYWORD_BOOSTS = {
    "experience":   ["have you", "did you", "when did you", "can you remember"],
    "frequency":    ["how often", "do you usually", "do you often", "every day",
                     "how frequently", "how regularly"],
    "description":  ["what kind of", "what kind", "what are the types", "what types",
                     "what examples", "what are some", "what do people",
                     "in your country", "what is popular", "on what occasion"],
    "preference":   ["do you like", "do you prefer", "favourite", "favorite",
                     "do you enjoy", "which do you prefer"],
    "evaluation":   ["do you think", "what do you think", "do you agree",
                     "is it good", "is it important", "is it better", "is it worth",
                     "should", "advantages and disadvantages", "which is better",
                     "is it easy", "is it necessary", "most important", "necessary"],
    "analyze":      ["why do", "why are", "why is", "how do", "how does",
                     "what influences", "what impact", "what effect",
                     "what causes", "how can", "how did", "how has",
                     "what are the problems", "what problems"],
    "comparison":   ["what are the differences", "difference between", "compared",
                     "better than", "worse than", "has changed", "have changed"],
    "hypothetical": ["would you like", "if you", "will replace", "will change",
                     "will people", "in the future", "will", "imagine"],
}
BOOST  = 0.2
MARGIN = 0.02

def tag_question(text: str) -> list:
    lower = text.lower()
    try:
        import spacy
        nlp = tag_topic._nlp
        tag_docs = getattr(tag_question, '_tag_docs', None)
        if tag_docs is None:
            tag_docs = {tag: nlp(desc) for tag, desc in TAG_DESCRIPTIONS.items()}
            tag_question._tag_docs = tag_docs

        q_doc = nlp(lower)
        scores = {}
        for tag in TAGS_ORDER:
            score = q_doc.similarity(tag_docs[tag])
            for phrase in KEYWORD_BOOSTS[tag]:
                if phrase in lower:
                    score += BOOST
                    break
            scores[tag] = round(score, 4)

        best   = max(scores.values())
        assigned = [tag for tag in TAGS_ORDER if scores[tag] >= best - MARGIN]
        return assigned or ["unclear"]
    except Exception:
        # Keyword-only fallback (no spaCy)
        for tag in TAGS_ORDER:
            for phrase in KEYWORD_BOOSTS[tag]:
                if phrase in lower:
                    return [tag]
        return ["unclear"]


# ── STEP 1+3: PARSE & FORMAT ───────────────────────────────────────────────────
def parse_part1_txt(lines: list, source: str, season: str) -> list:
    """
    Expects blocks like:
      Topic: <topic name>
      1. Question one
      2. Question two
      (blank line separates topics)
    """
    topics = []
    current_topic = None
    current_questions = []

    for raw in lines:
        line = raw.strip()
        if not line:
            if current_topic and current_questions:
                topics.append({
                    "topic_en": current_topic,
                    "part": 1,
                    "season": season,
                    "questions": current_questions,
                    "tags": [],
                })
            current_topic = None
            current_questions = []
            continue

        # Detect topic header
        topic_match = re.match(r'^(?:topic|section)[:\s]+(.+)', line, re.I)
        if topic_match:
            current_topic = clean_text(topic_match.group(1))
            continue

        # Detect numbered question
        if re.match(r'^\d+[\.\)、]', line):
            q_text = clean_text(line)
            if q_text:
                current_questions.append({"text": q_text, "source": source})
            continue

        # Bare line with no number — treat as topic if no topic set yet
        if not current_topic:
            current_topic = clean_text(line)

    if current_topic and current_questions:
        topics.append({
            "topic_en": current_topic,
            "part": 1,
            "season": season,
            "questions": current_questions,
            "tags": [],
        })
    return topics


def parse_part2_txt(lines: list, source: str, season: str) -> list:
    """
    Expects blocks like:
      Describe a <prompt>
      You should say:
        - bullet 1
        - bullet 2
      Part 3:
      1. Question
      (blank line separates topics)
    """
    topics = []
    current = None

    def flush():
        if current and current.get("prompt"):
            topics.append({
                "topic": current["prompt"].lower(),
                "part": 2,
                "season": season,
                "cue_card": {
                    "prompt": current["prompt"],
                    "you_should_say": current.get("bullets", []),
                },
                "part3": current.get("part3", []),
                "tags": [],
                "content_tags": {},
            })

    mode = None   # 'bullets' | 'part3'
    for raw in lines:
        line = raw.strip()
        if not line:
            flush()
            current = None
            mode = None
            continue

        # New cue card
        if re.match(r'^describe\b', line, re.I):
            flush()
            current = {"prompt": clean_text(line), "bullets": [], "part3": []}
            mode = None
            continue

        if current is None:
            continue

        # You should say header
        if re.match(r'^you should say', line, re.I):
            mode = "bullets"
            continue

        # Part 3 header
        if re.match(r'^part\s*3', line, re.I):
            mode = "part3"
            continue

        if mode == "bullets":
            bullet = clean_text(re.sub(r'^[-•*]\s*', '', line))
            if bullet:
                current["bullets"].append(bullet)

        elif mode == "part3":
            q_text = clean_text(line)
            if q_text and re.match(r'^\d+', line):
                current["part3"].append({"text": q_text, "source": source, "skill_tags": []})

    flush()
    return topics


def parse_json_input(data: list, source: str, season: str, part: int) -> list:
    """
    Accept a JSON list already roughly in schema. Cleans text fields.
    """
    out = []
    for item in data:
        if part == 1:
            topic_en = clean_text(item.get("topic_en") or item.get("topic", ""))
            questions = [
                {"text": clean_text(q.get("text", "")), "source": q.get("source", source)}
                for q in item.get("questions", [])
                if q.get("text", "").strip()
            ]
            out.append({
                "topic_en": topic_en,
                "part": 1,
                "season": season,
                "questions": questions,
                "tags": [],
            })
        else:
            cc = item.get("cue_card", {})
            prompt   = clean_text(cc.get("prompt") or item.get("topic", ""))
            bullets  = [clean_text(b) for b in cc.get("you_should_say", []) if b.strip()]
            p3 = [
                {"text": clean_text(q.get("text", "")), "source": q.get("source", source), "skill_tags": []}
                for q in item.get("part3", [])
                if q.get("text", "").strip()
            ]
            out.append({
                "topic": prompt.lower(),
                "part": 2,
                "season": season,
                "cue_card": {"prompt": prompt, "you_should_say": bullets},
                "part3": p3,
                "tags": [],
                "content_tags": {},
            })
    return out


# ── STEP 6: WRITE REVIEW FILE ─────────────────────────────────────────────────
def write_review(items: list, part: int):
    lines = [f"=== TEMP REVIEW — Part {part} ({len(items)} topics) ===\n"]
    for i, item in enumerate(items, 1):
        if part == 1:
            lines.append(f"\n[{i}] Topic: {item['topic_en']}")
            for q in item["questions"]:
                lines.append(f"    • {q['text']}  ({q['source']})")
        else:
            ct  = item.get("content_tags", {})
            cc  = item["cue_card"]
            lines.append(f"\n[{i}] {cc['prompt']}")
            lines.append(f"    Tags: category={ct.get('category')}  substance={ct.get('substance')}  frame_angle={ct.get('frame_angle')}")
            lines.append("    You should say:")
            for b in cc["you_should_say"]:
                lines.append(f"      - {b}")
            if item["part3"]:
                lines.append("    Part 3:")
                for q in item["part3"]:
                    tags_str = ", ".join(q.get("skill_tags", []))
                    lines.append(f"      [{tags_str}] {q['text']}")
    with open(REVIEW_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"\nReview written to: {REVIEW_PATH}")


# ── STEP 7: MERGE ─────────────────────────────────────────────────────────────
def merge_into_existing(new_items: list, part: int):
    target = PART1_PATH if part == 1 else PART2_PATH
    with open(target, encoding="utf-8") as f:
        existing = json.load(f)

    if part == 1:
        existing_keys = {item["topic_en"].lower() for item in existing}
        added = [it for it in new_items if it["topic_en"].lower() not in existing_keys]
    else:
        existing_keys = {item["topic"].lower() for item in existing}
        added = [it for it in new_items if it["topic"].lower() not in existing_keys]

    existing.extend(added)
    with open(target, "w", encoding="utf-8") as f:
        json.dump(existing, f, ensure_ascii=False, indent=2)

    print(f"Merged {len(added)} new topics into {target}  (skipped {len(new_items)-len(added)} duplicates)")


# ── MAIN ──────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="Ingest a new question bank file.")
    parser.add_argument("input_file", help="Path to raw file (JSON or TXT)")
    parser.add_argument("--part",   required=True, choices=["1","2"], help="IELTS part number")
    parser.add_argument("--source", required=True, choices=["tongzhuo","laokaoya"], help="Source name")
    parser.add_argument("--season", default=DEFAULT_SEASON, help=f"Season string (default: {DEFAULT_SEASON})")
    parser.add_argument("--merge",  action="store_true", help="After review, merge into existing JSON")
    args = parser.parse_args()

    part    = int(args.part)
    source  = args.source
    season  = args.season
    infile  = args.input_file

    if not os.path.exists(infile):
        sys.exit(f"Error: file not found: {infile}")

    # ── Step 1: Parse ─────────────────────────────────────────────────────────
    ext = os.path.splitext(infile)[1].lower()
    print(f"Step 1 — Parsing {ext} file: {infile}")

    if ext == ".json":
        with open(infile, encoding="utf-8") as f:
            raw_data = json.load(f)
        items = parse_json_input(raw_data, source, season, part)
    elif ext in (".txt", ".md"):
        with open(infile, encoding="utf-8") as f:
            lines = f.readlines()
        if part == 1:
            items = parse_part1_txt(lines, source, season)
        else:
            items = parse_part2_txt(lines, source, season)
    else:
        sys.exit(f"Unsupported file type: {ext}. Supported: .json, .txt")

    print(f"  Parsed {len(items)} topics.")

    # ── Steps 4+5: Tag ────────────────────────────────────────────────────────
    if part == 2:
        print("Step 4 — Tagging topics (content_tags)...")
        _init_spacy()
        taxonomy = load_taxonomy()
        for item in items:
            prompt = item["cue_card"]["prompt"]
            item["content_tags"] = tag_topic(prompt, taxonomy)
            ct = item["content_tags"]
            print(f"  [{ct['category']:10s}|{ct['substance']:10s}|{ct['frame_angle']:16s}]  {prompt[:55]}")

        print("Step 5 — Tagging questions (skill_tags)...")
        total_q = 0
        for item in items:
            for q in item["part3"]:
                q["skill_tags"] = tag_question(q["text"])
                total_q += 1
        print(f"  Tagged {total_q} Part 3 questions.")

    # ── Step 6: Write review ──────────────────────────────────────────────────
    print("Step 6 — Writing temp_review.txt...")
    write_review(items, part)
    print(f"\nOpen temp_review.txt and check the output.")

    # ── Step 7: Merge ─────────────────────────────────────────────────────────
    if args.merge:
        answer = input("\nMerge into existing JSON? (yes/no): ").strip().lower()
        if answer in ("yes", "y"):
            print("Step 7 — Merging...")
            merge_into_existing(items, part)
        else:
            print("Merge cancelled. Run again with --merge when ready.")
    else:
        print("\nTo merge after reviewing: re-run with --merge flag.")


if __name__ == "__main__":
    main()
