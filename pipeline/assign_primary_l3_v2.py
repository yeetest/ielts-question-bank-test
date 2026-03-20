#!/usr/bin/env python3
"""
assign_primary_l3_v2.py

Automatic primary-L3 assignment engine using curated taxonomy.

Inputs:
- config/topic_taxonomy_v2_curated.yaml
- merged_part1.json + merged_part2.json (default: repo root), or:
  - --quarter <id> → data/quarters/<id>/merged_part*.json
  - --part1 PATH --part2 PATH (both required if either set)

Outputs:
- human-in-the-loop/topic_taxonomy_assignment_v2_part1.json
- human-in-the-loop/topic_taxonomy_assignment_v2_part2.json
- human-in-the-loop/l3_assignment_diagnostics_v2.md

Notes:
- This script does NOT overwrite original content_tags.
- It writes a new `taxonomy_v2` field in side output files only.
"""

from __future__ import annotations

import argparse
import json
import math
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError as exc:  # pragma: no cover
    raise SystemExit("PyYAML is required. Install with: pip3 install pyyaml") from exc


ROOT = Path(__file__).resolve().parent.parent

CURATED_PATH = ROOT / "config" / "topic_taxonomy_v2_curated.yaml"
P1_PATH = ROOT / "merged_part1.json"
P2_PATH = ROOT / "merged_part2.json"

OUT_P1 = ROOT / "human-in-the-loop" / "topic_taxonomy_assignment_v2_part1.json"
OUT_P2 = ROOT / "human-in-the-loop" / "topic_taxonomy_assignment_v2_part2.json"
OUT_DIAG = ROOT / "human-in-the-loop" / "l3_assignment_diagnostics_v2.md"


L1_ALIASES = {
    "experience/activity": "experience_activity",
}

# Legacy / auto-tag strings in content_tags.l3 → curated YAML l3 label (subset check uses exact strings).
LEGACY_CONTENT_L3_TO_CURATED = {
    "traveling": "travel",
    "learning": "learning_growth",
    "decision": "decision_making",
}


def norm_l3_key(s: str) -> str:
    return str(s or "").strip().lower().replace("-", "_")


def curated_labels_aligned_with_content_l3(old_l3_list: list[str]) -> set[str]:
    """Curated l3 labels that should get a strong alignment bonus from existing card l3."""
    aligned: set[str] = set()
    for raw in old_l3_list:
        k = norm_l3_key(raw)
        if k in LEGACY_CONTENT_L3_TO_CURATED:
            aligned.add(LEGACY_CONTENT_L3_TO_CURATED[k])
        else:
            aligned.add(k)
    return aligned


def primary_l2_index(l2: str, l2_list: list[str]) -> int:
    try:
        return l2_list.index(l2)
    except ValueError:
        return 999

STOPWORDS = {
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
    "at",
    "as",
    "by",
    "this",
    "that",
    "these",
    "those",
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
    "cannot",
    "cant",
    "you",
    "your",
    "i",
    "we",
    "they",
    "he",
    "she",
    "it",
    "who",
    "what",
    "when",
    "where",
    "why",
    "how",
    "something",
    "someone",
    "anything",
    "anyone",
    "time",
    "person",
    "people",
    "place",
    "thing",
}

