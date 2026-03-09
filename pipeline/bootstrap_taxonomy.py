#!/usr/bin/env python3
"""
bootstrap_taxonomy.py
Processes 52 Part 2 topic prompts and writes tags/content_tags.json
and taxonomy_review.txt for manual verification.
"""

import json
import os
import re
from collections import Counter

import spacy

# ── PATHS ─────────────────────────────────────────────────────────────────────
BASE       = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA       = os.path.join(BASE, "merged_part2.json")
TAGS_OUT   = os.path.join(BASE, "tags", "content_tags.json")
REVIEW_OUT = os.path.join(BASE, "taxonomy_review.txt")

# ── CATEGORY RULES ────────────────────────────────────────────────────────────
# head_lemma or noun_phrase keyword → category (first match wins)
CATEGORY_RULES = {
    "people":     {"person", "friend", "someone", "sportsperson", "child",
                   "people", "musician", "artist", "athlete"},
    "experience": {"time", "occasion", "event", "dinner", "journey", "trip",
                   "activity", "decision", "habit"},
    "place":      {"place", "building", "park"},   # "area" removed → no longer triggers place
}
# Prompt-level overrides applied after head-lemma rules
CATEGORY_OVERRIDES = {
    "sportsperson": "people",
    "great dinner":  "experience",
    "area/subject of science": "object",
}
# Anything not matched → "object"

# ── FRAME_KEY PATTERN RULES ───────────────────────────────────────────────────
# Applied to the lowercased full prompt. First match wins. Returns tag string.
FRAME_KEY_RULES = [
    (re.compile(r"would like to|want to",             re.I), "aspiration"),
    (re.compile(r"when you\b|a time you\b|a time when",re.I), "past_experience"),
    (re.compile(r"\b(who|that)\s+\w+s\b",             re.I), "trait"),
    (re.compile(r"you admire|you look up to",          re.I), "admire"),
    (re.compile(r"\bwithout\b",                        re.I), "challenge"),
    (re.compile(r"for the first time|first time",      re.I), "first_time"),
    (re.compile(r"\bimportant\b|has been kept",        re.I), "valued"),
    (re.compile(r"\binteresting\b|\benjoy\b",          re.I), "enjoyment"),
    (re.compile(r"in a foreign country|in another country", re.I), "foreign"),
]

def assign_frame_key(prompt):
    p = prompt.lower()
    for pattern, tag in FRAME_KEY_RULES:
        if pattern.search(p):
            return tag
    return "null"

# ── LOAD ──────────────────────────────────────────────────────────────────────
print("Loading spaCy model...")
nlp = spacy.load("en_core_web_md")

with open(DATA, encoding="utf-8") as f:
    data = json.load(f)

prompts = [item["cue_card"]["prompt"] for item in data]
print(f"Loaded {len(prompts)} prompts.\n")

# ── SPLIT PROMPTS ─────────────────────────────────────────────────────────────
def extract_parts(prompt):
    """
    Strip 'Describe a/an/the' then use spaCy noun_chunks to split into:
      noun_phrase  – first noun chunk (article removed)
      qualifier    – everything after the first noun chunk
      head_lemma   – lemma of the chunk's root noun
    """
    text = re.sub(r"^Describe\s+(?:a|an|the)\s+", "", prompt, flags=re.I).strip()
    text = re.sub(r"^Describe\s+", "", text, flags=re.I).strip()

    doc    = nlp(text)
    chunks = list(doc.noun_chunks)

    if chunks:
        first       = chunks[0]
        noun_phrase = re.sub(r"^(?:a|an|the)\s+", "", first.text, flags=re.I).strip()
        qualifier   = text[first.end_char:].strip()
        head_lemma  = first.root.lemma_.lower()
    else:
        noun_phrase = text
        qualifier   = ""
        head_lemma  = doc[0].lemma_.lower() if doc else text.split()[0].lower()

    return noun_phrase, qualifier, head_lemma

# ── CATEGORY ──────────────────────────────────────────────────────────────────
def assign_category(head_lemma, noun_phrase, prompt):
    # Check prompt-level overrides first
    p_lower = prompt.lower()
    for trigger, cat in CATEGORY_OVERRIDES.items():
        if trigger in p_lower:
            return cat
    # Fall back to head-lemma / noun-phrase keyword rules
    np_lower = noun_phrase.lower()
    for cat, keywords in CATEGORY_RULES.items():
        if head_lemma in keywords or any(kw in np_lower for kw in keywords):
            return cat
    return "object"

