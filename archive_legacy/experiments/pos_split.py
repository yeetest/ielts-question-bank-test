"""
pos_split.py
Splits keywords_filtered.txt into two files by POS category:
  - keywords_nouns_verbs.txt  (NOUN, PROPN, VERB)
  - keywords_adjs.txt         (ADJ)

Same format as input: question line + → token(POS,score) line.
Questions with no tokens after split are still included (empty → line).

To run:
    python3 pos_split.py

Input/output filenames set below.
"""

import re

# --- Config ---
INPUT_FILE = "keywords_filtered.txt"
OUTPUT_NV = "keywords_nouns_verbs.txt"
OUTPUT_ADJ = "keywords_adjs.txt"

NOUN_VERB_POS = {"NOUN", "PROPN", "VERB"}
ADJ_POS = {"ADJ"}


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


# --- Split by POS ---
def split_by_pos(keyword_line, pos_set):
    if not keyword_line:
        return ""
    content = keyword_line.lstrip("→ ").strip()
    tokens = re.findall(r"\w+\([^)]+\)", content)

    kept = []
    for token in tokens:
        # Extract POS from token like "routine(NOUN,0.621)"
        match = re.match(r"^(\w+)\((\w+),", token)
        if match:
            pos = match.group(2)
            if pos in pos_set:
                kept.append(token)

    return "→ " + ", ".join(kept) if kept else ""


# --- Write ---
def write_output(blocks, output_file):
    with open(output_file, "w", encoding="utf-8") as f:
        for question, keyword_line in blocks:
            f.write(question + "\n")
            if keyword_line:
                f.write("  " + keyword_line + "\n")
            f.write("\n")


# --- Main ---
with open(INPUT_FILE, "r", encoding="utf-8") as f:
    raw = f.read()

blocks = parse_blocks(raw)

nv_blocks = [(q, split_by_pos(kw, NOUN_VERB_POS)) for q, kw in blocks]
adj_blocks = [(q, split_by_pos(kw, ADJ_POS)) for q, kw in blocks]

write_output(nv_blocks, OUTPUT_NV)
write_output(adj_blocks, OUTPUT_ADJ)

# Report
nv_count = sum(len(re.findall(r"\w+\(", kw)) for _, kw in nv_blocks)
adj_count = sum(len(re.findall(r"\w+\(", kw)) for _, kw in adj_blocks)
total = sum(len(re.findall(r"\w+\(", kw)) for _, kw in blocks)

print(f"Input: {total} tokens from {len(blocks)} questions")
print(f"  → {OUTPUT_NV}: {nv_count} tokens (NOUN/PROPN/VERB)")
print(f"  → {OUTPUT_ADJ}: {adj_count} tokens (ADJ)")