# Label-specific expansion hints for semantic matching.
LABEL_HINTS = {
    "conversation": {"chat", "talk", "speaking", "communication", "discuss"},
    "sharing": {"share", "shared", "sharing"},
    "advice_support": {"advice", "suggestion", "recommend", "support"},
    "encouragement": {"encourage", "motivate", "motivation"},
    "apology_repair": {"apology", "apologize", "sorry", "repair"},
    "resource_exchange": {"borrow", "borrowed", "lend", "lending", "exchange"},
    "foreign_language_communication": {"foreign", "language", "english", "speak"},
    # Omit "enjoy" — phrases like "didn't enjoy" falsely boost happiness over anger / learning_growth.
    "happiness": {"happy", "smile", "joy"},
    "attachment": {"keep", "kept", "treasure", "sentimental"},
    "patience": {"wait", "waiting", "patient"},
    "regret": {"regret", "sorry", "mistake"},
    "anger": {"angry", "anger", "annoyed"},
    "anxiety": {"anxious", "worry", "nervous"},
    "pride": {"proud", "pride"},
    "self_improvement": {"improve", "improvement", "develop", "better"},
    "adaptation": {"adapt", "change", "new"},
    "decision_making": {"decision", "choose", "chose"},
    "goal_setting": {"goal", "dream", "plan"},
    "problem_solving": {"problem", "solve", "solution"},
    "learning_growth": {"learn", "learning", "learned", "study"},
    "resilience": {"overcome", "recover", "persist"},
    "creativity": {"creative", "creativity", "imagination", "artist"},
    "confidence": {"confident", "confidence"},
    "independence": {"independent", "alone", "self"},
    "discipline": {"discipline", "self_control"},
    "responsibility": {"responsible", "responsibility"},
    "kindness": {"kind", "helpful"},
    "childhood": {"child", "childhood", "kid"},
    "life_stage": {"stage", "phase", "age"},
    "milestone": {"milestone", "first", "important"},
    "routine_cycle": {"routine", "daily", "habit"},
    "transition_period": {"change", "transition"},
    "memory_reflection": {"memory", "remember", "reflection"},
    "environment": {"environment", "nature", "animal", "wild", "protect"},
    "policy": {"policy", "rule", "government", "law"},
    "fairness": {"fair", "equality"},
    "sustainability": {"sustainable", "sustainability"},
    "civic_mindedness": {"community", "civic", "public"},
    "role_modeling": {"role", "model", "admire"},
    "social_influence": {"influence", "influenced"},
    "peer_influence": {"peer", "friend", "classmate"},
    "media_influence": {"media", "online", "social"},
    "motivation": {"motivation", "motivate"},
    "shopping": {"shop", "shopping", "store", "mall"},
    "entertainment": {"entertainment", "music", "movie", "show", "program"},
    "exercise": {"exercise", "sport", "walking", "fitness"},
    "reading": {"read", "reading", "book"},
    "travel": {"travel", "trip", "journey", "visit"},
    "hobby": {"hobby", "pastime"},
    "daily_life_pattern": {"daily", "routine", "regular"},
    "morning_routine": {"morning", "breakfast", "wake"},
    "habit_building": {"habit", "develop"},
    "rest_break": {"break", "rest", "relax"},
    "leisure_time": {"spare", "free_time", "leisure"},
    "self_care_routine": {"self_care", "care", "health"},
    "study_subject": {"subject", "science", "biology", "robotics", "study"},
    "learning_method": {"method", "way", "learn"},
    "self_study": {"self_study", "alone", "without_teacher"},
    "academic_interest": {"interest", "interested", "field"},
    "exam_preparation": {"exam", "test", "prepare"},
    "language_learning": {"language", "english", "speak"},
    "career_planning": {"career", "future_job", "plan"},
    "workplace_experience": {"work", "office", "company"},
    "job_role": {"job", "role", "position"},
    "work_life_balance": {"balance", "work", "life"},
    "professional_growth": {"promotion", "skill", "career_growth"},
    "service_experience": {"service", "staff", "customer"},
    "technology": {"technology", "app", "computer", "phone", "electricity"},
    "artwork": {"art", "painting", "drawing", "story", "movie"},
    "media": {"program", "tv", "online", "media"},
    "money": {"money", "expensive", "cost", "spend"},
    "digital_service": {"online", "digital", "platform"},
    "information_resource": {"information", "resource", "reference"},
    "gift_item": {"gift", "present"},
    "personal_item": {"shoe", "key", "personal"},
    "food_gardening_item": {"food", "fruit", "vegetable", "plant"},
    "photography_item": {"photo", "camera"},
    "transport_item": {"bicycle", "motorcycle", "car"},
    "household_item": {"home", "household"},
    "family_bond": {"family", "relative", "parent"},
    "friendship": {"friend", "friendship"},
    "supportive_relationship": {"help", "support"},
    "family_activity": {"dinner", "together"},
    "family_pride_moment": {"proud", "family"},
    "sportsperson": {"sportsperson", "athlete"},
    "public_figure": {"famous", "celebrity"},
    "service_worker": {"staff", "worker", "employee"},
    "creative_professional": {"artist", "musician", "creative"},
    "educator": {"teacher", "educator"},
    "business_owner": {"business", "owner", "shop"},
    "elderly_people": {"old", "elderly", "senior"},
    "intergenerational_contact": {"generation", "old", "young"},
    "social_support": {"support", "care"},
    "personality_trait": {"personality", "trait"},
    "community_member": {"community", "member"},
    "home": {"home", "accommodation", "house"},
    "building": {"building"},
    "shopping_venue": {"shop", "store", "mall"},
    "museum": {"museum"},
    "accommodation": {"accommodation", "apartment"},
    "workplace": {"office", "workplace"},
    "city_space": {"city", "hometown", "town"},
    "neighborhood_area": {"area", "neighborhood"},
    "public_place": {"public", "crowded"},
    "scenery": {"scenery", "view"},
    "nature_place": {"natural", "park", "mountain"},
    "travel_destination": {"destination", "visit", "travel"},
}


