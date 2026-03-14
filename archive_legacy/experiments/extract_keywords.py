"""
extract_keywords.py
Extracts important words from IELTS questions using spaCy + TF-IDF.

Two methods combined:
  1. spaCy (en_core_web_sm) — keeps nouns, verbs, adjectives; drops stop words & punctuation
  2. TF-IDF (sklearn) — scores words across the full corpus, returns top N per question

Output: dict where key = original question, value = ranked list of (word, score) tuples.

Usage:
    python3 pipeline/extract_keywords.py                     # all questions, top 5
    python3 pipeline/extract_keywords.py --top 8             # top 8 words
    python3 pipeline/extract_keywords.py --part 1            # Part 1 only
    python3 pipeline/extract_keywords.py --part 2            # Part 3 only
    python3 pipeline/extract_keywords.py --output keywords.json  # save to file

Requires: pip3 install spacy scikit-learn && python3 -m spacy download en_core_web_sm
"""

import json
import re
import sys
from pathlib import Path

import spacy
from sklearn.feature_extraction.text import TfidfVectorizer


# ---------------------------------------------------------------------------
# spaCy filtering
# ---------------------------------------------------------------------------

nlp = spacy.load("en_core_web_sm")

# POS tags to keep: nouns, verbs, adjectives
KEEP_POS = {"NOUN", "VERB", "ADJ", "PROPN"}

# Extra stop words specific to IELTS questions (not content-bearing)
# Keep light — only remove the most generic question-framing words
IELTS_STOP = {
    "think", "person", "thing", "way",
    "like", "know", "say", "tell", "let",
    "come", "go", "get", "give", "take",
    "do", "have", "be",
    "many", "much", "lot",
}


def spacy_filter(text):
    """Return list of (lemma, pos) tuples from a question."""
    doc = nlp(text.lower())
    words = []
    for token in doc:
        if token.is_stop or token.is_punct or token.is_space:
            continue
        if token.pos_ not in KEEP_POS:
            continue
        lemma = token.lemma_
        if lemma in IELTS_STOP or len(lemma) < 3:
            continue
        words.append((lemma, token.pos_))
    return words


# ---------------------------------------------------------------------------
# TF-IDF scoring
# ---------------------------------------------------------------------------

def build_tfidf(questions, top_n=5):
    """
    Build TF-IDF matrix over spaCy-filtered questions.
    Returns dict: original question → [(word, pos, score), ...] ranked by weight.
    """
    # Pre-filter each question with spaCy, keep POS mapping
    filtered_docs = []
    pos_maps = []  # per-question: {lemma: pos}
    for q in questions:
        pairs = spacy_filter(clean_question(q))
        pos_map = {lemma: pos for lemma, pos in pairs}
        filtered_docs.append(" ".join(lemma for lemma, _ in pairs))
        pos_maps.append(pos_map)

    # Fit TF-IDF on the filtered corpus
    vectorizer = TfidfVectorizer(
        token_pattern=r"(?u)\b\w+\b",
        max_df=0.85,   # ignore words in >85% of docs (too common)
        min_df=1,       # keep rare words (small corpus)
    )
    tfidf_matrix = vectorizer.fit_transform(filtered_docs)
    feature_names = vectorizer.get_feature_names_out()

    results = {}
    for i, q in enumerate(questions):
        row = tfidf_matrix[i].toarray().flatten()
        top_indices = row.argsort()[::-1][:top_n]
        keywords = []
        for idx in top_indices:
            score = row[idx]
            if score > 0:
                word = feature_names[idx]
                pos = pos_maps[i].get(word, "?")
                keywords.append((word, pos, round(float(score), 3)))
        results[q] = keywords

    return results


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def clean_question(text):
    """Strip leading number and normalise."""
    return re.sub(r'^\d+[\.\)]\s*', '', text.strip())


def load_questions(part=None):
    """Load questions from JSON files. Returns list of (question_text, source_info)."""
    base = Path(__file__).parent.parent
    questions = []

    if part is None or part == 1:
        p1 = json.loads((base / "merged_part1.json").read_text(encoding="utf-8"))
        for topic in p1:
            for q in topic.get("questions", []):
                questions.append(q["text"])

    if part is None or part == 2:
        p2 = json.loads((base / "merged_part2.json").read_text(encoding="utf-8"))
        for topic in p2:
            for q in topic.get("part3", []):
                questions.append(q["text"])

    return questions


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    part = None
    top_n = 5
    output_path = None

    args = sys.argv[1:]
    i = 0
    while i < len(args):
        if args[i] == "--part" and i + 1 < len(args):
            part = int(args[i + 1])
            i += 2
        elif args[i] == "--top" and i + 1 < len(args):
            top_n = int(args[i + 1])
            i += 2
        elif args[i] == "--output" and i + 1 < len(args):
            output_path = args[i + 1]
            i += 2
        else:
            i += 1

    questions = load_questions(part)
    print(f"Loaded {len(questions)} questions (part={part or 'all'})")

    results = build_tfidf(questions, top_n=top_n)

    # Print sample
    sample = list(results.items())[:15]
    for q, kws in sample:
        kw_str = ", ".join(f"{w}({pos},{s})" for w, pos, s in kws)
        print(f"  {q}")
        print(f"    → {kw_str}")
        print()

    if len(results) > 15:
        print(f"  ... ({len(results) - 15} more questions)")

    # Save to file if requested
    if output_path:
        with open(output_path, "w", encoding="utf-8") as f:
            for q, kws in results.items():
                kw_str = ", ".join(f"{w}({pos},{s})" for w, pos, s in kws)
                f.write(f"{q}\n")
                f.write(f"  → {kw_str}\n\n")
        print(f"\nSaved to {output_path}")


if __name__ == "__main__":
    main()
