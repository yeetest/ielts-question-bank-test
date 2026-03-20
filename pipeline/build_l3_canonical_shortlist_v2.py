#!/usr/bin/env python3
"""
build_l3_canonical_shortlist_v2.py

Condense noisy L3 candidate proposals into a human-reviewable canonical shortlist
per `l1 > l2` bucket. Deterministic rules only (no LLM dependency).

Inputs:
- human-in-the-loop/l3_candidate_bank_v2.json
- human-in-the-loop/topic_taxonomy_view_v2_part1.json
- human-in-the-loop/topic_taxonomy_view_v2_part2.json

Outputs:
- human-in-the-loop/l3_canonical_shortlist_v2.json
- human-in-the-loop/l3_canonical_shortlist_review_v2.md
"""

from __future__ import annotations

import json
import re
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent

IN_CANDIDATE_BANK = ROOT / "human-in-the-loop" / "l3_candidate_bank_v2.json"
IN_VIEW_P1 = ROOT / "human-in-the-loop" / "topic_taxonomy_view_v2_part1.json"
IN_VIEW_P2 = ROOT / "human-in-the-loop" / "topic_taxonomy_view_v2_part2.json"

OUT_JSON = ROOT / "human-in-the-loop" / "l3_canonical_shortlist_v2.json"
OUT_MD = ROOT / "human-in-the-loop" / "l3_canonical_shortlist_review_v2.md"


STOP_LABELS = {
    "other",
    "any",
    "thing",
    "stuff",
    "someone",
    "people",
    "often",
    "always",
    "usually",
    "many",
    "much",
    "more",
    "less",
    "difference",
    "both",
    "another",
    "etc",
    "there",
    "here",
    "live",
    "living",
    "think",
    "alway",
    "always",
    "usual",
    "usually",
    "again",
    "first",
    "second",
    "third",
    "book",
    "friend",
    "family_member",
    "visit",
    "during",
    "since",
    "changed",
    "send",
    "chinese",
}

FUNCTION_WORDS = {
    "a",
    "an",
    "the",
    "and",
    "or",
    "to",
    "of",
    "for",
    "in",
    "on",
    "with",
    "without",
    "from",
    "by",
    "as",
    "at",
    "about",
    "into",
    "over",
    "under",
    "than",
    "then",
    "that",
    "this",
    "these",
    "those",
    "when",
    "where",
    "why",
    "what",
    "which",
    "who",
    "whom",
    "whose",
    "how",
    "is",
    "are",
    "was",
    "were",
    "be",
    "been",
    "being",
    "have",
    "has",
    "had",
    "do",
    "does",
    "did",
    "would",
    "could",
    "should",
    "can",
    "cant",
    "cannot",
    "not",
    "you",
    "your",
    "yours",
    "he",
    "she",
    "they",
    "them",
    "their",
    "it",
    "its",
}

QUESTION_ARTIFACT_WORDS = {
    "question",
    "questions",
    "prompt",
    "part",
    "topic",
    "something",
    "someone",
    "anything",
    "anyone",
    "time",
    "times",
    "person",
    "people",
    "place",
    "places",
    "item",
    "occasion",
    "way",
    "ways",
    "between",
    "about",
    "ask",
    "asking",
    "tell",
    "saying",
    "said",
}

VERBISH_WORDS = {
    "ask",
    "asking",
    "talk",
    "talking",
    "speak",
    "speaking",
    "chat",
    "chatting",
    "walk",
    "walking",
    "shop",
    "shopping",
    "study",
    "studying",
    "travel",
    "traveling",
    "play",
    "playing",
}