def load_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def load_yaml(path: Path) -> Any:
    with path.open(encoding="utf-8") as f:
        return yaml.safe_load(f)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        f.write(content)


def normalize_l1(l1: str) -> str:
    return L1_ALIASES.get(l1, l1)


def normalize_word(w: str) -> str:
    w = w.lower().strip()
    if not w:
        return ""
    if w.endswith("ies") and len(w) > 4:
        return w[:-3] + "y"
    if w.endswith("s") and len(w) > 3 and not w.endswith(("ss", "us", "is")):
        return w[:-1]
    return w


def tokenize(text: str) -> list[str]:
    tokens = re.findall(r"[a-zA-Z]+", text.lower())
    out = []
    for t in tokens:
        t = normalize_word(t)
        if not t or t in STOPWORDS:
            continue
        out.append(t)
    return out


def label_keywords(label: str) -> set[str]:
    base = set(normalize_word(t) for t in label.split("_") if t)
    hints = set(normalize_word(h) for h in LABEL_HINTS.get(label, set()))
    return base | hints


def build_text_parts(topic_obj: dict[str, Any], part: int) -> dict[str, str]:
    if part == 1:
        title = str(topic_obj.get("topic_en", "")).strip()
        questions = topic_obj.get("questions", []) or []
        q_text = " ".join(str(q.get("text", "")).strip() for q in questions)
        return {"title": title, "prompt": "", "part3": q_text}

    title = str(topic_obj.get("topic", "")).strip()
    cue = topic_obj.get("cue_card", {}) or {}
    prompt = str(cue.get("prompt", "")).strip()
    you_should_say = " ".join(str(x).strip() for x in (cue.get("you_should_say", []) or []))
    part3 = " ".join(str(q.get("text", "")).strip() for q in (topic_obj.get("part3", []) or []))
    return {"title": title, "prompt": f"{prompt} {you_should_say}".strip(), "part3": part3}


def score_candidate_l3(
    label: str,
    *,
    title_tokens: list[str],
    prompt_tokens: list[str],
    part3_tokens: list[str],
    old_l3_tokens: set[str],
    aligned_curated_l3: set[str],
    full_text: str,
) -> tuple[float, list[str]]:
    reasons: list[str] = []
    score = 0.0
    kws = label_keywords(label)

    # A) weighted keyword matches from title/prompt/part3
    title_hits = sum(1 for t in title_tokens if t in kws)
    prompt_hits = sum(1 for t in prompt_tokens if t in kws)
    part3_hits = sum(1 for t in part3_tokens if t in kws)
    if title_hits:
        score += 2.2 * title_hits
        reasons.append(f"title_hits={title_hits}")
    if prompt_hits:
        score += 1.6 * prompt_hits
        reasons.append(f"prompt_hits={prompt_hits}")
    if part3_hits:
        score += 1.1 * part3_hits
        reasons.append(f"part3_hits={part3_hits}")

    # Exact phrase match bonus.
    if label.replace("_", " ") in full_text:
        score += 2.4
        reasons.append("exact_phrase_match")

    # B) semantic hints from topic title verbs/nouns (lightweight token relevance).
    if title_tokens:
        top_title_tokens = title_tokens[: min(8, len(title_tokens))]
        hint_hits = sum(1 for t in top_title_tokens if t in kws)
        if hint_hits:
            score += 1.3 * hint_hits
            reasons.append(f"title_semantic_hints={hint_hits}")

    # C) support from old L3 if available.
    if old_l3_tokens:
        label_tokens = set(label.split("_"))
        overlap = len(label_tokens & old_l3_tokens)
        if overlap:
            score += 1.8 * overlap
            reasons.append(f"old_l3_overlap={overlap}")
        if label in old_l3_tokens:
            score += 2.2
            reasons.append("old_l3_exact")

    # D) Strong preference when curated label matches card l3 (incl. legacy → canonical map).
    if aligned_curated_l3 and label in aligned_curated_l3:
        score += 6.0
        reasons.append("content_l3_aligned")

    # Slight smoothing to avoid all-zero collapse for clearly related labels.
    if score == 0 and any(tok in kws for tok in set(title_tokens + prompt_tokens + part3_tokens)):
        score = 0.5
        reasons.append("weak_semantic_overlap")

    return score, reasons


