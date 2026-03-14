"""
filter_nouns_verbs.py
Filters keywords_nouns_verbs.txt to remove question-framing stopwords,
deduplicates (keeping highest TF-IDF score per word), outputs sorted list.

To run:
    python3 filter_nouns_verbs.py
"""

import re
from collections import OrderedDict

# --- Config ---
INPUT_FILE = "keywords_nouns_verbs.txt"
OUTPUT_FILE = "keywords_nouns_verbs_filtered.txt"

# Question-framing words — not topically meaningful
STOP_NOUNS_VERBS = {
    # generic question words / framing
    "people", "person", "child", "children", "kid", "adult", "student",
    "parent", "teacher", "man", "woman", "boy", "girl", "teenager",
    "kind", "type", "example", "difference", "time", "thing",
    "way", "reason", "factor", "benefit", "advantage", "disadvantage",
    "change", "choice", "decision", "influence", "effect", "impact",
    "use", "role", "form", "process", "quality", "importance",
    "today", "past", "future", "year", "day", "week", "morning",
    "afternoon", "age", "stage", "moment", "decade", "tomorrow",
    # generic nouns — not topically meaningful
    "activity", "area", "group", "member", "class", "term",
    "requirement", "meaning", "development", "growth",
    "preparation", "difficulty", "background", "charge",
    "entry", "fee", "key", "spot", "site", "chance", "occasion",
    "manner", "hassle", "ending", "preference", "impression",
    "system", "medium", "report", "idea", "problem", "challenge",
    "public", "society", "population", "generation", "citizen",
    "intervention", "punishment", "responsibility", "law",
    "government", "enterprise", "appearance", "emotion", "fear",
    "noise", "sound", "hand", "air", "spring", "autumn",
    "major", "grade", "course", "subject", "market", "street",
    "price", "salary", "cash", "inside", "outside",
    # generic verbs
    "live", "learn", "prefer", "spend", "feel", "make", "find",
    "ask", "choose", "describe", "look", "continue", "start",
    "try", "see", "consider", "keep", "focus", "provide",
    "lead", "compare", "agree", "show", "call", "stop",
    "explain", "manage", "close", "break", "bear", "face",
    "meet", "leave", "pay", "save", "send", "aim",
    "acquire", "adapt", "affect", "argue", "attach", "attract",
    "ban", "behave", "bring", "buy", "crowd", "develop",
    "disappear", "dislike", "enjoy", "enhance", "expect",
    "finish", "fix", "forget", "gain", "grow", "hate", "help",
    "identify", "improve", "inspire", "limit", "lock", "lose",
    "mind", "miss", "plan", "prepare", "pretend", "prevent",
    "produce", "prohibit", "protect", "pursue", "react",
    "receive", "recognize", "recommend", "refuse", "regret",
    "rely", "remember", "replace", "require", "return",
    "reward", "rid", "stay", "succeed", "throw", "value", "wait",
}


# Merge variant forms → canonical lemma (keeps highest score)
LEMMA_MERGE = {
    "advertising": "advertisement",
    "communication": "communicate",
    "creativity": "create",
    "education": "educate",
    "electronic": "electricity",
    "encouragement": "encourage",
    "friendship": "friend",
    "grown": "grow",
    "household": "house",
    "housing": "house",
    "inspiration": "inspire",
    "musician": "music",
    "neighborhood": "neighbor",
    "neighbour": "neighbor",
    "photograph": "photo",
    "photography": "photo",
    "protection": "protect",
    "reading": "read",
    "scientist": "science",
    "shopping": "shop",
    "training": "train",
    "transportation": "transport",
    "waiting": "wait",
    "workplace": "work",
}


# --- Parse ---
def parse_blocks(text):
    blocks = []
    lines = text.strip().split("\n")
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if line and re.match(r"^\d+\.", line):
            question = line
            keyword_line = ""
            if i + 1 < len(lines) and lines[i + 1].strip().startswith("→"):
                keyword_line = lines[i + 1].strip()
                i += 2
            else:
                i += 1
            blocks.append((question, keyword_line))
        else:
            i += 1
    return blocks


# --- Filter + Dedup ---
def build_deduped(blocks):
    """Return {word: (pos, score)} keeping highest score per word."""
    best = OrderedDict()
    for _, keyword_line in blocks:
        if not keyword_line:
            continue
        content = keyword_line.lstrip("→ ").strip()
        tokens = re.findall(r"\w+\([^)]+\)", content)
        for token in tokens:
            match = re.match(r"^(\w+)\((\w+),([\d.]+)\)", token)
            if match:
                word, pos, score = match.group(1), match.group(2), float(match.group(3))
                if word.lower() in STOP_NOUNS_VERBS:
                    continue
                # Merge variant forms
                word = LEMMA_MERGE.get(word, word)
                if word not in best or score > best[word][1]:
                    best[word] = (pos, score)
    return best


# --- Main ---
with open(INPUT_FILE, "r", encoding="utf-8") as f:
    raw = f.read()

blocks = parse_blocks(raw)
total_tokens = sum(len(re.findall(r"\w+\(", kw)) for _, kw in blocks)

deduped = build_deduped(blocks)

with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    for word, (pos, score) in sorted(deduped.items()):
        f.write(f"{word}({pos},{score})\n")

print(f"Done. {total_tokens} tokens → {len(deduped)} unique (filtered + deduplicated).")
print(f"Output: {OUTPUT_FILE}")