# Cross-bucket and bucket-aware alias merge rules.
GLOBAL_ALIAS = {
    "chat": "conversation",
    "chatting": "conversation",
    "conversation": "conversation",
    "talk": "conversation",
    "talking": "conversation",
    "communication_skill": "conversation",
    "child": "childhood",
    "kid": "childhood",
    "children": "childhood",
    "childhood_activity": "childhood",
    "childhood_memory": "childhood",
    "shop": "shopping",
    "store": "shopping",
    "store_visit": "shopping",
    "shop_visit": "shopping",
    "shopping": "shopping",
    "sport": "exercise",
    "sports": "exercise",
    "walking": "exercise",
    "walk": "exercise",
    "physical_activity": "exercise",
    "workout": "exercise",
    "exercise": "exercise",
    "trip": "travel",
    "journey": "travel",
    "traveling": "travel",
    "travel": "travel",
    "city_trip": "travel",
    "hobby_activity": "hobby",
    "spare_time": "leisure_time",
    "free_time": "leisure_time",
    "daily_routine": "morning_routine",
    "morning_time": "morning_routine",
    "daily": "daily_life_pattern",
    "routine": "daily_life_pattern",
    "family_member": "family_bond",
    "become_friend": "friendship",
    "advice_other": "advice_support",
    "advice_friend": "advice_support",
    "city_live": "city_space",
    "living_there": "city_space",
    "near_live": "neighborhood_area",
    "alway_take": "rest_break",
    "area": "neighborhood_area",
    "country": "travel_destination",
    "bicycle": "transport_item",
    "bicycle_motorcycle": "transport_item",
    "bought_shoe": "personal_item",
    "borrow_money": "resource_exchange",
    "better_children": "childhood",
    "boss_employee": "professional_relationship",
    "bring_key": "personal_item",
    "buying_shoe": "personal_item",
    "car": "transport_item",
    "borrowed": "resource_exchange",
    "children_help": "supportive_relationship",
    "dinner": "family_activity",
    "car_trip": "transport_item",
    "changed_since": "daily_life_pattern",
    "chinese_send": "resource_exchange",
    "borrowing_lending": "resource_exchange",
    "choosing": "gift_item",
    "choosing_gift": "gift_item",
    "comfortable_shoe": "personal_item",
    "chat_group": "conversation",
}

BUCKET_ALIAS = {
    ("place", "outdoor"): {
        "city": "city_space",
        "hometown": "city_space",
        "park": "nature_place",
        "mountain": "nature_place",
        "view": "scenery",
        "scenic_view": "scenery",
        "public_space": "public_place",
    },
    ("experience_activity", "routines"): {
        "habit": "habit",
        "hobby": "hobby",
        "break": "rest_break",
        "rest": "rest_break",
        "daily_life": "daily_life_pattern",
        "routine": "daily_life_pattern",
        "memory": "memory_reflection",
    },
    ("object", "tangible"): {
        "gift": "gift_item",
        "toy": "toy_game_item",
        "photo": "photography_item",
        "plant": "plant_item",
        "vegetable": "food_gardening_item",
        "fruit": "food_gardening_item",
        "shoe": "personal_item",
        "key": "personal_item",
        "food": "food_item",
    },
    ("abstract_concepts", "communication"): {
        "advice": "advice_support",
        "encouragement": "encouragement",
        "sharing": "sharing",
        "borrowing": "resource_exchange",
        "lending": "resource_exchange",
        "apology": "apology_repair",
        "foreign_language": "foreign_language_communication",
    },
    ("people", "close_bonds"): {
        "friend": "friendship",
        "family": "family_bond",
        "parent": "family_bond",
        "relative": "family_bond",
        "helpful_person": "supportive_relationship",
        "proud_moment": "family_pride_moment",
    },
}

LONG_LABEL_ALLOWLIST = {
    "foreign_language_communication",
    "daily_life_pattern",
    "food_gardening_item",
}

REBUCKET_HINTS = {
    "technology",
    "media",
    "money",
    "policy",
    "environment",
    "professional_relationship",
}

APPROVED_VERBISH_LABELS = {
    "shopping",
    "exercise",
    "travel",
    "study_subject",
    "conversation",
}

BUCKET_ALLOWED_CANONICAL = {
    ("place", "outdoor"): {
        "city_space",
        "scenery",
        "neighborhood_area",
        "public_place",
        "nature_place",
        "quiet_outdoor_space",
        "travel_destination",
    },
    ("experience_activity", "routines"): {
        "daily_life_pattern",
        "morning_routine",
        "hobby",
        "rest_break",
        "leisure_time",
        "memory_reflection",
    },
    ("object", "tangible"): {
        "gift_item",
        "food_gardening_item",
        "personal_item",
        "photography_item",
        "toy_game_item",
        "transport_item",
    },
    ("abstract_concepts", "communication"): {
        "conversation",
        "sharing",
        "resource_exchange",
        "advice_support",
        "encouragement",
        "apology_repair",
        "foreign_language_communication",
    },
    ("people", "close_bonds"): {
        "family_bond",
        "friendship",
        "supportive_relationship",
        "childhood",
        "family_pride_moment",
        "family_activity",
    },
}


def load_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        f.write(content)