def choose_primary_l2(l2_candidates: list[str], curated_l2: dict[str, Any]) -> str | None:
    if not l2_candidates:
        return None
    # Keep existing order from topic data; first valid curated bucket wins as base.
    for l2 in l2_candidates:
        if l2 in curated_l2:
            return l2
    return None


def confidence_from_scores(best: float, second: float) -> str:
    gap = best - second
    if best >= 7.0 and gap >= 2.0:
        return "high"
    if best >= 4.0 and gap >= 1.0:
        return "medium"
    return "low"


def assign_for_topic(
    topic_obj: dict[str, Any],
    *,
    part: int,
    curated: dict[str, Any],
    threshold: float,
) -> tuple[dict[str, Any], dict[str, Any]]:
    text_parts = build_text_parts(topic_obj, part)
    title_tokens = tokenize(text_parts["title"])
    prompt_tokens = tokenize(text_parts["prompt"])
    part3_tokens = tokenize(text_parts["part3"])
    full_text = " ".join([text_parts["title"], text_parts["prompt"], text_parts["part3"]]).lower()

    content_tags = topic_obj.get("content_tags", {}) or {}
    raw_l1 = str(content_tags.get("l1", "")).strip()
    l1 = normalize_l1(raw_l1)
    l2_list = [str(x).strip() for x in (content_tags.get("l2", []) or []) if str(x).strip()]
    old_l3_list = [str(x).strip() for x in (content_tags.get("l3", []) or []) if str(x).strip()]
    old_l3_tokens = {normalize_word(t) for item in old_l3_list for t in re.split(r"[_\-\s]+", item.lower()) if t}
    aligned_curated_l3 = curated_labels_aligned_with_content_l3(old_l3_list)

    curated_l2 = (curated.get("l1", {}) or {}).get(l1, {}) or {}
    primary_l2_base = choose_primary_l2(l2_list, curated_l2)

    notes: list[str] = []
    if not l1 or l1 not in (curated.get("l1", {}) or {}):
        notes.append("l1_not_in_curated")
    if not l2_list:
        notes.append("no_candidate_l2")
    if primary_l2_base is None and l2_list:
        notes.append("no_valid_l2_in_curated_for_topic")

    scored_rows: list[tuple[str, str, float, list[str]]] = []
    for l2 in l2_list:
        l2_node = curated_l2.get(l2, {}) or {}
        l3_labels = l2_node.get("l3", []) or []
        for label in l3_labels:
            score, reasons = score_candidate_l3(
                label,
                title_tokens=title_tokens,
                prompt_tokens=prompt_tokens,
                part3_tokens=part3_tokens,
                old_l3_tokens=old_l3_tokens,
                aligned_curated_l3=aligned_curated_l3,
                full_text=full_text,
            )
            scored_rows.append((l2, label, score, reasons))

    scored_rows.sort(
        key=lambda x: (-x[2], primary_l2_index(x[0], l2_list), x[0], x[1])
    )

    # When the card already names specific l3 tokens (incl. legacy→canonical map), only
    # consider curated labels in that aligned set — keeps runtime primary ⊆ content_tags.l3
    # without hand-editing merged JSON. Fall back to full pool if nothing clears threshold.
    if aligned_curated_l3 and scored_rows:
        aligned_only = [
            r for r in scored_rows if r[1] in aligned_curated_l3 and r[2] > threshold
        ]
        if aligned_only:
            aligned_only.sort(
                key=lambda x: (-x[2], primary_l2_index(x[0], l2_list), x[0], x[1])
            )
            scored_rows = aligned_only

    best_l2 = primary_l2_base
    best_l3 = None
    best_score = 0.0
    best_reasons: list[str] = []
    second_score = 0.0

    if scored_rows:
        top = scored_rows[0]
        best_l2, best_l3, best_score, best_reasons = top
        second_score = scored_rows[1][2] if len(scored_rows) > 1 else 0.0

    if best_score <= threshold:
        best_l3 = None
        notes.append(f"score_below_threshold:{best_score:.2f}")

    confidence = confidence_from_scores(best_score, second_score) if best_l3 else "low"
    ambiguous = bool(best_l3 and (best_score - second_score) < 1.0)
    if ambiguous:
        notes.append(f"ambiguous_top_gap:{(best_score-second_score):.2f}")

    topic_title = text_parts["title"]
    row = {
        "topic": topic_title,
        "taxonomy_v2": {
            "primary": {
                "l1": l1 if l1 else None,
                "l2": best_l2,
                "l3": best_l3,
            },
            "diagnostics": {
                "score": round(best_score, 3),
                "second_best_score": round(second_score, 3),
                "confidence": confidence,
                "ambiguous": ambiguous,
                "reasons": best_reasons,
                "notes": notes,
            },
        },
    }

    stat = {
        "topic": topic_title,
        "assigned": bool(best_l3),
        "confidence": confidence,
        "ambiguous": ambiguous,
        "best_score": best_score,
        "second_score": second_score,
        "best_l1": l1,
        "best_l2": best_l2,
        "best_l3": best_l3,
        "top_candidates": [
            {"l2": r[0], "l3": r[1], "score": round(r[2], 3)}
            for r in scored_rows[:3]
        ],
    }
    return row, stat


