import json
import os
import spacy

# ── CONFIG ────────────────────────────────────────────────────────────────────
BASE        = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_PATH   = os.path.join(BASE, "merged_part2.json")
TAGS_PATH   = os.path.join(BASE, "tags", "question_type_tags.json")

TAGS_ORDER = ["describe", "analyze", "evaluate", "predict"]

TAG_DESCRIPTIONS = {
    "describe": "stating current facts, what exists now, what people do, listing things",
    "analyze":  "explaining why something happens, how something works, cause and effect, meaning",
    "evaluate": "forming judgments, pros and cons, better or worse, right or wrong, should or shouldn't, agreeing or disagreeing",
    "predict":  "future state, what will happen, how things will change, hypothetical outcomes",
}

KEYWORD_BOOSTS = {
    "describe": [
        "what kind of", "what kind", "what are the types", "what types",
        "what examples", "what are some", "what do people",
        "in your country", "what is popular", "on what occasion",
    ],
    "analyze": [
        "why do", "why are", "why is", "how do", "how does",
        "what influences", "what impact", "what effect",
        "what causes", "how can", "how did", "how has", "manage to",
        "what are the problems", "what problems",
    ],
    "evaluate": [
        "do you think", "what do you think", "do you agree",
        "is it good", "is it important", "is it better", "is it worth",
        "should", "advantages and disadvantages", "which is better",
        "which", "is it easy", "is it necessary", "most important", "right age",
        "necessary",
    ],
    "predict": [
        "will replace", "will change", "will people", "in the future",
        "will",
    ],
}

BOOST = 0.2       # keyword boost weight
MARGIN = 0.02     # include second tag if within this margin of the top

# ── LOAD MODEL ────────────────────────────────────────────────────────────────
print("Loading spaCy model...")
nlp = spacy.load("en_core_web_md")

# Pre-encode tag description vectors
tag_docs = {tag: nlp(desc) for tag, desc in TAG_DESCRIPTIONS.items()}

# ── TAGGER ────────────────────────────────────────────────────────────────────
def tag_question(text: str) -> list[str]:
    lower = text.lower()
    q_doc = nlp(lower)

    scores = {}
    for tag in TAGS_ORDER:
        # Step 1: semantic similarity
        score = q_doc.similarity(tag_docs[tag])
        # Step 2: keyword boost
        for phrase in KEYWORD_BOOSTS[tag]:
            if phrase in lower:
                score += BOOST
                break  # one boost per tag max
        scores[tag] = round(score, 4)

    # Step 3: relative scoring — top tag wins; include second if within MARGIN
    best = max(scores.values())
    assigned = [tag for tag in TAGS_ORDER if scores[tag] >= best - MARGIN]
    if not assigned:
        assigned = ["unclear"]

    return assigned, scores

# ── MAIN ──────────────────────────────────────────────────────────────────────
with open(DATA_PATH, encoding="utf-8") as f:
    data = json.load(f)

total = 0
for item in data:
    for q in item.get("part3", []):
        text = q.get("text", "")
        tags, scores = tag_question(text)
        q["type_tags"] = tags

        # Progress log
        preview = text[:50].ljust(50)
        score_str = "  ".join(f"{t}={scores[t]:.3f}" for t in TAGS_ORDER)
        print(f"{preview} → {tags}  ({score_str})")
        total += 1

with open(DATA_PATH, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print(f"\nDone. Tagged {total} questions → {DATA_PATH}")
