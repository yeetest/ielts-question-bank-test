"""
filter_adjs.py
Filters keywords_adjs.txt to keep only evaluative + emotional adjectives.
Outputs keywords_adjs_filtered.txt in identical format.

To run:
    python3 filter_adjs.py
"""

import re

# --- Config ---
INPUT_FILE = "keywords_adjs.txt"
OUTPUT_FILE = "keywords_adjs_filtered.txt"

# Evaluative + emotional adjectives to keep
KEEP_ADJS = {
    # emotional / sentiment
    "happy", "proud", "comfortable", "pleasant", "nice", "sorry",
    "unforgettable", "meaningful", "interested", "keen", "favourite",
    "favorite", "quiet", "beautiful", "special", "noisy",
    "friendly", "fashionable",
    # evaluative
    "easy", "difficult", "necessary", "essential", "helpful",
    "effective", "reasonable", "worth", "successful", "smart",
    "creative", "valuable", "dangerous", "ideal", "right", "wrong",
    "positive", "negative", "popular", "famous", "interesting",
    "bad", "great", "suitable", "unwilling", "willing", "reluctant",
    "patient", "dedicated",
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


# --- Filter ---
def filter_keywords(keyword_line):
    if not keyword_line:
        return ""
    content = keyword_line.lstrip("→ ").strip()
    tokens = re.findall(r"\w+\([^)]+\)", content)

    kept = []
    for token in tokens:
        match = re.match(r"^(\w+)\(", token)
        if match:
            word = match.group(1).lower()
            if word in KEEP_ADJS:
                kept.append(token)

    return "→ " + ", ".join(kept) if kept else ""


# --- Write ---
def write_output(blocks, output_file):
    """Write deduplicated keywords-only (no question lines).
    Each unique adjective appears once, with its highest TF-IDF score."""
    from collections import OrderedDict
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
                if word not in best or score > best[word][1]:
                    best[word] = (pos, score)

    with open(output_file, "w", encoding="utf-8") as f:
        for word, (pos, score) in sorted(best.items()):
            f.write(f"{word}({pos},{score})\n")

    return len(best)


# --- Main ---
with open(INPUT_FILE, "r", encoding="utf-8") as f:
    raw = f.read()

blocks = parse_blocks(raw)
filtered_blocks = [(q, filter_keywords(kw)) for q, kw in blocks]
token_count = sum(len(re.findall(r"\w+\(", kw)) for _, kw in filtered_blocks)
unique_count = write_output(filtered_blocks, OUTPUT_FILE)

original_count = sum(len(re.findall(r"\w+\(", kw)) for _, kw in blocks)
print(f"Done. {original_count} total → {token_count} evaluative → {unique_count} unique (deduplicated).")
print(f"Output: {OUTPUT_FILE}")