def run_assignment_for_part(
    data: list[dict[str, Any]],
    *,
    part: int,
    curated: dict[str, Any],
    threshold: float,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    rows = []
    stats = []
    for topic in data:
        row, stat = assign_for_topic(topic, part=part, curated=curated, threshold=threshold)
        rows.append(row)
        stats.append(stat)
    return rows, stats


def make_diagnostics_markdown(
    *,
    all_stats: list[dict[str, Any]],
    total_topics: int,
    assigned: int,
    unassigned: int,
    low_conf: int,
) -> str:
    ambiguous = [s for s in all_stats if s["ambiguous"]]
    ambiguous_sorted = sorted(ambiguous, key=lambda s: (s["best_score"] - s["second_score"], -s["best_score"]))
    low_conf_rows = [s for s in all_stats if s["assigned"] and s["confidence"] == "low"]
    unassigned_rows = [s for s in all_stats if not s["assigned"]]

    l2_counter = Counter((s["best_l1"], s["best_l2"] or "null_l2") for s in all_stats if s["assigned"])

    lines = []
    lines.append("# L3 Assignment Diagnostics v2")
    lines.append("")
    lines.append("## Summary")
    lines.append(f"- total topics: {total_topics}")
    lines.append(f"- assigned L3: {assigned}")
    lines.append(f"- unassigned topics: {unassigned}")
    lines.append(f"- low-confidence assignments: {low_conf}")
    lines.append("")
    lines.append("## Assigned Distribution (top buckets)")
    for (l1, l2), cnt in l2_counter.most_common(12):
        lines.append(f"- {l1} > {l2}: {cnt}")
    lines.append("")
    lines.append("## Top Ambiguous Topics")
    if ambiguous_sorted:
        for s in ambiguous_sorted[:20]:
            gap = s["best_score"] - s["second_score"]
            top = ", ".join(f"{c['l2']}::{c['l3']}={c['score']}" for c in s["top_candidates"])
            lines.append(f"- {s['topic']}")
            lines.append(
                f"  - chosen: {s['best_l1']} > {s['best_l2']} > {s['best_l3']} | score={s['best_score']:.2f} | gap={gap:.2f}"
            )
            lines.append(f"  - top candidates: {top}")
    else:
        lines.append("- none")
    lines.append("")
    lines.append("## Low-Confidence Assignments")
    if low_conf_rows:
        for s in sorted(low_conf_rows, key=lambda x: x["best_score"])[:30]:
            lines.append(
                f"- {s['topic']}: {s['best_l1']} > {s['best_l2']} > {s['best_l3']} (score={s['best_score']:.2f})"
            )
    else:
        lines.append("- none")
    lines.append("")
    lines.append("## Unassigned Topics")
    if unassigned_rows:
        for s in sorted(unassigned_rows, key=lambda x: -x["best_score"])[:50]:
            top = ", ".join(f"{c['l2']}::{c['l3']}={c['score']}" for c in s["top_candidates"])
            lines.append(f"- {s['topic']} (best score={s['best_score']:.2f})")
            if top:
                lines.append(f"  - top candidates: {top}")
    else:
        lines.append("- none")
    lines.append("")
    lines.append(
        f"_Generated at {datetime.now(timezone.utc).isoformat()} by `pipeline/assign_primary_l3_v2.py`_"
    )
    return "\n".join(lines) + "\n"


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Assign primary L3 from curated YAML (does not overwrite content_tags)."
    )
    ap.add_argument(
        "--quarter",
        metavar="ID",
        help="Load data/quarters/<ID>/merged_part1.json and merged_part2.json",
    )
    ap.add_argument("--part1", type=Path, default=None, help="Explicit merged Part 1 JSON path")
    ap.add_argument("--part2", type=Path, default=None, help="Explicit merged Part 2 JSON path")
    args = ap.parse_args()

    if args.quarter and (args.part1 is not None or args.part2 is not None):
        raise SystemExit("Use either --quarter or both --part1 and --part2, not together.")
    if args.part1 is not None or args.part2 is not None:
        if args.part1 is None or args.part2 is None:
            raise SystemExit("When using explicit paths, pass both --part1 and --part2.")
        p1_path = args.part1 if args.part1.is_absolute() else ROOT / args.part1
        p2_path = args.part2 if args.part2.is_absolute() else ROOT / args.part2
    elif args.quarter:
        qd = ROOT / "data" / "quarters" / args.quarter
        p1_path = qd / "merged_part1.json"
        p2_path = qd / "merged_part2.json"
    else:
        p1_path, p2_path = P1_PATH, P2_PATH

    curated = load_yaml(CURATED_PATH)
    p1 = load_json(p1_path)
    p2 = load_json(p2_path)

    threshold = 2.5
    p1_rows, p1_stats = run_assignment_for_part(p1, part=1, curated=curated, threshold=threshold)
    p2_rows, p2_stats = run_assignment_for_part(p2, part=2, curated=curated, threshold=threshold)

    write_json(OUT_P1, p1_rows)
    write_json(OUT_P2, p2_rows)

    all_stats = p1_stats + p2_stats
    total_topics = len(all_stats)
    assigned = sum(1 for s in all_stats if s["assigned"])
    unassigned = total_topics - assigned
    low_conf = sum(1 for s in all_stats if s["assigned"] and s["confidence"] == "low")

    md = make_diagnostics_markdown(
        all_stats=all_stats,
        total_topics=total_topics,
        assigned=assigned,
        unassigned=unassigned,
        low_conf=low_conf,
    )
    write_text(OUT_DIAG, md)

    print(f"Input Part 1: {p1_path}")
    print(f"Input Part 2: {p2_path}")
    print(f"total topics: {total_topics}")
    print(f"assigned L3: {assigned}")
    print(f"unassigned topics: {unassigned}")
    print(f"low-confidence assignments: {low_conf}")
    print(f"Wrote: {OUT_P1}")
    print(f"Wrote: {OUT_P2}")
    print(f"Wrote: {OUT_DIAG}")


if __name__ == "__main__":
    main()