# ── SUBSTANCE CLUSTERING (noun head lemmas, spaCy cosine) ─────────────────────
def cluster_by_similarity(phrases, threshold=0.75):
    docs     = [nlp(p) for p in phrases]
    assigned = [False] * len(phrases)
    clusters = []
    for i in range(len(phrases)):
        if assigned[i]:
            continue
        cluster = [i]
        assigned[i] = True
        for j in range(i + 1, len(phrases)):
            if not assigned[j] and docs[i].similarity(docs[j]) >= threshold:
                cluster.append(j)
                assigned[j] = True
        clusters.append(cluster)
    return clusters

def label_cluster(indices, phrases):
    counts     = Counter(phrases[i] for i in indices)
    max_count  = counts.most_common(1)[0][1]
    candidates = [p for p, c in counts.items() if c == max_count]
    return min(candidates, key=len)

# ── PROCESS ALL PROMPTS ───────────────────────────────────────────────────────
records = []
for prompt in prompts:
    np, qual, lemma = extract_parts(prompt)
    cat      = assign_category(lemma, np, prompt)
    frame    = assign_frame_key(prompt)
    records.append({
        "prompt":    prompt,
        "noun":      np,
        "qualifier": qual,
        "lemma":     lemma,
        "category":  cat,
        "frame_key": frame,
    })

# ── SUBSTANCE CLUSTERS ────────────────────────────────────────────────────────
print("Clustering noun lemmas (substance)...")
noun_lemmas      = [r["lemma"] for r in records]
noun_clusters    = cluster_by_similarity(noun_lemmas, threshold=0.75)
substance_labels = [label_cluster(c, noun_lemmas) for c in noun_clusters]

# Map each record index → its substance label
record_substance = {}
for label, cluster in zip(substance_labels, noun_clusters):
    for idx in cluster:
        record_substance[idx] = label

# ── COLLECT UNIQUE FRAME_KEY VALUES ──────────────────────────────────────────
frame_key_values = sorted(set(r["frame_key"] for r in records))

# ── SAVE content_tags.json ────────────────────────────────────────────────────
content_tags = {
    "category":  ["people", "place", "object", "experience"],
    "substance": sorted(set(substance_labels)),
    "frame_key": frame_key_values,
}

with open(TAGS_OUT, "w", encoding="utf-8") as f:
    json.dump(content_tags, f, ensure_ascii=False, indent=2)
print(f"Saved → {TAGS_OUT}")

# ── SAVE taxonomy_review.txt ──────────────────────────────────────────────────
SEP = "=" * 70

lines = [
    SEP,
    "TAXONOMY REVIEW — bootstrap_taxonomy.py",
    f"Topics: {len(records)}  |  Substance clusters: {len(noun_clusters)}  |  Frame_key values: {len(frame_key_values)}",
    SEP,
]

# Section 1: Category
lines += ["", SEP, "1. CATEGORY ASSIGNMENTS", SEP]
for cat in ["people", "place", "experience", "object"]:
    members = [r for r in records if r["category"] == cat]
    lines.append(f"\n[{cat.upper()}]  ({len(members)} topics)")
    for r in members:
        lines.append(f"  • {r['prompt']}")

# Section 2: Substance clusters
lines += ["", SEP, "2. SUBSTANCE CLUSTERS  (noun head lemmas)", SEP]
for i, cluster in enumerate(noun_clusters):
    label = substance_labels[i]
    lines.append(f"\n[{label}]  ({len(cluster)} members)")
    for idx in cluster:
        lines.append(f"  • {records[idx]['lemma']:18s} ← {records[idx]['prompt']}")

# Section 3: Frame_key assignments
lines += ["", SEP, "3. FRAME_KEY ASSIGNMENTS  (pattern rules)", SEP]
for fk in frame_key_values:
    members = [r for r in records if r["frame_key"] == fk]
    lines.append(f"\n[{fk}]  ({len(members)} topics)")
    for r in members:
        lines.append(f"  • {r['prompt']}")

with open(REVIEW_OUT, "w", encoding="utf-8") as f:
    f.write("\n".join(lines) + "\n")
print(f"Saved → {REVIEW_OUT}")

# ── CONSOLE SUMMARY ───────────────────────────────────────────────────────────
print(f"\n{'─'*50}")
print(f"Categories : {content_tags['category']}")
print(f"Substance  : {len(content_tags['substance'])} labels → {content_tags['substance']}")
print(f"Frame_key  : {content_tags['frame_key']}")
