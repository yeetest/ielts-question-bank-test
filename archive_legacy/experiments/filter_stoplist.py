import re

# --- Config ---
INPUT_FILE = "keywords.txt"
OUTPUT_FILE = "keywords_filtered.txt"

# Words that are never topically meaningful in IELTS questions
STOPLIST = {
    "think", "want", "need", "way", "good", "able", "possible", "important",
    "s", "what", "well", "bit", "few", "mid"
}

# --- Parse ---
# Reads the file and groups each question + its keyword line as one block
def parse_blocks(text):
    blocks = []
    lines = text.strip().split("\n")
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if line and re.match(r"^\d+\.", line):          # line starts with "1." "2." etc → it's a question
            question = line
            keyword_line = ""
            if i + 1 < len(lines) and lines[i + 1].strip().startswith("→"):
                keyword_line = lines[i + 1].strip()    # next line is the keyword line
                i += 2
            else:
                i += 1
            blocks.append((question, keyword_line))
        else:
            i += 1
    return blocks

# --- Filter ---
# Removes any keyword token whose word is in the stoplist
def filter_keywords(keyword_line, stoplist):
    if not keyword_line:
        return ""
    prefix = "→ "
    content = keyword_line.lstrip("→ ").strip()        # strip the arrow prefix
    tokens = re.findall(r"\w+\([^)]+\)", content)      # extract full tokens like "routine(NOUN,0.621)" using regex

    kept = []
    for token in tokens:
        match = re.match(r"^(\w+)\(", token)           # extract just the word before the "("
        if match:
            word = match.group(1).lower()
            if word not in stoplist:                   # keep token only if word not in stoplist
                kept.append(token)

    return prefix + ", ".join(kept) if kept else ""

# --- Write ---
# Outputs filtered blocks in the same format as input
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
filtered_blocks = [(q, filter_keywords(kw, STOPLIST)) for q, kw in blocks]
write_output(filtered_blocks, OUTPUT_FILE)

# Report how many tokens were removed
original_count = sum(len(re.findall(r"\w+\(", kw)) for _, kw in blocks)
filtered_count = sum(len(re.findall(r"\w+\(", kw)) for _, kw in filtered_blocks)
print(f"Done. {original_count} tokens → {filtered_count} kept ({original_count - filtered_count} removed).")
print(f"Output: {OUTPUT_FILE}")
