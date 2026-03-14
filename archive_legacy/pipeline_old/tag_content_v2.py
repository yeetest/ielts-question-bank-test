"""
tag_content_v2.py
Auto-tags topics with content_tags using the v2 3-layer taxonomy.
Keyword matching against topic name (primary) + question texts (secondary).

V2 taxonomy: 5 L1 → 15 L2 → 30 L3
(from human-in-the-loop/content_tags_v2_draft.md)

Usage:
    python3 pipeline/tag_content_v2.py merged_part1.json --part 1
    python3 pipeline/tag_content_v2.py merged_part2.json
    python3 pipeline/tag_content_v2.py merged_part1.json --part 1 --dry-run
    python3 pipeline/tag_content_v2.py merged_part1.json --part 1 --overwrite
"""

import json
import re
import sys
import subprocess
from pathlib import Path
from collections import defaultdict


# ===========================================================================
# V2 TAXONOMY — keyword → tag mapping
# ===========================================================================
# Each entry: { "l1": ..., "l2": ..., "l3": ... (optional), "keywords": [...],
#               "topic_keywords": [...] (optional, matched only against topic name) }
# Keywords are matched case-insensitively.
# "topic_keywords" get 5x weight (matched against topic name only).
# "keywords" get 1x weight from topic name, 0.3x weight from question text.