def normalize_label(label: str) -> str:
    label = label.strip().lower().replace("-", "_")
    label = re.sub(r"[^a-z0-9_]+", "_", label)
    label = re.sub(r"_+", "_", label).strip("_")
    return label


def token_count(label: str) -> int:
    return len([t for t in label.split("_") if t])


def normalize_token(token: str) -> str:
    if token.endswith("ies") and len(token) > 4:
        return token[:-3] + "y"
    if token.endswith("s") and len(token) > 3 and not token.endswith(("ss", "us", "is")):
        return token[:-1]
    return token


def canonicalize_tokens(label: str) -> str:
    tokens = [normalize_token(t) for t in label.split("_") if t]
    return "_".join(tokens)


def is_question_artifact(label: str) -> bool:
    tokens = [t for t in label.split("_") if t]
    if not tokens:
        return True
    if all(t in FUNCTION_WORDS for t in tokens):
        return True
    if any(t in QUESTION_ARTIFACT_WORDS for t in tokens) and len(tokens) <= 2:
        return True
    if any(re.fullmatch(r"\d+", t) for t in tokens):
        return True
    if any(re.search(r"\d", t) for t in tokens):
        return True
    return False


def reject_reason(label: str, support_count: int) -> str | None:
    if not label:
        return "empty_label"
    if label in STOP_LABELS:
        return "stop_like_label"
    tokens = [t for t in label.split("_") if t]
    if not tokens:
        return "no_tokens"
    if len(tokens) > 3 and label not in LONG_LABEL_ALLOWLIST:
        return "too_long"
    if any(t in FUNCTION_WORDS for t in tokens) and len(tokens) == 1:
        return "function_word"
    if any(t in STOP_LABELS for t in tokens):
        return "stop_token"
    if is_question_artifact(label):
        return "question_artifact"
    if all(t in VERBISH_WORDS for t in tokens) and label not in APPROVED_VERBISH_LABELS:
        return "verb_fragment"
    if support_count <= 1 and len(tokens) >= 3 and label not in LONG_LABEL_ALLOWLIST:
        return "over_specific_low_support"
    return None


def apply_alias(label: str, l1: str, l2: str) -> str:
    if label in GLOBAL_ALIAS:
        label = GLOBAL_ALIAS[label]
    bucket_alias = BUCKET_ALIAS.get((l1, l2), {})
    if label in bucket_alias:
        label = bucket_alias[label]

    # Bucket-sensitive verb-fragment preference.
    if (l1, l2) == ("abstract_concepts", "communication"):
        if label in {"talk", "talking", "chat", "chatting"}:
            label = "conversation"
    if (l1, l2) == ("experience_activity", "routines"):
        if label in {"routine", "daily_routine"}:
            label = "daily_life_pattern"
    if (l1, l2) == ("object", "tangible"):
        if label in {"walk", "walking"}:
            label = "exercise"  # explicitly deterministic merge rule requested by user
    return label


def confidence_for_label(support_count: int, merged_count: int) -> str:
    if support_count >= 5 or (support_count >= 4 and merged_count >= 2):
        return "high"
    if support_count >= 2:
        return "medium"
    return "low"


def rationale_for_label(label: str) -> str:
    if label.endswith("_routine") or "routine" in label:
        return "stable daily-life behavior concept across prompts"
    if label in {"conversation", "shopping", "exercise", "travel", "childhood", "hobby"}:
        return "highly reusable cross-topic semantic concept"
    if label.endswith("_item") or label.endswith("_place") or label.endswith("_bond"):
        return "object/place/relationship noun concept reusable for retrieval"
    if "communication" in label or "relationship" in label:
        return "stable interaction concept rather than prompt wording"
    return "portable noun-like semantic concept with repeat evidence"


