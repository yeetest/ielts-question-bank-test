#!/usr/bin/env python3
"""
auto_tag_topics.py
Tags each Part 2 topic in merged_part2.json with:
  content_tags: { category, substance, frame_key }
using tags/content_tags.json as the taxonomy reference.
"""

import json
import os
import re

import spacy

# ── PATHS ─────────────────────────────────────────────────────────────────────
BASE      = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA      = os.path.join(BASE, "merged_part2.json")
TAGS_FILE = os.path.join(BASE, "tags", "content_tags.json")

# ── LOAD ──────────────────────────────────────────────────────────────────────
print("Loading spaCy model...")
nlp = spacy.load("en_core_web_md")

with open(DATA, encoding="utf-8") as f:
    data = json.load(f)

with open(TAGS_FILE, encoding="utf-8") as f:
    taxonomy = json.load(f)

# Pre-encode substance labels for similarity matching
substance_docs = {s: nlp(s) for s in taxonomy["substance"]}
print(f"Loaded {len(data)} topics, {len(substance_docs)} substance labels.\n")

# ── CATEGORY RULES (mirrors bootstrap_taxonomy.py) ────────────────────────────
CATEGORY_RULES = {
    "people":     {"person", "friend", "someone", "sportsperson", "child",
                   "people", "musician", "artist", "athlete"},
    "experience": {"time", "occasion", "event", "dinner", "journey", "trip",
                   "activity", "decision", "habit"},
    "place":      {"place", "building", "park"},
}
CATEGORY_OVERRIDES = {
    "sportsperson":           "people",
    "great dinner":           "experience",
    "area/subject of science": "object",
}

# ── FRAME_KEY RULES ───────────────────────────────────────────────────────────
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

# ── HELPERS ───────────────────────────────────────────────────────────────────
def extract_head_lemma(prompt):
    text = re.sub(r"^Describe\s+(?:a|an|the)\s+", "", prompt, flags=re.I).strip()
    text = re.sub(r"^Describe\s+", "", text, flags=re.I).strip()
    doc    = nlp(text)
    chunks = list(doc.noun_chunks)
    if chunks:
        return chunks[0].root.lemma_.lower()
    return doc[0].lemma_.lower() if doc else text.split()[0].lower()

def assign_category(head_lemma, prompt):
    p_lower  = prompt.lower()
    np_lower = head_lemma  # head_lemma is already a single word; check prompt for phrases
    for trigger, cat in CATEGORY_OVERRIDES.items():
        if trigger in p_lower:
            return cat
    for cat, keywords in CATEGORY_RULES.items():
        if head_lemma in keywords or any(kw in p_lower for kw in keywords):
            return cat
    return "object"

def assign_substance(head_lemma):
    """Find closest substance label by spaCy cosine similarity."""
    lemma_doc   = nlp(head_lemma)
    best_label  = head_lemma   # fallback: use the lemma itself
    best_score  = -1.0
    for label, label_doc in substance_docs.items():
        score = lemma_doc.similarity(label_doc)
        if score > best_score:
            best_score = score
            best_label = label
    return best_label

def assign_frame_key(prompt):
    p = prompt.lower()
    for pattern, tag in FRAME_KEY_RULES:
        if pattern.search(p):
            return tag
    return "null"

# ── TAG ALL TOPICS ────────────────────────────────────────────────────────────
for item in data:
    prompt    = item["cue_card"]["prompt"]
    lemma     = extract_head_lemma(prompt)
    category  = assign_category(lemma, prompt)
    substance = assign_substance(lemma)
    frame_key = assign_frame_key(prompt)

    item["content_tags"] = {
        "category":  category,
        "substance": substance,
        "frame_key": frame_key,
    }

    print(f"[{category:10s} | {substance:10s} | {frame_key:16s}]  {prompt[:55]}")

# ── SAVE ──────────────────────────────────────────────────────────────────────
with open(DATA, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print(f"\nDone. Saved content_tags to {len(data)} topics → {DATA}")