TAG_RULES = [
    # ── L1: people ──────────────────────────────────────────────────────

    # L2: professions
    {"l1": "people", "l2": "professions",
     "topic_keywords": [
         "person who", "someone who", "sportsperson", "celebrity",
         "famous person", "well-known", "artist", "musician",
     ],
     "keywords": [
         "doctor", "actor", "actress", "athlete", "director",
         "leader", "official", "politician", "scientist",
         "teacher", "professor", "coach", "engineer",
         "nurse", "police", "officer",
         "businessman", "businesswoman", "singer",
         "writer", "author", "chef", "architect",
     ]},

    # L2: close_bonds
    {"l1": "people", "l2": "close_bonds",
     "topic_keywords": [
         "friend", "family member", "family", "neighbour", "neighbor",
         "colleague",
     ],
     "keywords": [
         "parent", "mother", "father", "sister", "brother",
         "grandparent", "grandmother", "grandfather",
         "uncle", "aunt", "cousin", "relative",
         "partner", "spouse", "wife", "husband",
         "best friend", "close friend", "classmate",
     ]},

    # L2: general (people at large)
    {"l1": "people", "l2": "general",
     "topic_keywords": [
         "children", "child", "old people", "elderly", "young people",
     ],
     "keywords": [
         "society", "citizens", "crowd", "generation", "strangers",
         "community", "population", "teenagers",
     ]},

    # ── L1: place ───────────────────────────────────────────────────────

    # L2: outdoor
    {"l1": "place", "l2": "outdoor",
     "topic_keywords": [
         "city", "town", "village", "country", "place", "park",
         "mountain", "beach", "garden", "area", "scenery", "view",
         "nature", "natural place", "countryside", "island",
         "hometown", "landscape",
     ],
     "keywords": [
         "sea", "ocean", "river", "lake", "forest", "field",
         "landmark", "outdoor", "street", "bridge",
         "waterfall", "desert", "valley", "hill",
         "crowded place",
     ]},

    # L2: indoor
    {"l1": "place", "l2": "indoor",
     "topic_keywords": [
         "building", "house", "home", "room", "museum", "library",
         "shop", "store", "mall", "accommodation", "apartment",
     ],
     "keywords": [
         "gallery", "cinema", "theatre", "theater", "factory",
         "hospital", "restaurant", "cafe", "office", "hotel",
         "indoor", "facility", "gym", "stadium",
     ]},

    # ── L1: object ──────────────────────────────────────────────────────

    # L2: tangible
    {"l1": "object", "l2": "tangible",
     "topic_keywords": [
         "food", "fruit", "vegetable", "clothes", "shoes", "gift",
         "toy", "key", "camera", "bicycle", "bike", "car",
         "plant", "item", "thing you bought", "something you bought",
         "photo", "photograph", "painting", "map", "letter",
         "instrument", "headphone",
     ],
     "keywords": [
         "bag", "watch", "clock", "pen", "pencil", "chair",
         "table", "furniture", "jewellery", "jewelry", "hat",
         "coat", "dress", "shirt", "ticket", "statue",
     ]},

    # L2: intangible → L3: artwork
    {"l1": "object", "l2": "intangible", "l3": "artwork",
     "topic_keywords": [
         "book", "novel", "story", "poem", "song", "music",
         "movie", "film", "painting", "artwork",
     ],
     "keywords": [
         "sculpture", "album",
     ]},

    # L2: intangible → L3: technology
    {"l1": "object", "l2": "intangible", "l3": "technology",
     "topic_keywords": [
         "technology", "app", "computer", "phone", "program",
         "software", "device", "gadget", "robot",
         "electricity", "power cut",
     ],
     "keywords": [
         "internet", "laptop", "desktop", "screen", "keyboard",
         "social media", "platform", "website", "digital",
         "smartphone", "mobile phone",
     ]},

    # L2: intangible → L3: money
    {"l1": "object", "l2": "intangible", "l3": "money",
     "topic_keywords": [
         "money", "spent more than", "expensive", "cost",
     ],
     "keywords": [
         "cash", "fee", "salary", "price", "investment",
         "spending", "afford", "budget", "income", "wage",
         "financial", "save money",
     ]},

    # L2: intangible → L3: media
    {"l1": "object", "l2": "intangible", "l3": "media",
     "topic_keywords": [
         "advertisement", "tv program", "online program",
         "tv.*program", "online.*program", "news",
     ],
     "keywords": [
         "television", "broadcast", "newspaper",
         "magazine", "radio", "podcast", "documentary",
     ]},

    # ── L1: experience/activity ─────────────────────────────────────────

    # L2: work
    {"l1": "experience/activity", "l2": "work",
     "topic_keywords": [
         "job", "work", "career", "business", "company",
     ],
     "keywords": [
         "employment", "profession", "occupation", "employer",
         "employee", "workplace", "office work", "part-time",
         "full-time", "interview", "hire", "promotion",
         "retired", "retirement",
     ]},

    # L2: study
    {"l1": "experience/activity", "l2": "study",
     "topic_keywords": [
         "study", "studies", "education", "science", "subject",
         "course", "typing", "handwriting",
     ],
     "keywords": [
         "language learning", "grade", "graduation",
         "university", "college", "student",
         "exam", "test", "homework", "lecture", "lesson",
         "major", "degree", "scholarship",
     ]},

    # L2: leisure → L3: exercise
    {"l1": "experience/activity", "l2": "leisure", "l3": "exercise",
     "topic_keywords": [
         "sport", "sports team", "walking", "cycling", "exercise",
         "swimming", "hiking",
     ],
     "keywords": [
         "running", "football", "basketball", "tennis", "badminton",
         "yoga", "climbing", "jogging", "gym",
         "physical activity", "team sport",
     ]},

    # L2: leisure → L3: shopping
    {"l1": "experience/activity", "l2": "leisure", "l3": "shopping",
     "topic_keywords": [
         "shopping", "shop", "store",
     ],
     "keywords": [
         "buying", "mall", "market", "online shopping", "purchase",
     ]},

    # L2: leisure → L3: cooking
    {"l1": "experience/activity", "l2": "leisure", "l3": "cooking",
     "topic_keywords": [
         "cook", "cooking", "meal", "dinner", "food",
     ],
     "keywords": [
         "recipe", "bake", "baking", "kitchen", "eating out",
         "restaurant", "lunch", "breakfast", "cuisine",
     ]},

    # L2: leisure → L3: traveling
    {"l1": "experience/activity", "l2": "leisure", "l3": "traveling",
     "topic_keywords": [
         "travel", "journey", "trip", "visit", "tourism",
         "vacation", "holiday", "foreign country",
         "lost your way", "lost.*way",
     ],
     "keywords": [
         "plane", "train", "transport", "flight", "abroad",
         "sightseeing", "destination",
     ]},

    # L2: leisure → L3: creative
    {"l1": "experience/activity", "l2": "leisure", "l3": "creative",
     "topic_keywords": [
         "drawing", "painting", "photography", "crafting",
         "creative", "craft",
     ],
     "keywords": [
         "making things", "handmade", "diy", "design",
         "knitting", "sewing", "sculpting",
     ]},

    # L2: leisure → L3: reading
    {"l1": "experience/activity", "l2": "leisure", "l3": "reading",
     "topic_keywords": [
         "reading", "book you read",
     ],
     "keywords": [
         "article", "e-book", "ebook", "bookstore",
     ]},

    # L2: leisure → L3: entertainment
    {"l1": "experience/activity", "l2": "leisure", "l3": "entertainment",
     "topic_keywords": [
         "movie", "film", "concert", "show", "music",
         "game", "video game",
     ],
     "keywords": [
         "cinema", "performance", "singing", "dancing",
     ]},

    # L2: routines
    {"l1": "experience/activity", "l2": "routines",
     "topic_keywords": [
         "daily", "routine", "habit", "morning", "day off",
         "spare time", "having a break", "hobby", "memory",
         "going out",
     ],
     "keywords": [
         "chore", "bedtime", "commute", "everyday",
         "schedule", "timetable", "regular", "free time",
     ]},

    # ── L1: abstract_concepts ───────────────────────────────────────────

    # L2: communication
    {"l1": "abstract_concepts", "l2": "communication",
     "topic_keywords": [
         "advice", "chatting", "conversation", "apologize",
         "apologized", "apologised", "encouraged", "talking",
     ],
     "keywords": [
         "argue", "arguing", "speak", "speaking",
         "discuss", "discussion", "debate", "persuade",
         "complain", "complaint", "disagree",
         "communicate", "communication",
         "borrow", "lend", "lending", "borrowing", "sharing",
     ]},

    # L2: emotion → L3: pride
    {"l1": "abstract_concepts", "l2": "emotion", "l3": "pride",
     "topic_keywords": [
         "proud", "pride", "felt proud",
     ],
     "keywords": [
         "accomplishment", "achievement", "success", "milestone",
     ]},

    # L2: emotion → L3: happiness
    {"l1": "abstract_concepts", "l2": "emotion", "l3": "happiness",
     "topic_keywords": [
         "happy", "smiling", "enjoyed", "happy things",
     ],
     "keywords": [
         "happiness", "joy", "joyful", "smile",
         "enjoyment", "fun", "cheerful", "laugh",
         "excited", "excitement",
     ]},

    # L2: emotion → L3: fear
    {"l1": "abstract_concepts", "l2": "emotion", "l3": "fear",
     "topic_keywords": [
         "exciting", "nervous", "scared",
     ],
     "keywords": [
         "worry", "worried", "anxiety", "anxious", "danger",
         "fear", "afraid", "stress", "panic",
     ]},

    # L2: emotion → L3: anger
    {"l1": "abstract_concepts", "l2": "emotion", "l3": "anger",
     "topic_keywords": [
         "angry", "didn't enjoy",
     ],
     "keywords": [
         "frustrat", "conflict", "annoyed", "annoying",
         "upset", "furious",
     ]},

    # L2: emotion → L3: attachment
    {"l1": "abstract_concepts", "l2": "emotion", "l3": "attachment",
     "topic_keywords": [
         "can't live without", "kept in your family",
         "kept for a long time", "old thing", "heirloom",
     ],
     "keywords": [
         "miss", "nostalgia", "nostalgic", "sentimental",
         "treasure", "cherish", "keepsake",
     ]},

    # L2: emotion → L3: regret
    {"l1": "abstract_concepts", "l2": "emotion", "l3": "regret",
     "topic_keywords": [
         "apologized", "apologised", "broke something",
     ],
     "keywords": [
         "sorry", "apologize", "apologise", "mistake", "regret",
     ]},

    # L2: emotion → L3: patience
    {"l1": "abstract_concepts", "l2": "emotion", "l3": "patience",
     "topic_keywords": [
         "waited", "waiting",
     ],
     "keywords": [
         "patience", "patient", "tolerance", "queue",
     ]},

    # L2: personal_traits → L3: creativity
    {"l1": "abstract_concepts", "l2": "personal_traits", "l3": "creativity",
     "topic_keywords": [
         "creative person", "imagination", "creative",
     ],
     "keywords": [
         "creativity", "artistic", "innovation", "innovative",
         "imaginative", "inventive", "original",
     ]},

    # L2: personal_traits → L3: problem-solving
    {"l1": "abstract_concepts", "l2": "personal_traits", "l3": "problem-solving",
     "topic_keywords": [
         "solved a problem", "smart way",
     ],
     "keywords": [
         "solution", "solve", "solving", "fix", "fixing",
         "figure out", "figured out",
     ]},

    # L2: personal_traits → L3: craftsmanship
    {"l1": "abstract_concepts", "l2": "personal_traits", "l3": "craftsmanship",
     "topic_keywords": [
         "handmade", "by hand",
     ],
     "keywords": [
         "craftsmanship", "artisan", "craftsman", "woodwork", "pottery",
     ]},

    # L2: personal_traits → L3: responsibility
    {"l1": "abstract_concepts", "l2": "personal_traits", "l3": "responsibility",
     "topic_keywords": [],
     "keywords": [
         "responsibility", "responsible", "duty", "accountability",
     ]},

    # L2: personal_traits → L3: honesty
    {"l1": "abstract_concepts", "l2": "personal_traits", "l3": "honesty",
     "topic_keywords": [],
     "keywords": [
         "honest", "honesty", "truthful", "sincere",
         "trustworthy",
     ]},

    # L2: values → L3: policy
    {"l1": "abstract_concepts", "l2": "values", "l3": "policy",
     "topic_keywords": [
         "not allowed", "rules",
     ],
     "keywords": [
         "law", "government", "regulation", "ban",
         "legal", "illegal", "policy",
         "prohibit", "forbidden",
     ]},

    # L2: values → L3: environment
    {"l1": "abstract_concepts", "l2": "values", "l3": "environment",
     "topic_keywords": [
         "natural world", "environment", "wildlife",
         "wild animal", "pets", "animal",
     ],
     "keywords": [
         "environmental", "conservation", "pollution",
         "green", "protect.*nature", "eco",
         "climate", "recycle", "sustainable",
     ]},

    # L2: values → L3: economics
    {"l1": "abstract_concepts", "l2": "values", "l3": "economics",
     "topic_keywords": [],
     "keywords": [
         "economy", "economic", "market forces",
         "economic growth", "industry", "trade",
         "globalization",
     ]},

    # L2: values → L3: fairness
    {"l1": "abstract_concepts", "l2": "values", "l3": "fairness",
     "topic_keywords": [],
     "keywords": [
         "equality", "equal", "justice", "fair", "fairness",
         "equity", "discrimination", "rights", "inequality",
     ]},

    # L2: personal_growth → L3: learning
    {"l1": "abstract_concepts", "l2": "personal_growth", "l3": "learning",
     "topic_keywords": [
         "learned", "learning", "without.*teacher",
         "self-taught",
     ],
     "keywords": [
         "education", "knowledge", "studying", "taught", "teaching",
     ]},

    # L2: personal_growth → L3: self-improvement
    {"l1": "abstract_concepts", "l2": "personal_growth", "l3": "self-improvement",
     "topic_keywords": [
         "develop", "want to develop", "doing.*well",
     ],
     "keywords": [
         "improve", "improvement", "practice", "practise",
         "skill", "better at", "get better",
     ]},

    # L2: personal_growth → L3: adaptation
    {"l1": "abstract_concepts", "l2": "personal_growth", "l3": "adaptation",
     "topic_keywords": [],
     "keywords": [
         "adapt", "adjust", "cope", "new situation", "move to",
     ]},

    # L2: personal_growth → L3: goal-setting
    {"l1": "abstract_concepts", "l2": "personal_growth", "l3": "goal-setting",
     "topic_keywords": [
         "plans", "dream",
     ],
     "keywords": [
         "goal", "ambition", "ambitious", "aspiration",
         "future plan", "career plan",
     ]},

    # L2: personal_growth → L3: decision
    {"l1": "abstract_concepts", "l2": "personal_growth", "l3": "decision",
     "topic_keywords": [
         "decision", "important decision",
     ],
     "keywords": [
         "decide", "choice", "choose", "choosing",
     ]},

    # L2: influence
    {"l1": "abstract_concepts", "l2": "influence",
     "topic_keywords": [
         "admire", "encouraged", "influence",
     ],
     "keywords": [
         "influential", "inspire", "inspiration",
         "motivate", "motivation", "impact",
         "role model", "look up to", "idol",
     ]},

    # L2: time
    {"l1": "abstract_concepts", "l2": "time",
     "topic_keywords": [
         "childhood", "life stages", "first time",
         "in your childhood",
     ],
     "keywords": [
         "generation", "old days", "when you were young",
         "growing up", "era", "tradition", "traditional",
         "ancient", "modern",
     ]},
]