def title_to_bucket_labels(l1: str, l2: str, titles: list[str]) -> dict[str, set[str]]:
    out: dict[str, set[str]] = defaultdict(set)
    for t in titles:
        text = t.lower()
        if (l1, l2) == ("place", "outdoor"):
            if any(k in text for k in ["city", "hometown", "area"]):
                out["city_space"].add(t)
            if any(k in text for k in ["view", "scenery"]):
                out["scenery"].add(t)
            if any(k in text for k in ["natural", "park", "mountain"]):
                out["nature_place"].add(t)
            if any(k in text for k in ["public", "crowded"]):
                out["public_place"].add(t)
            if "quiet" in text:
                out["quiet_outdoor_space"].add(t)

        if (l1, l2) == ("experience_activity", "routines"):
            if any(k in text for k in ["daily", "routine"]):
                out["daily_life_pattern"].add(t)
            if "morning" in text:
                out["morning_routine"].add(t)
            if "hobby" in text:
                out["hobby"].add(t)
            if any(k in text for k in ["break", "day off"]):
                out["rest_break"].add(t)
            if any(k in text for k in ["spare time", "going out"]):
                out["leisure_time"].add(t)
            if "memory" in text:
                out["memory_reflection"].add(t)

        if (l1, l2) == ("object", "tangible"):
            if any(k in text for k in ["gift"]):
                out["gift_item"].add(t)
            if any(k in text for k in ["food", "fruit", "vegetable", "plants"]):
                out["food_gardening_item"].add(t)
            if any(k in text for k in ["shoe", "key"]):
                out["personal_item"].add(t)
            if any(k in text for k in ["photo", "camera"]):
                out["photography_item"].add(t)
            if any(k in text for k in ["toy"]):
                out["toy_game_item"].add(t)
            if any(k in text for k in ["bicycle", "motorcycle", "car trip"]):
                out["transport_item"].add(t)

        if (l1, l2) == ("abstract_concepts", "communication"):
            if any(k in text for k in ["chat", "conversation"]):
                out["conversation"].add(t)
            if "sharing" in text:
                out["sharing"].add(t)
            if any(k in text for k in ["borrowing", "lending"]):
                out["resource_exchange"].add(t)
            if "advice" in text:
                out["advice_support"].add(t)
            if "encouraged" in text:
                out["encouragement"].add(t)
            if "apologized" in text:
                out["apology_repair"].add(t)

        if (l1, l2) == ("people", "close_bonds"):
            if "friend" in text:
                out["friendship"].add(t)
            if any(k in text for k in ["family", "family member"]):
                out["family_bond"].add(t)
            if "child" in text:
                out["childhood"].add(t)
            if any(k in text for k in ["helps others", "help"]):
                out["supportive_relationship"].add(t)
            if "proud" in text:
                out["family_pride_moment"].add(t)
    return out


def compute_missing_counts(views: list[dict[str, Any]]) -> dict[tuple[str, str], int]:
    out: dict[tuple[str, str], int] = defaultdict(int)
    for row in views:
        tx = row.get("taxonomy_v2", {}) or {}
        p = tx.get("primary", {}) or {}
        l1 = p.get("l1")
        l2 = p.get("l2")
        if not l1 or not l2:
            continue
        if p.get("l3") is None:
            out[(str(l1), str(l2))] += 1
    return dict(out)


