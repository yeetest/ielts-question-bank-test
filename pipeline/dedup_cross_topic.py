"""
dedup_cross_topic.py
──────────────────────────────────────────────────────────────────────
Finds semantically duplicate questions ACROSS all topics and parts
(Part 1 questions + Part 2 Part 3 questions).

Uses TF-IDF + cosine similarity to detect questions that ask the same
thing with different phrasing.

Output: human-in-the-loop/duplicates.txt
  — Groups of duplicates, one group per block.
  — Each line shows: [KEEP/REMOVE] Part X | Topic | Question text
  — Human reviews and edits KEEP/REMOVE markers before running
    apply_dedup.py to commit the changes to JSON.

Usage:
    python3 pipeline/dedup_cross_topic.py [--threshold 0.82]
"""

import json, os, re, sys
from collections import defaultdict

try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
except ImportError:
    sys.exit("ERROR: scikit-learn required. Install with: pip3 install scikit-learn")

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(SCRIPT_DIR)
OUTPUT_DIR = os.path.join(REPO_ROOT, "human-in-the-loop")

P1_FILE = os.path.join(REPO_ROOT, "merged_part1.json")
P2_FILE = os.path.join(REPO_ROOT, "merged_part2.json")
OUTPUT = os.path.join(OUTPUT_DIR, "duplicates.txt")

DEFAULT_THRESHOLD = 0.82


def clean_text(text):
    """Strip leading number, punctuation, lowercase, normalise whitespace."""
    t = re.sub(r"^\d+[\.\)]\s*", "", text.strip())
    t = t.lower().strip()
    t = re.sub(r"\s+", " ", t)
    return t


def load_all_questions():
    """Load all questions from both parts into a flat list with metadata."""
    questions = []

    p1_data = json.load(open(P1_FILE, encoding="utf-8"))
    for topic_idx, topic in enumerate(p1_data):
        for q_idx, q in enumerate(topic.get("questions", [])):
            questions.append({
                "part": 1,
                "topic": topic.get("topic_en", ""),
                "topic_idx": topic_idx,
                "q_idx": q_idx,
                "text": q["text"],
                "clean": clean_text(q["text"]),
                "source": q.get("source", ""),
                "type_tags": q.get("type_tags", []),
            })

    p2_data = json.load(open(P2_FILE, encoding="utf-8"))
    for topic_idx, topic in enumerate(p2_data):
        for q_idx, q in enumerate(topic.get("part3", [])):
            questions.append({
                "part": 2,
                "topic": topic.get("topic", topic.get("topic_en", "")),
                "topic_idx": topic_idx,
                "q_idx": q_idx,
                "text": q["text"],
                "clean": clean_text(q["text"]),
                "source": q.get("source", ""),
                "type_tags": q.get("type_tags", []),
            })

    return questions


def find_duplicates(questions, threshold):
    """Find groups of semantically similar questions using TF-IDF cosine."""
    clean_texts = [q["clean"] for q in questions]

    vectorizer = TfidfVectorizer(
        ngram_range=(1, 2),
        min_df=1,
        stop_words="english",
    )
    tfidf = vectorizer.fit_transform(clean_texts)
    sim_matrix = cosine_similarity(tfidf)

    n = len(questions)
    visited = [False] * n
    groups = []

    for i in range(n):
        if visited[i]:
            continue
        cluster = [i]
        visited[i] = True
        for j in range(i + 1, n):
            if visited[j]:
                continue
            if sim_matrix[i, j] >= threshold:
                cluster.append(j)
                visited[j] = True
        if len(cluster) > 1:
            groups.append(cluster)

    return groups


def score_question(q):
    """Score to pick which duplicate to keep (higher = better)."""
    s = len(q["text"])
    if q["text"].strip().endswith("?"):
        s += 20
    if q["type_tags"]:
        s += 10
    return s


def write_output(groups, questions, output_path):
    """Write duplicate groups to txt for human review."""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    # Count cross-topic vs within-topic groups
    cross_topic = 0
    within_topic = 0
    for g in groups:
        topics = set((questions[i]["part"], questions[i]["topic"]) for i in g)
        if len(topics) > 1:
            cross_topic += 1
        else:
            within_topic += 1

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("DUPLICATE QUESTIONS — Review & Edit\n")
        f.write("=" * 60 + "\n")
        f.write(f"Total groups: {len(groups)} ({cross_topic} cross-topic, {within_topic} within-topic)\n")
        f.write(f"Total duplicate questions: {sum(len(g) for g in groups)}\n\n")
        f.write("Instructions:\n")
        f.write("  - Each group shows questions that are semantically similar.\n")
        f.write("  - Lines marked [KEEP] will be kept; lines marked [REMOVE] will be deleted.\n")
        f.write("  - The script auto-suggests KEEP for the best version, REMOVE for the rest.\n")
        f.write("  - Review and change [KEEP]/[REMOVE] as needed.\n")
        f.write("  - After editing, run: python3 pipeline/apply_dedup.py\n")
        f.write("=" * 60 + "\n\n")

        for group_idx, group in enumerate(groups, 1):
            # Sort by score, highest first
            scored = sorted(group, key=lambda i: score_question(questions[i]), reverse=True)
            best = scored[0]

            topics = set((questions[i]["part"], questions[i]["topic"]) for i in group)
            group_type = "CROSS-TOPIC" if len(topics) > 1 else "WITHIN-TOPIC"

            f.write(f"── Group {group_idx} ({group_type}) ──\n")
            for idx in scored:
                q = questions[idx]
                marker = "KEEP" if idx == best else "REMOVE"
                tags = ", ".join(q["type_tags"]) if q["type_tags"] else ""
                f.write(f"[{marker}] Part {q['part']} | {q['topic']} | {q['text']}")
                if tags:
                    f.write(f" [{tags}]")
                f.write(f" (source: {q['source']})\n")
            f.write("\n")

    return len(groups)


def main():
    threshold = DEFAULT_THRESHOLD
    if "--threshold" in sys.argv:
        idx = sys.argv.index("--threshold")
        if idx + 1 < len(sys.argv):
            threshold = float(sys.argv[idx + 1])

    print(f"Loading questions from both parts...")
    questions = load_all_questions()
    print(f"Loaded {len(questions)} questions total")

    print(f"Finding duplicates (threshold={threshold})...")
    groups = find_duplicates(questions, threshold)

    if not groups:
        print("No duplicates found!")
        return

    count = write_output(groups, questions, OUTPUT)
    print(f"\nFound {count} duplicate groups")
    print(f"Written to: {OUTPUT}")
    print(f"\nNext steps:")
    print(f"  1. Review {OUTPUT} and edit [KEEP]/[REMOVE] markers")
    print(f"  2. Run: python3 pipeline/apply_dedup.py")


if __name__ == "__main__":
    main()