# L1 priority for tie-breaking (lower index = higher priority)
L1_PRIORITY = ["people", "place", "object", "experience/activity", "abstract_concepts"]

# Maximum tags to output
MAX_L2 = 3
MAX_L3 = 2


# ===========================================================================
# Matching engine
# ===========================================================================

def get_topic_name(topic, part):
    """Get the topic name string."""
    if part == 1:
        return topic.get("topic_en", "")
    else:
        return topic.get("topic", "")


def get_topic_text(topic, part):
    """Get the topic name + cue card text (high weight)."""
    texts = [get_topic_name(topic, part).lower()]
    if part == 2:
        cue = topic.get("cue_card", {})
        if cue.get("prompt"):
            texts.append(cue["prompt"].lower())
    return " ".join(texts)


def get_question_text(topic, part):
    """Get all question text (low weight)."""
    q_key = "questions" if part == 1 else "part3"
    texts = []
    for q in topic.get(q_key, []):
        texts.append(q.get("text", "").lower())
    return " ".join(texts)


def match_keywords(text, keywords):
    """Count how many keywords match in the text."""
    count = 0
    for kw in keywords:
        if ".*" in kw:
            pattern = kw
        else:
            # Word boundary match, allow trailing s
            pattern = r"\b" + re.escape(kw).replace(r"\ ", r"\s+") + r"s?\b"
        if re.search(pattern, text, re.IGNORECASE):
            count += 1
    return count