def decision_for_bucket(
    *,
    raw_count: int,
    proposed_count: int,
    low_count: int,
    rejected_count: int,
    has_rebucket_hints: bool,
) -> str:
    if has_rebucket_hints:
        return "NEEDS MANUAL REBUCKET"
    if raw_count > 0 and rejected_count / raw_count >= 0.55:
        return "NEEDS MANUAL SPLIT"
    if proposed_count == 0:
        return "NEEDS MANUAL SPLIT"
    if 5 <= proposed_count <= 15 and low_count <= max(2, proposed_count // 4):
        return "APPROVE"
    if proposed_count > 15 or low_count > max(3, proposed_count // 3):
        return "APPROVE WITH TRIM"
    return "APPROVE WITH TRIM"


def main() -> None:
    candidate_bank = load_json(IN_CANDIDATE_BANK)
    view_p1 = load_json(IN_VIEW_P1)
    view_p2 = load_json(IN_VIEW_P2)

    missing_counts = compute_missing_counts(view_p1 + view_p2)
    bucket_titles: dict[tuple[str, str], list[str]] = defaultdict(list)
    for row in view_p1 + view_p2:
        tx = row.get("taxonomy_v2", {}) or {}
        p = tx.get("primary", {}) or {}
        l1 = p.get("l1")
        l2 = p.get("l2")
        topic = str(row.get("topic", "")).strip()
        if l1 and l2 and topic:
            bucket_titles[(str(l1), str(l2))].append(topic)
    by_l1_in = candidate_bank.get("by_l1", {}) or {}

    out_by_l1: dict[str, Any] = {}
    total_l2_buckets_processed = 0
    total_raw_candidate_labels = 0
    total_proposed_canonical_labels = 0

    review_lines: list[str] = []
    review_lines.append("# L3 Canonical Shortlist Review v2")
    review_lines.append("")
    review_lines.append("Deterministic canonicalization only. No taxonomy config overwrite and no topic reassignment.")
    review_lines.append("")

    for l1 in sorted(by_l1_in.keys()):
        l1_node = by_l1_in[l1] or {}
        by_l2_in = l1_node.get("by_l2", {}) or {}
        out_l2_map: dict[str, Any] = {}

        review_lines.append(f"## {l1}")
        review_lines.append("")

        for l2 in sorted(by_l2_in.keys()):
            total_l2_buckets_processed += 1
            raw_entries = (by_l2_in[l2] or {}).get("candidate_l3", []) or []
            raw_count = len(raw_entries)
            total_raw_candidate_labels += raw_count

            merged: dict[str, dict[str, Any]] = {}
            rejected: list[dict[str, str]] = []

            for raw in raw_entries:
                raw_label = str(raw.get("label", "")).strip()
                norm = normalize_label(raw_label)
                norm = canonicalize_tokens(norm)
                support = int(raw.get("support_topic_count", 0) or 0)

                reason = reject_reason(norm, support)
                if reason:
                    rejected.append({"label": norm or raw_label, "reason": reason})
                    continue

                canonical = apply_alias(norm, l1, l2)
                canonical = normalize_label(canonicalize_tokens(canonical))
                reason = reject_reason(canonical, support)
                if reason:
                    rejected.append({"label": canonical or norm, "reason": f"post_alias_{reason}"})
                    continue

                if canonical not in merged:
                    merged[canonical] = {
                        "label": canonical,
                        "support_count": 0,
                        "merged_from_raw_labels": set(),
                        "representative_topics": [],
                        "representative_question_snippets": [],
                    }

                m = merged[canonical]
                m["support_count"] += support
                m["merged_from_raw_labels"].add(raw_label)

                for topic in raw.get("example_topics", []) or []:
                    if len(m["representative_topics"]) >= 8:
                        break
                    if topic not in m["representative_topics"]:
                        m["representative_topics"].append(topic)

                for snip in raw.get("example_question_snippets", []) or []:
                    if len(m["representative_question_snippets"]) >= 5:
                        break
                    if snip not in m["representative_question_snippets"]:
                        m["representative_question_snippets"].append(snip)

            proposed: list[dict[str, Any]] = []
            for label, item in merged.items():
                merged_from = sorted(item["merged_from_raw_labels"])
                conf = confidence_for_label(item["support_count"], len(merged_from))
                proposed.append(
                    {
                        "label": label,
                        "support_count": item["support_count"],
                        "confidence": conf,
                        "merged_from_raw_labels": merged_from,
                        "representative_topics": item["representative_topics"][:8],
                        "representative_question_snippets": item["representative_question_snippets"][:5],
                        "_rationale": rationale_for_label(label),
                    }
                )

            # Deterministic bucket-level reinforcement from topic titles (no LLM).
            supplements = title_to_bucket_labels(l1, l2, bucket_titles.get((l1, l2), []))
            for sup_label, topics in supplements.items():
                existing = next((x for x in proposed if x["label"] == sup_label), None)
                support = len(topics)
                if existing is not None:
                    existing["support_count"] += support
                    merged_labels = set(existing["merged_from_raw_labels"])
                    merged_labels.add("title_keyword_supplement")
                    existing["merged_from_raw_labels"] = sorted(merged_labels)
                    for tp in sorted(topics):
                        if tp not in existing["representative_topics"] and len(existing["representative_topics"]) < 8:
                            existing["representative_topics"].append(tp)
                    existing["confidence"] = confidence_for_label(
                        existing["support_count"], len(existing["merged_from_raw_labels"])
                    )
                else:
                    proposed.append(
                        {
                            "label": sup_label,
                            "support_count": support,
                            "confidence": confidence_for_label(support, 1),
                            "merged_from_raw_labels": ["title_keyword_supplement"],
                            "representative_topics": sorted(topics)[:8],
                            "representative_question_snippets": [],
                            "_rationale": rationale_for_label(sup_label),
                        }
                    )

            proposed.sort(
                key=lambda x: (
                    {"high": 0, "medium": 1, "low": 2}.get(x["confidence"], 3),
                    -x["support_count"],
                    x["label"],
                )
            )

            allowed = BUCKET_ALLOWED_CANONICAL.get((l1, l2))
            if allowed is not None:
                proposed = [p for p in proposed if p["label"] in allowed]

            # Shortlist sizing policy: usually 5-15, but can be smaller for narrow buckets.
            if raw_count <= 6:
                target_max = min(6, max(3, raw_count))
            elif raw_count <= 15:
                target_max = 10
            else:
                target_max = 15
            proposed = proposed[:target_max]

            # If still too noisy, trim lowest-confidence tail.
            while len(proposed) > 5 and proposed and proposed[-1]["confidence"] == "low":
                proposed.pop()

            proposed_count = len(proposed)
            total_proposed_canonical_labels += proposed_count

            low_count = sum(1 for p in proposed if p["confidence"] == "low")
            has_rebucket_hints = any(p["label"] in REBUCKET_HINTS for p in proposed)
            decision = decision_for_bucket(
                raw_count=raw_count,
                proposed_count=proposed_count,
                low_count=low_count,
                rejected_count=len(rejected),
                has_rebucket_hints=has_rebucket_hints,
            )

            out_l2_map[l2] = {
                "current_missing_primary_l3_count": missing_counts.get((l1, l2), 0),
                "raw_candidate_count": raw_count,
                "proposed_canonical_l3_count": proposed_count,
                "proposed_canonical_l3": [
                    {
                        "label": p["label"],
                        "support_count": p["support_count"],
                        "confidence": p["confidence"],
                        "merged_from_raw_labels": p["merged_from_raw_labels"],
                        "representative_topics": p["representative_topics"],
                        "representative_question_snippets": p["representative_question_snippets"],
                    }
                    for p in proposed
                ],
                "review_decision": decision,
                "labels_rejected_as_noise": rejected[:20],
            }

            # Review markdown block.
            review_lines.append(f"### {l1} > {l2}")
            review_lines.append(f"- current missing primary.l3 count: {missing_counts.get((l1, l2), 0)}")
            review_lines.append(f"- raw candidate count: {raw_count}")
            review_lines.append(f"- proposed canonical shortlist count: {proposed_count}")
            review_lines.append("")
            review_lines.append("Final recommended canonical labels:")
            for p in proposed:
                review_lines.append(
                    f"- `{p['label']}` (support={p['support_count']}, confidence={p['confidence']}) - {p['_rationale']}"
                )
            review_lines.append("")
            review_lines.append("Labels rejected as noise (examples):")
            if rejected:
                for r in rejected[:10]:
                    review_lines.append(f"- `{r['label']}` - {r['reason']}")
            else:
                review_lines.append("- none")
            review_lines.append("")
            review_lines.append("Recommended immediate human decision:")
            review_lines.append(f"- {decision}")
            review_lines.append("")

        out_by_l1[l1] = out_l2_map

    avg_per_bucket = (
        round(total_proposed_canonical_labels / total_l2_buckets_processed, 2)
        if total_l2_buckets_processed
        else 0.0
    )

    payload = {
        "metadata": {
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "script": "pipeline/build_l3_canonical_shortlist_v2.py",
            "purpose": "deterministic_canonical_shortlist_per_l2_bucket",
        },
        "inputs": {
            "candidate_bank": str(IN_CANDIDATE_BANK.relative_to(ROOT)),
            "topic_taxonomy_view_part1": str(IN_VIEW_P1.relative_to(ROOT)),
            "topic_taxonomy_view_part2": str(IN_VIEW_P2.relative_to(ROOT)),
        },
        "global_summary": {
            "total_l2_buckets_processed": total_l2_buckets_processed,
            "total_raw_candidate_labels_considered": total_raw_candidate_labels,
            "total_proposed_canonical_l3_labels": total_proposed_canonical_labels,
            "average_proposed_canonical_labels_per_l2_bucket": avg_per_bucket,
        },
        "by_l1": out_by_l1,
    }

    write_json(OUT_JSON, payload)
    write_text(OUT_MD, "\n".join(review_lines).strip() + "\n")

    print(f"l2 buckets processed: {total_l2_buckets_processed}")
    print(f"raw candidate labels considered: {total_raw_candidate_labels}")
    print(f"proposed canonical labels: {total_proposed_canonical_labels}")
    print(f"avg canonical labels per l2 bucket: {avg_per_bucket}")
    print(f"Wrote shortlist json to: {OUT_JSON}")
    print(f"Wrote review markdown to: {OUT_MD}")


if __name__ == "__main__":
    main()

