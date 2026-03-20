#!/usr/bin/env python3
"""
assign_primary_l3_v2_refined.py

Refined primary-L3 assignment using targeted taxonomy calibration.
Writes additive outputs only.

Merged JSON inputs (same as assign_primary_l3_v2.py):
- Default: repo root merged_part1.json / merged_part2.json
- --quarter <id> → data/quarters/<id>/merged_part*.json
- --part1 PATH --part2 PATH (both required if either set)
"""

from __future__ import annotations

import argparse
import json
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

CURATED_PATH = ROOT / "config" / "topic_taxonomy_v2_curated_refined.yaml"
P1_PATH = ROOT / "merged_part1.json"
P2_PATH = ROOT / "merged_part2.json"

PREV_P1 = ROOT / "human-in-the-loop" / "topic_taxonomy_assignment_v2_part1.json"
PREV_P2 = ROOT / "human-in-the-loop" / "topic_taxonomy_assignment_v2_part2.json"

OUT_P1 = ROOT / "human-in-the-loop" / "topic_taxonomy_assignment_v2_refined_part1.json"
OUT_P2 = ROOT / "human-in-the-loop" / "topic_taxonomy_assignment_v2_refined_part2.json"
OUT_DIAG = ROOT / "human-in-the-loop" / "l3_assignment_diagnostics_v2_refined.md"

L1_ALIASES = {"experience/activity": "experience_activity"}

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
    "thing",
}

LABEL_HINTS = {
    "conversation": {"chat", "talk", "speaking", "communication", "discuss", "chatting"},
    "sharing": {"share", "shared", "sharing"},
    "advice_support": {"advice", "suggestion", "recommend"},
    "encouragement": {"encourage", "motivate"},
    "apology_repair": {"apology", "apologize", "sorry"},
    "resource_exchange": {"borrow", "borrowed", "lend", "lending", "exchange"},
    "foreign_language_communication": {"foreign", "language", "english", "speak"},
    "happiness": {"happy", "smile", "joy", "enjoy"},
    "attachment": {"keep", "kept", "treasure", "sentimental"},
    "patience": {"wait", "waiting", "patient"},
    "regret": {"regret", "sorry", "apology"},
    "anger": {"angry", "anger", "annoyed"},
    "frustration": {"frustrated", "frustration", "broke", "broken"},
    "self_improvement": {"improve", "improvement", "develop", "better"},
    "adaptation": {"adapt", "change", "new"},
    "decision_making": {"decision", "choose", "chose"},
    "goal_setting": {"goal", "dream", "plan"},
    "problem_solving": {"problem", "solve", "solution", "fix", "repair", "broke", "broken", "damage"},
    "learning_growth": {"learn", "learning", "study"},
    "resilience": {"overcome", "recover", "persist"},
    "study_subject": {"subject", "science", "biology", "robotics", "study"},
    "learning_method": {"method", "typing", "skill"},
    "self_study": {"self_study", "alone", "without_teacher"},
    "academic_interest": {"interest", "interested", "field"},
    "exam_preparation": {"exam", "test", "prepare"},
    "language_learning": {"language", "english"},
    "job_role": {"job", "role", "position", "work"},
    "workplace_experience": {"workplace", "office", "company", "work"},
    "career_planning": {"career", "future", "plan"},
    "professional_growth": {"promotion", "skill", "growth"},
    "service_experience": {"service", "staff", "customer", "shop"},
    "work_life_balance": {"balance", "stress", "rest"},
    "technology": {"technology", "app", "computer", "phone", "electricity"},
    "media": {"program", "tv", "online", "media", "movie", "film"},
    "money": {"money", "expensive", "cost", "spend"},
    "book_or_reading_material": {"book", "reading", "read", "material", "story"},
    "digital_service": {"online", "digital", "platform", "service"},
    "information_resource": {"information", "resource", "knowledge", "useful"},
    "gift_item": {"gift", "present"},
    "personal_item": {"shoe", "key", "personal"},
    "food_gardening_item": {"food", "fruit", "vegetable", "plant", "growing"},
    "photography_item": {"photo", "camera", "photograph"},
    "transport_item": {"bicycle", "motorcycle", "car", "trip"},
    "household_item": {"home", "household"},
    "family_bond": {"family", "relative", "bond"},
    "friendship": {"friend", "friendship"},
    "supportive_relationship": {"help", "support"},
    "family_activity": {"dinner", "together"},
    "family_pride_moment": {"proud", "family"},
    "family_memory": {"kept", "memory", "old", "important"},
    "elderly_people": {"old", "elderly", "senior"},
    "intergenerational_contact": {"stay", "staying", "with", "generation", "old", "young", "contact"},
    "social_support": {"support", "care"},
    "aging_experience": {"aging", "older", "old"},
    "older_generation": {"generation", "older"},
    "sportsperson": {"sportsperson", "athlete"},
    "public_figure": {"famous", "celebrity"},
    "admired_professional": {"admire", "respect", "professional"},
    "achievement": {"achievement", "success"},
    "professional_role": {"role", "profession", "career"},
    "home": {"home", "house"},
    "accommodation": {"accommodation", "apartment"},
    "building": {"building"},
    "museum": {"museum"},
    "shopping_venue": {"shop", "store", "mall"},
    "workplace": {"office", "workplace"},
    "city_space": {"city", "hometown", "town"},
    "neighborhood_area": {"area", "neighborhood"},
    "public_place": {"public", "crowded"},
    "scenery": {"scenery", "view"},
    "nature_place": {"natural", "park", "mountain", "quiet"},
    "travel_destination": {"destination", "visit", "travel"},
    "shopping": {"shop", "shopping", "store"},
    "entertainment": {"music", "movie", "show", "program"},
    "exercise": {"exercise", "sport", "walking"},
    "reading": {"reading", "book", "read"},
    "travel": {"travel", "trip", "journey", "lost", "way"},
    "hobby": {"hobby", "pastime"},
    "daily_life_pattern": {"daily", "routine", "regular"},
    "morning_routine": {"morning", "wake"},
    "habit_building": {"habit"},
    "rest_break": {"break", "day", "off", "rest"},
    "leisure_time": {"spare", "free", "going", "out"},
    "self_care_routine": {"self", "care", "health"},
    "memory_reflection": {"memory", "remember"},
}