def classify_topic(topic, part):
    """
    Returns content_tags dict: {"l1": str, "l2": [...], "l3": [...]}
    """
    topic_text = get_topic_text(topic, part)
    question_text = get_question_text(topic, part)

    # Score each rule with weighted matching
    # topic_keywords matched against topic_text: weight 5
    # keywords matched against topic_text: weight 2
    # keywords matched against question_text: weight 0.3
    rule_scores = []
    for rule in TAG_RULES:
        score = 0.0

        # topic_keywords (only matched against topic name/cue card)
        tk = rule.get("topic_keywords", [])
        if tk:
            score += match_keywords(topic_text, tk) * 5.0

        # general keywords against topic text
        kw = rule.get("keywords", [])
        if kw:
            score += match_keywords(topic_text, kw) * 2.0

        # general keywords against question text (low weight)
        if kw:
            score += match_keywords(question_text, kw) * 0.3

        if score > 0:
            rule_scores.append((score, rule))

    if not rule_scores:
        return None, {}

    # Sort by score descending
    rule_scores.sort(key=lambda x: -x[0])

    # Determine L1: sum scores per L1
    l1_totals = defaultdict(float)
    for score, rule in rule_scores:
        l1_totals[rule["l1"]] += score

    # Pick L1 with highest total; tie-break by priority
    primary_l1 = max(
        l1_totals,
        key=lambda l1: (l1_totals[l1], -L1_PRIORITY.index(l1))
    )

    # Collect L2 candidates — only from rules matching the primary L1
    l2_scores = defaultdict(float)
    l3_from_l2 = defaultdict(list)  # l2 → [(score, l3)]
    for score, rule in rule_scores:
        if rule["l1"] != primary_l1:
            continue
        l2 = rule["l2"]
        l2_scores[l2] += score
        if "l3" in rule and score > 0:
            l3_from_l2[l2].append((score, rule["l3"]))

    # Pick top L2s (up to MAX_L2)
    sorted_l2 = sorted(l2_scores.items(), key=lambda x: -x[1])
    top_l2 = [l2 for l2, _ in sorted_l2[:MAX_L2]]

    # Pick top L3s from the selected L2s (up to MAX_L3)
    l3_candidates = []
    for l2 in top_l2:
        for score, l3 in l3_from_l2.get(l2, []):
            l3_candidates.append((score, l3))

    l3_candidates.sort(key=lambda x: -x[0])
    seen_l3 = set()
    top_l3 = []
    for _, l3 in l3_candidates:
        if l3 not in seen_l3:
            seen_l3.add(l3)
            top_l3.append(l3)
            if len(top_l3) >= MAX_L3:
                break

    result = {
        "l1": primary_l1,
        "l2": sorted(top_l2),
        "l3": sorted(top_l3),
    }

    return result, dict(l1_totals)