# Deterministic bucket priority used at final tie-break stage.
BUCKET_L3_PRIORITY = {
    ("experience_activity", "work"): [
        "job_role",
        "workplace_experience",
        "career_planning",
        "professional_growth",
        "service_experience",
        "work_life_balance",
    ],
    ("people", "general"): [
        "intergenerational_contact",
        "elderly_people",
        "social_support",
        "aging_experience",
        "older_generation",
    ],
    ("people", "close_bonds"): [
        "family_bond",
        "family_memory",
        "supportive_relationship",
        "friendship",
        "family_pride_moment",
        "family_activity",
    ],
    ("object", "intangible"): [
        "book_or_reading_material",
        "information_resource",
        "technology",
        "media",
        "digital_service",
        "money",
    ],
    ("abstract_concepts", "emotion"): [
        "frustration",
        "regret",
        "anger",
        "happiness",
        "attachment",
        "patience",
        "anxiety",
        "pride",
    ],
    ("abstract_concepts", "personal_growth"): [
        "problem_solving",
        "self_improvement",
        "adaptation",
        "decision_making",
        "goal_setting",
        "learning_growth",
        "resilience",
    ],
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
    toks = re.findall(r"[a-zA-Z]+", text.lower())
    out = []
    for t in toks:
        n = normalize_word(t)
        if not n or n in STOPWORDS:
            continue
        out.append(n)
    return out


def label_keywords(label: str) -> set[str]:
    base = {normalize_word(x) for x in label.split("_") if x}
    hints = {normalize_word(x) for x in LABEL_HINTS.get(label, set())}
    return base | hints


def build_text_parts(topic_obj: dict[str, Any], part: int) -> dict[str, str]:
    if part == 1:
        title = str(topic_obj.get("topic_en", "")).strip()
        q = " ".join(str(i.get("text", "")).strip() for i in (topic_obj.get("questions", []) or []))
        return {"title": title, "prompt": "", "part3": q}
    title = str(topic_obj.get("topic", "")).strip()
    cue = topic_obj.get("cue_card", {}) or {}
    prompt = str(cue.get("prompt", "")).strip()
    yss = " ".join(str(x).strip() for x in (cue.get("you_should_say", []) or []))
    part3 = " ".join(str(i.get("text", "")).strip() for i in (topic_obj.get("part3", []) or []))
    return {"title": title, "prompt": f"{prompt} {yss}".strip(), "part3": part3}


def bucket_priority_index(l1: str, l2: str, l3: str) -> int:
    arr = BUCKET_L3_PRIORITY.get((l1, l2), [])
    if l3 in arr:
        return arr.index(l3)
    return 999


def score_candidate(
    *,
    topic_title: str,
    l1: str,
    l2: str,
    l3: str,
    title_tokens: list[str],
    prompt_tokens: list[str],
    part3_tokens: list[str],
    old_l3_tokens: set[str],
    full_text: str,
) -> dict[str, Any]:
    kws = label_keywords(l3)
    title_hits = sum(1 for t in title_tokens if t in kws)
    prompt_hits = sum(1 for t in prompt_tokens if t in kws)
    part3_hits = sum(1 for t in part3_tokens if t in kws)
    old_overlap = len(set(l3.split("_")) & old_l3_tokens)
    old_exact = int(l3 in old_l3_tokens)
    exact_title_phrase = int(l3.replace("_", " ") in topic_title.lower())
    exact_full_phrase = int(l3.replace("_", " ") in full_text)

    score = 0.0
    score += 2.4 * title_hits
    score += 1.9 * prompt_hits
    score += 1.2 * part3_hits
    score += 1.6 * exact_title_phrase
    score += 1.2 * exact_full_phrase
    score += 1.3 * old_overlap
    score += 1.8 * old_exact

    # Bucket-sensitive boosts / penalties.
    t = topic_title.lower()
    all_tokens = set(title_tokens + prompt_tokens + part3_tokens)

    # Book/useful topics in intangible bucket.
    if (l1, l2) == ("object", "intangible") and ("book" in all_tokens or "read" in all_tokens):
        if l3 == "book_or_reading_material":
            score += 3.2
        if l3 in {"information_resource", "media"}:
            score += 1.1
        if l3 == "money":
            score -= 0.8

    # Broke something -> prefer problem solving over regret unless clear regret signals.
    if "broke" in all_tokens or "broken" in all_tokens or "damage" in all_tokens:
        if l3 == "problem_solving":
            score += 3.2
        if l3 == "frustration":
            score += 1.0
        if l3 == "regret" and not ({"sorry", "regret", "apology"} & all_tokens):
            score -= 1.4

    # Family-kept-important topic.
    if {"family", "kept"} <= all_tokens or "has been kept in your family" in t:
        if l3 in {"family_bond", "family_memory"}:
            score += 2.8
        if l3 == "family_activity":
            score -= 0.8

    # Work generic topic.
    if topic_title.strip().lower() == "work":
        if l3 in {"job_role", "workplace_experience"}:
            score += 2.8
        if l3 == "work_life_balance":
            if {"balance", "stress"} & all_tokens:
                score += 1.4
            else:
                score -= 1.2

    # Staying with old people.
    if "staying with old people" in t:
        if l3 == "intergenerational_contact":
            score += 2.6
        if l3 == "elderly_people":
            score += 0.9

    reasons = []
    if title_hits:
        reasons.append(f"title_hits={title_hits}")
    if prompt_hits:
        reasons.append(f"prompt_hits={prompt_hits}")
    if part3_hits:
        reasons.append(f"part3_hits={part3_hits}")
    if old_overlap:
        reasons.append(f"old_l3_overlap={old_overlap}")
    if old_exact:
        reasons.append("old_l3_exact")

    return {
        "l1": l1,
        "l2": l2,
        "l3": l3,
        "score": round(score, 4),
        "title_hits": title_hits,
        "prompt_hits": prompt_hits,
        "part3_hits": part3_hits,
        "old_overlap": old_overlap,
        "old_exact": old_exact,
        "exact_title_phrase": exact_title_phrase,
        "reasons": reasons,
    }


def confidence(best_score: float, second_score: float) -> str:
    gap = best_score - second_score
    if best_score >= 7.0 and gap >= 1.5:
        return "high"
    if best_score >= 4.0 and gap >= 0.9:
        return "medium"
    return "low"


def deterministic_fallback(topic_title: str, l1: str, l2_list: list[str]) -> tuple[str | None, str | None]:
    t = topic_title.lower().strip()
    if "typing" in t:
        return ("study", "learning_method")
    if t == "hobby":
        return ("routines", "hobby")
    if "chatting" in t:
        return ("communication", "conversation")
    if t == "going out":
        return ("routines", "leisure_time")
    if "day off" in t:
        return ("routines", "rest_break")
    if "solved a problem in a smart way" in t:
        if "personal_growth" in l2_list:
            return ("personal_growth", "problem_solving")
        if "personal_traits" in l2_list:
            return ("personal_traits", "confidence")
        return ("time", "milestone")
    if "makes plans a lot" in t:
        if "professions" in l2_list:
            return ("professions", "professional_role")
        return ("close_bonds", "supportive_relationship")
    if "quiet place you like to go" in t:
        return ("outdoor", "nature_place")
    if "lost your way" in t:
        return ("leisure", "travel")
    return (None, None)


def assign_topic(topic_obj: dict[str, Any], part: int, curated: dict[str, Any], threshold: float) -> tuple[dict[str, Any], dict[str, Any]]:
    parts = build_text_parts(topic_obj, part)
    title = parts["title"]
    title_tokens = tokenize(parts["title"])
    prompt_tokens = tokenize(parts["prompt"])
    part3_tokens = tokenize(parts["part3"])
    full_text = " ".join([parts["title"], parts["prompt"], parts["part3"]]).lower()

    ct = topic_obj.get("content_tags", {}) or {}
    l1 = normalize_l1(str(ct.get("l1", "")).strip())
    l2_list = [str(x).strip() for x in (ct.get("l2", []) or []) if str(x).strip()]
    old_l3_list = [str(x).strip() for x in (ct.get("l3", []) or []) if str(x).strip()]
    old_l3_tokens = {normalize_word(t) for item in old_l3_list for t in re.split(r"[_\-\s]+", item.lower()) if t}

    curated_l1 = (curated.get("l1", {}) or {}).get(l1, {}) or {}
    scored = []
    for l2 in l2_list:
        l3s = ((curated_l1.get(l2) or {}).get("l3") or [])
        for l3 in l3s:
            scored.append(
                score_candidate(
                    topic_title=title,
                    l1=l1,
                    l2=l2,
                    l3=l3,
                    title_tokens=title_tokens,
                    prompt_tokens=prompt_tokens,
                    part3_tokens=part3_tokens,
                    old_l3_tokens=old_l3_tokens,
                    full_text=full_text,
                )
            )

    # B1 deterministic tie-break priority:
    # 1 exact title concept match, 2 prompt match, 3 part3 support, 4 old_l3 overlap, 5 bucket priority
    scored.sort(
        key=lambda r: (
            -r["score"],
            -r["exact_title_phrase"],
            -r["prompt_hits"],
            -r["part3_hits"],
            -r["old_overlap"],
            bucket_priority_index(r["l1"], r["l2"], r["l3"]),
            r["l2"],
            r["l3"],
        )
    )

    notes: list[str] = []
    best = scored[0] if scored else None
    second = scored[1] if len(scored) > 1 else None

    chosen_l2 = best["l2"] if best else (l2_list[0] if l2_list else None)
    chosen_l3 = best["l3"] if best else None
    best_score = best["score"] if best else 0.0
    second_score = second["score"] if second else 0.0
    used_fallback = False

    if best_score <= threshold:
        chosen_l3 = None
        notes.append(f"score_below_threshold:{best_score:.2f}")

    # B3 deterministic fallback for previous unassigned-like cases.
    if chosen_l3 is None:
        fb_l2, fb_l3 = deterministic_fallback(title, l1, l2_list)
        if fb_l2 and fb_l3 and fb_l2 in l2_list and fb_l3 in (((curated_l1.get(fb_l2) or {}).get("l3") or [])):
            chosen_l2 = fb_l2
            chosen_l3 = fb_l3
            best_score = max(best_score, threshold + 0.3)
            used_fallback = True
            notes.append("deterministic_fallback_applied")

    conf = confidence(best_score, second_score) if chosen_l3 else "low"
    if used_fallback and conf == "low":
        conf = "medium"
    ambiguous = bool(chosen_l3 and (best_score - second_score) < 0.6 and not used_fallback)
    if ambiguous:
        notes.append(f"ambiguous_top_gap:{(best_score-second_score):.2f}")

    row = {
        "topic": title,
        "taxonomy_v2": {
            "primary": {"l1": l1 or None, "l2": chosen_l2, "l3": chosen_l3},
            "diagnostics": {
                "score": round(best_score, 3),
                "second_best_score": round(second_score, 3),
                "confidence": conf,
                "ambiguous": ambiguous,
                "reasons": (best["reasons"] if best else []),
                "notes": notes,
                "top_candidates": [
                    {"l2": r["l2"], "l3": r["l3"], "score": round(r["score"], 3)}
                    for r in scored[:3]
                ],
            },
        },
    }
    stat = {
        "topic": title,
        "assigned": bool(chosen_l3),
        "confidence": conf,
        "ambiguous": ambiguous,
        "best_score": best_score,
        "second_score": second_score,
        "best_l1": l1,
        "best_l2": chosen_l2,
        "best_l3": chosen_l3,
        "top_candidates": row["taxonomy_v2"]["diagnostics"]["top_candidates"],
    }
    return row, stat


def run_part(data: list[dict[str, Any]], part: int, curated: dict[str, Any], threshold: float) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    rows = []
    stats = []
    for topic in data:
        r, s = assign_topic(topic, part, curated, threshold)
        rows.append(r)
        stats.append(s)
    return rows, stats


def compare_changes(prev_rows: list[dict[str, Any]], new_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    prev_map = {r["topic"]: (((r.get("taxonomy_v2") or {}).get("primary") or {}).get("l3")) for r in prev_rows}
    out = []
    for r in new_rows:
        topic = r["topic"]
        new_l3 = (((r.get("taxonomy_v2") or {}).get("primary") or {}).get("l3"))
        old_l3 = prev_map.get(topic)
        if old_l3 != new_l3:
            out.append({"topic": topic, "before": old_l3, "after": new_l3})
    return out


def build_diagnostics_md(
    *,
    before_stats: dict[str, int],
    after_stats: dict[str, int],
    remaining_unassigned: list[dict[str, Any]],
    remaining_low_conf: list[dict[str, Any]],
    changed: list[dict[str, Any]],
) -> str:
    lines = []
    lines.append("# L3 Assignment Diagnostics v2 Refined")
    lines.append("")
    lines.append("## Before vs After")
    lines.append(f"- before assigned L3: {before_stats['assigned']}")
    lines.append(f"- after assigned L3: {after_stats['assigned']}")
    lines.append(f"- before unassigned topics: {before_stats['unassigned']}")
    lines.append(f"- after unassigned topics: {after_stats['unassigned']}")
    lines.append(f"- before low-confidence assignments: {before_stats['low_conf']}")
    lines.append(f"- after low-confidence assignments: {after_stats['low_conf']}")
    lines.append(f"- topics with changed primary.l3: {len(changed)}")
    lines.append("")
    lines.append("## Remaining Unassigned Topics")
    if remaining_unassigned:
        for s in remaining_unassigned:
            lines.append(f"- {s['topic']} (best score={s['best_score']:.2f})")
    else:
        lines.append("- none")
    lines.append("")
    lines.append("## Remaining Low-Confidence Topics")
    if remaining_low_conf:
        for s in remaining_low_conf:
            lines.append(
                f"- {s['topic']}: {s['best_l1']} > {s['best_l2']} > {s['best_l3']} (score={s['best_score']:.2f})"
            )
    else:
        lines.append("- none")
    lines.append("")
    lines.append("## Topics With Changed primary.l3")
    if changed:
        for c in changed:
            lines.append(f"- {c['topic']}: {c['before']} -> {c['after']}")
    else:
        lines.append("- none")
    lines.append("")
    lines.append(
        f"_Generated at {datetime.now(timezone.utc).isoformat()} by `pipeline/assign_primary_l3_v2_refined.py`_"
    )
    return "\n".join(lines) + "\n"


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Refined primary-L3 assignment (reads prior assignment from human-in-the-loop/)."
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
    prev_p1 = load_json(PREV_P1)
    prev_p2 = load_json(PREV_P2)

    threshold = 1.5
    p1_rows, p1_stats = run_part(p1, part=1, curated=curated, threshold=threshold)
    p2_rows, p2_stats = run_part(p2, part=2, curated=curated, threshold=threshold)
    all_rows = p1_rows + p2_rows
    all_stats = p1_stats + p2_stats

    write_json(OUT_P1, p1_rows)
    write_json(OUT_P2, p2_rows)

    before_assigned = sum(1 for r in (prev_p1 + prev_p2) if (((r.get("taxonomy_v2") or {}).get("primary") or {}).get("l3")))
    before_total = len(prev_p1) + len(prev_p2)
    before_unassigned = before_total - before_assigned
    before_low = sum(
        1
        for r in (prev_p1 + prev_p2)
        if (((r.get("taxonomy_v2") or {}).get("primary") or {}).get("l3"))
        and (((r.get("taxonomy_v2") or {}).get("diagnostics") or {}).get("confidence") == "low")
    )

    after_assigned = sum(1 for s in all_stats if s["assigned"])
    after_total = len(all_stats)
    after_unassigned = after_total - after_assigned
    after_low = sum(1 for s in all_stats if s["assigned"] and s["confidence"] == "low")

    changed = compare_changes(prev_p1 + prev_p2, all_rows)
    remaining_unassigned = [s for s in all_stats if not s["assigned"]]
    remaining_low = [s for s in all_stats if s["assigned"] and s["confidence"] == "low"]

    md = build_diagnostics_md(
        before_stats={"assigned": before_assigned, "unassigned": before_unassigned, "low_conf": before_low},
        after_stats={"assigned": after_assigned, "unassigned": after_unassigned, "low_conf": after_low},
        remaining_unassigned=remaining_unassigned,
        remaining_low_conf=remaining_low,
        changed=changed,
    )
    write_text(OUT_DIAG, md)

    print(f"Input Part 1: {p1_path}")
    print(f"Input Part 2: {p2_path}")
    print(f"assigned L3: {after_assigned}")
    print(f"unassigned topics: {after_unassigned}")
    print(f"low-confidence assignments: {after_low}")
    print(f"changed primary.l3 topics: {len(changed)}")
    print(f"Wrote: {OUT_P1}")
    print(f"Wrote: {OUT_P2}")
    print(f"Wrote: {OUT_DIAG}")


if __name__ == "__main__":
    main()