# ===========================================================================
# Main processing
# ===========================================================================

def process_file(filepath, part, dry_run=False, overwrite=False):
    with open(filepath, encoding="utf-8") as f:
        data = json.load(f)

    tagged = 0
    skipped = 0
    failed = 0
    results = []

    for topic in data:
        name = get_topic_name(topic, part)

        # Skip already-tagged unless overwrite
        existing = topic.get("content_tags")
        if existing and not overwrite:
            if isinstance(existing, dict) and existing.get("l1"):
                skipped += 1
                continue

        tags, l1_scores = classify_topic(topic, part)

        if tags is None:
            failed += 1
            results.append(f"  [NO MATCH] {name}")
            continue

        topic["content_tags"] = tags
        tagged += 1

        score_str = ", ".join(
            f"{k}={v:.1f}" for k, v in sorted(l1_scores.items(), key=lambda x: -x[1])
        )
        results.append(
            f"  [TAGGED] {name[:50]:50s} → l1={tags['l1']}, l2={tags['l2']}, l3={tags['l3']}  ({score_str})"
        )

    # Print summary
    prefix = "[DRY RUN] " if dry_run else ""
    print(f"\n{prefix}Content tagging v2 — Part {part}")
    print(f"  Total: {len(data)}  |  Tagged: {tagged}  |  Skipped: {skipped}  |  No match: {failed}")
    print()
    for r in results:
        print(r)

    if not dry_run and tagged > 0:
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"\nWrote {filepath}")

        # Auto-regenerate .txt mirror
        txt_script = Path(__file__).parent.parent / "human-in-the-loop" / "json_to_txt.py"
        if txt_script.exists():
            print("Regenerating .txt mirror...")
            subprocess.run([sys.executable, str(txt_script), str(filepath)], check=True)
    elif dry_run:
        print("\nNo changes written (dry run).")
    else:
        print("\nNothing to tag.")


def main():
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python3 pipeline/tag_content_v2.py merged_part1.json --part 1")
        print("  python3 pipeline/tag_content_v2.py merged_part2.json")
        print("  Add --dry-run to preview without writing")
        print("  Add --overwrite to re-tag already tagged topics")
        sys.exit(1)

    filepath = sys.argv[1]
    part = 2
    if "--part" in sys.argv:
        idx = sys.argv.index("--part")
        if idx + 1 < len(sys.argv):
            part = int(sys.argv[idx + 1])

    dry_run = "--dry-run" in sys.argv
    overwrite = "--overwrite" in sys.argv

    process_file(filepath, part, dry_run=dry_run, overwrite=overwrite)


if __name__ == "__main__":
    main()
