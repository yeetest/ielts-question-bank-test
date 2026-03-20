#!/usr/bin/env python3
"""
generate_l3_candidates_v2.py

Bottom-up candidate generator for rebuilding L3 vocabulary in a human-in-the-loop flow.

Inputs:
- human-in-the-loop/topic_taxonomy_view_v2_part1.json
- human-in-the-loop/topic_taxonomy_view_v2_part2.json
- config/topic_taxonomy_v2.yaml
- merged_part1.json
- merged_part2.json

Outputs:
- human-in-the-loop/l3_candidate_bank_v2.json
- human-in-the-loop/l3_candidate_review_v2.md
"""

from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError as exc:  # pragma: no cover
    raise SystemExit("PyYAML is required. Install with: pip3 install pyyaml") from exc


ROOT = Path(__file__).resolve().parent.parent

P1_VIEW_PATH = ROOT / "human-in-the-loop" / "topic_taxonomy_view_v2_part1.json"
P2_VIEW_PATH = ROOT / "human-in-the-loop" / "topic_taxonomy_view_v2_part2.json"
CFG_PATH = ROOT / "config" / "topic_taxonomy_v2.yaml"
P1_SRC_PATH = ROOT / "merged_part1.json"
P2_SRC_PATH = ROOT / "merged_part2.json"

OUT_BANK_PATH = ROOT / "human-in-the-loop" / "l3_candidate_bank_v2.json"
OUT_REVIEW_PATH = ROOT / "human-in-the-loop" / "l3_candidate_review_v2.md"


SKILL_LIKE_WORDS = {
    "experience",
    "frequency",
    "description",
    "describe",
    "preference",
    "evaluation",
    "evaluate",
    "analyze",
    "analysis",
    "comparison",
    "hypothetical",
}

TIME_LIKE_WORDS = {
    "past",
    "present",
    "future",
    "today",
    "tomorrow",
    "yesterday",
    "now",
    "current",
    "currently",
    "recent",
    "recently",
    "before",
    "after",
}

QUALIFIER_ONLY_WORDS = {
    "memorable",
    "peaceful",
    "sentimental",
    "interesting",
    "useful",
    "exciting",
    "special",
    "important",
    "good",
    "bad",
    "perfect",
    "quiet",
    "crowded",
    "famous",
    "proud",
    "happy",
    "smart",
}

PROMPT_GLUE_WORDS = {
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
    "at",
    "from",
    "by",
    "as",
    "is",
    "are",
    "was",
    "were",
    "be",
    "been",
    "being",
    "you",
    "your",
    "yours",
    "he",
    "she",
    "his",
    "her",
    "their",
    "they",
    "them",
    "someone",
    "something",
    "anyone",
    "anything",
    "who",
    "whom",
    "whose",
    "which",
    "that",
    "this",
    "these",
    "those",
    "would",
    "could",
    "should",
    "can",
    "cant",
    "cannot",
    "not",
    "have",
    "has",
    "had",
    "do",
    "does",
    "did",
    "done",
    "want",
    "wants",
    "wanted",
    "like",
    "likes",
    "liked",
    "enjoy",
    "enjoyed",
    "enjoys",
    "tell",
    "say",
    "talk",
    "talked",
    "thing",
    "things",
    "time",
    "times",
    "person",
    "people",
    "place",
    "places",
    "item",
    "occasion",
    "topic",
    "part",
    "question",
    "questions",
    "first",
    "second",
    "third",
    "would",
    "when",
    "where",
    "why",
    "how",
    "what",
    "while",
    "into",
    "about",
    "more",
    "very",
    "really",
    "much",
    "many",
    "lot",
    "lots",
    "etc",
    "eg",
}

BLOCKED_SINGLE_WORDS = SKILL_LIKE_WORDS | TIME_LIKE_WORDS | QUALIFIER_ONLY_WORDS | PROMPT_GLUE_WORDS
BLOCKED_PHRASES = {
    "long_time",
    "foreign_country",
    "social_media",  # too platform/time-contextual for core topic noun
}


def load_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def load_yaml(path: Path) -> dict[str, Any]:
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


def normalize_topic_key(title: str) -> str:
    return re.sub(r"\s+", " ", title.strip().lower())


def simple_singular(word: str) -> str:
    if len(word) <= 3:
        return word
    if word.endswith("ies") and len(word) > 4:
        return word[:-3] + "y"
    if word.endswith("ses") and len(word) > 4:
        return word[:-2]
    if word.endswith("s") and not word.endswith(("ss", "us", "is")):
        return word[:-1]
    return word


def normalize_label(raw: str) -> str:
    parts = re.findall(r"[a-z]+", raw.lower())
    if not parts:
        return ""
    singular_parts = [simple_singular(p) for p in parts]
    return "_".join(singular_parts)


def is_blocked_label(label: str) -> bool:
    if not label:
        return True
    if label in BLOCKED_PHRASES:
        return True
    parts = label.split("_")
    if not parts:
        return True
    if any(p in BLOCKED_SINGLE_WORDS for p in parts):
        return True
    if len(parts) == 1 and len(parts[0]) < 3:
        return True
    return False


def extract_tokens(text: str) -> list[str]:
    return re.findall(r"[a-z]+", text.lower())


def extract_candidates_from_text(
    text: str,
    *,
    base_weight: float,
    source_type: str,
    bucket_counter: Counter[str],
) -> dict[str, dict[str, Any]]:
    tokens = extract_tokens(text)
    valid = [t for t in tokens if t not in BLOCKED_SINGLE_WORDS and len(t) >= 3]

    out: dict[str, dict[str, Any]] = {}

    # Unigrams
    for tok in valid:
        label = normalize_label(tok)
        if is_blocked_label(label):
            continue
        score = base_weight
        if tok in bucket_counter:
            score += min(0.6, 0.08 * bucket_counter[tok])
        if label not in out:
            out[label] = {"score": 0.0, "source_types": set()}
        out[label]["score"] += score
        out[label]["source_types"].add(source_type)

    # Bigrams (semantic compact phrases)
    for i in range(len(valid) - 1):
        left = valid[i]
        right = valid[i + 1]
        phrase = f"{left}_{right}"
        label = normalize_label(phrase)
        if is_blocked_label(label):
            continue
        # favor phrase-level labels over single words
        score = base_weight + 0.9
        if label not in out:
            out[label] = {"score": 0.0, "source_types": set()}
        out[label]["score"] += score
        out[label]["source_types"].add(source_type)

    return out


def choose_core_concept_fallback(title: str) -> str:
    tokens = extract_tokens(title)
    valid = [t for t in tokens if t not in BLOCKED_SINGLE_WORDS and len(t) >= 3]
    if not valid:
        return "core_topic"
    if len(valid) == 1:
        label = normalize_label(valid[0])
        return label or "core_topic"
    label = normalize_label(f"{valid[0]}_{valid[1]}")
    return label or normalize_label(valid[0]) or "core_topic"


def short_snippet(text: str, limit: int = 140) -> str:
    cleaned = re.sub(r"\s+", " ", text.strip())
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[: limit - 3].rstrip() + "..."


def build_source_maps(
    part1_data: list[dict[str, Any]], part2_data: list[dict[str, Any]]
) -> dict[tuple[int, str], dict[str, Any]]:
    out: dict[tuple[int, str], dict[str, Any]] = {}

    for t in part1_data:
        title = str(t.get("topic_en", "")).strip()
        key = (1, normalize_topic_key(title))
        qtexts = []
        for q in t.get("questions", []) or []:
            qt = str(q.get("text", "")).strip()
            if qt:
                qtexts.append(qt)
        out[key] = {"title": title, "question_texts": qtexts}

    for t in part2_data:
        title = str(t.get("topic", "")).strip()
        key = (2, normalize_topic_key(title))
        qtexts = []

        cue_card = t.get("cue_card", {}) or {}
        prompt = str(cue_card.get("prompt", "")).strip()
        if prompt:
            qtexts.append(prompt)
        for bullet in cue_card.get("you_should_say", []) or []:
            bt = str(bullet).strip()
            if bt:
                qtexts.append(bt)

        for q in t.get("part3", []) or []:
            qt = str(q.get("text", "")).strip()
            if qt:
                qtexts.append(qt)

        out[key] = {"title": title, "question_texts": qtexts}

    return out


def confidence_from_support(support_count: int, source_types: set[str], notes: list[str]) -> str:
    if support_count >= 4 and ("question_text_extraction" in source_types or "existing_l3_reuse" in source_types):
        return "high"
    if support_count >= 2 and len(source_types) >= 1:
        return "medium"
    if "heuristic_fallback" in source_types and support_count <= 1:
        return "low"
    if notes:
        return "low"
    return "medium"


def main() -> None:
    p1_view = load_json(P1_VIEW_PATH)
    p2_view = load_json(P2_VIEW_PATH)
    cfg = load_yaml(CFG_PATH)
    p1_src = load_json(P1_SRC_PATH)
    p2_src = load_json(P2_SRC_PATH)

    source_map = build_source_maps(p1_src, p2_src)
    l2_to_l3_cfg = cfg.get("l2_to_l3", {}) or {}

    all_rows: list[tuple[int, dict[str, Any]]] = []
    all_rows.extend((1, row) for row in p1_view)
    all_rows.extend((2, row) for row in p2_view)

    bucket_topic_counts: Counter[tuple[str, str]] = Counter()
    bucket_missing_counts: Counter[tuple[str, str]] = Counter()
    bucket_token_counters: dict[tuple[str, str], Counter[str]] = defaultdict(Counter)

    # First pass for coarse token frequency by bucket (for lightweight weighting).
    for part, row in all_rows:
        tx = row.get("taxonomy_v2", {}) or {}
        primary = tx.get("primary", {}) or {}
        l1 = primary.get("l1")
        l2 = primary.get("l2")
        if not l1 or not l2:
            continue
        bucket = (str(l1), str(l2))
        bucket_topic_counts[bucket] += 1
        if primary.get("l3") is None:
            bucket_missing_counts[bucket] += 1

        topic_title = str(row.get("topic", "")).strip()
        src = source_map.get((part, normalize_topic_key(topic_title)), {"title": topic_title, "question_texts": []})
        texts = [src.get("title", "")] + list(src.get("question_texts", []))
        for text in texts:
            for token in extract_tokens(text):
                if token in BLOCKED_SINGLE_WORDS or len(token) < 3:
                    continue
                bucket_token_counters[bucket][token] += 1

    agg: dict[str, dict[str, dict[str, Any]]] = defaultdict(lambda: defaultdict(dict))
    topics_with_null_primary_l3 = 0

    for part, row in all_rows:
        tx = row.get("taxonomy_v2", {}) or {}
        primary = tx.get("primary", {}) or {}
        l1 = primary.get("l1")
        l2 = primary.get("l2")
        primary_l3 = primary.get("l3")
        if not l1 or not l2:
            continue

        topic_title = str(row.get("topic", "")).strip()
        src = source_map.get((part, normalize_topic_key(topic_title)), {"title": topic_title, "question_texts": []})
        title_text = src.get("title", topic_title) or topic_title
        question_texts = list(src.get("question_texts", []))

        bucket = (str(l1), str(l2))
        token_counter = bucket_token_counters[bucket]

        per_topic_candidates: dict[str, dict[str, Any]] = {}
        topic_snippets: list[str] = [short_snippet(t) for t in question_texts if t.strip()]

        # Existing known primary l3 can be reused as high-signal candidate seeds.
        if isinstance(primary_l3, str) and primary_l3.strip():
            label = normalize_label(primary_l3)
            if not is_blocked_label(label):
                per_topic_candidates[label] = {
                    "score": 2.4,
                    "source_types": {"existing_l3_reuse"},
                }

        # For missing primary l3 topics, run bottom-up text extraction.
        if primary_l3 is None:
            topics_with_null_primary_l3 += 1

            title_candidates = extract_candidates_from_text(
                title_text,
                base_weight=2.1,
                source_type="topic_title_extraction",
                bucket_counter=token_counter,
            )
            for label, payload in title_candidates.items():
                if label not in per_topic_candidates:
                    per_topic_candidates[label] = {"score": 0.0, "source_types": set()}
                per_topic_candidates[label]["score"] += payload["score"]
                per_topic_candidates[label]["source_types"] |= payload["source_types"]

            for q in question_texts:
                q_candidates = extract_candidates_from_text(
                    q,
                    base_weight=1.2,
                    source_type="question_text_extraction",
                    bucket_counter=token_counter,
                )
                for label, payload in q_candidates.items():
                    if label not in per_topic_candidates:
                        per_topic_candidates[label] = {"score": 0.0, "source_types": set()}
                    per_topic_candidates[label]["score"] += payload["score"]
                    per_topic_candidates[label]["source_types"] |= payload["source_types"]

            # Lightweight reuse hints from current configured l2->l3 vocabulary.
            for seed in l2_to_l3_cfg.get(str(l2), []) or []:
                label = normalize_label(str(seed))
                if is_blocked_label(label):
                    continue
                if label not in per_topic_candidates:
                    per_topic_candidates[label] = {"score": 0.0, "source_types": set()}
                per_topic_candidates[label]["score"] += 0.9
                per_topic_candidates[label]["source_types"].add("existing_l3_reuse")

            # If extraction is weak/noisy, inject one core concept fallback.
            sorted_now = sorted(per_topic_candidates.items(), key=lambda kv: (-kv[1]["score"], kv[0]))
            clean_now = [k for k, _ in sorted_now if not is_blocked_label(k)]
            if len(clean_now) < 3:
                fallback = choose_core_concept_fallback(title_text)
                if not is_blocked_label(fallback):
                    if fallback not in per_topic_candidates:
                        per_topic_candidates[fallback] = {"score": 0.0, "source_types": set()}
                    per_topic_candidates[fallback]["score"] += 1.1
                    per_topic_candidates[fallback]["source_types"].add("heuristic_fallback")

        # Keep 3..8 candidates for missing topics; for non-missing we keep compact seed support.
        ranked = sorted(per_topic_candidates.items(), key=lambda kv: (-kv[1]["score"], kv[0]))
        if primary_l3 is None:
            ranked = ranked[:8]
            if len(ranked) < 3:
                fallback = choose_core_concept_fallback(title_text)
                if not is_blocked_label(fallback):
                    ranked.append((fallback, {"score": 1.0, "source_types": {"heuristic_fallback"}}))
        else:
            ranked = ranked[:3]

        for label, payload in ranked:
            if is_blocked_label(label):
                continue
            bucket_node = agg[str(l1)][str(l2)]
            if label not in bucket_node:
                bucket_node[label] = {
                    "label": label,
                    "source_types": set(),
                    "support_topics_set": set(),
                    "example_topics": [],
                    "example_question_snippets": [],
                    "notes": [],
                    "warnings": [],
                }
            entry = bucket_node[label]
            entry["source_types"] |= set(payload.get("source_types", set()))
            entry["support_topics_set"].add(topic_title)
            if len(entry["example_topics"]) < 8 and topic_title not in entry["example_topics"]:
                entry["example_topics"].append(topic_title)
            for snip in topic_snippets:
                if len(entry["example_question_snippets"]) >= 5:
                    break
                if snip and snip not in entry["example_question_snippets"]:
                    entry["example_question_snippets"].append(snip)

    # Build serializable structure.
    by_l1: dict[str, Any] = {}
    total_unique_candidates = 0
    l2_bucket_count = 0

    for l1 in sorted(agg.keys()):
        by_l2_payload: dict[str, Any] = {}
        for l2 in sorted(agg[l1].keys()):
            l2_bucket_count += 1
            bucket = (l1, l2)
            total_topics_bucket = bucket_topic_counts.get(bucket, 0)
            missing_topics_bucket = bucket_missing_counts.get(bucket, 0)

            entries = []
            for label, raw_entry in agg[l1][l2].items():
                support_count = len(raw_entry["support_topics_set"])
                source_types = sorted(raw_entry["source_types"])
                notes: list[str] = []
                warnings: list[str] = []
                if "heuristic_fallback" in raw_entry["source_types"]:
                    notes.append("contains_fallback_signal")
                if support_count <= 1:
                    warnings.append("low_support")

                confidence = confidence_from_support(support_count, raw_entry["source_types"], warnings)
                entries.append(
                    {
                        "label": label,
                        "source_types": source_types,
                        "support_topic_count": support_count,
                        "example_topics": raw_entry["example_topics"][:8],
                        "example_question_snippets": raw_entry["example_question_snippets"][:5],
                        "confidence": confidence,
                        "notes": notes,
                        "warnings": warnings,
                    }
                )

            entries.sort(
                key=lambda e: (
                    {"high": 0, "medium": 1, "low": 2}.get(e["confidence"], 3),
                    -e["support_topic_count"],
                    e["label"],
                )
            )
            total_unique_candidates += len(entries)

            by_l2_payload[l2] = {
                "coverage": {
                    "topics_in_bucket": total_topics_bucket,
                    "topics_with_primary_l3_missing": missing_topics_bucket,
                    "current_non_null_primary_l3_topics": max(0, total_topics_bucket - missing_topics_bucket),
                    "current_primary_l3_coverage_rate": round(
                        (max(0, total_topics_bucket - missing_topics_bucket) / total_topics_bucket), 4
                    )
                    if total_topics_bucket
                    else 0.0,
                },
                "candidate_l3": entries,
            }

        by_l1[l1] = {"by_l2": by_l2_payload}

    missing_top_l2 = sorted(
        (
            {
                "l1": l1,
                "l2": l2,
                "missing_primary_l3_topics": miss,
                "topics_in_bucket": bucket_topic_counts.get((l1, l2), 0),
            }
            for (l1, l2), miss in bucket_missing_counts.items()
        ),
        key=lambda x: (-x["missing_primary_l3_topics"], x["l1"], x["l2"]),
    )

    total_topics = len(all_rows)
    summary_stats = {
        "total_topics": total_topics,
        "topics_with_primary_l3_null": topics_with_null_primary_l3,
        "l2_bucket_count": l2_bucket_count,
        "total_unique_candidate_l3": total_unique_candidates,
    }

    payload = {
        "metadata": {
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "script": "pipeline/generate_l3_candidates_v2.py",
            "purpose": "bottom_up_l3_candidate_generation_for_human_review",
            "focus": "prioritize_topics_with_primary_l3_null",
        },
        "inputs": {
            "taxonomy_views": [
                str(P1_VIEW_PATH.relative_to(ROOT)),
                str(P2_VIEW_PATH.relative_to(ROOT)),
            ],
            "taxonomy_config": str(CFG_PATH.relative_to(ROOT)),
            "source_data": [
                str(P1_SRC_PATH.relative_to(ROOT)),
                str(P2_SRC_PATH.relative_to(ROOT)),
            ],
        },
        "summary_stats": summary_stats,
        "missing_primary_l3_by_l2": missing_top_l2,
        "by_l1": by_l1,
    }

    write_json(OUT_BANK_PATH, payload)

    review_lines: list[str] = []
    review_lines.append("# L3 Candidate Review v2")
    review_lines.append("")
    review_lines.append("This is a human-in-the-loop candidate layer. No taxonomy config was auto-overwritten.")
    review_lines.append("")
    review_lines.append("## Global Summary")
    review_lines.append(f"- total_topics: {summary_stats['total_topics']}")
    review_lines.append(f"- topics_with_primary_l3_null: {summary_stats['topics_with_primary_l3_null']}")
    review_lines.append(f"- l2_bucket_count: {summary_stats['l2_bucket_count']}")
    review_lines.append(f"- total_unique_candidate_l3: {summary_stats['total_unique_candidate_l3']}")
    review_lines.append("")
    review_lines.append("## Highest Missing Buckets")
    for row in missing_top_l2[:10]:
        review_lines.append(
            f"- {row['l1']} > {row['l2']}: missing {row['missing_primary_l3_topics']} / {row['topics_in_bucket']}"
        )
    review_lines.append("")

    for l1 in sorted(by_l1.keys()):
        review_lines.append(f"## {l1}")
        review_lines.append("")
        by_l2 = by_l1[l1]["by_l2"]
        for l2 in sorted(by_l2.keys()):
            node = by_l2[l2]
            cov = node["coverage"]
            candidates = node["candidate_l3"]
            review_lines.append(f"### {l1} > {l2}")
            review_lines.append(
                f"- current coverage: {cov['current_non_null_primary_l3_topics']} / {cov['topics_in_bucket']} "
                f"({cov['current_primary_l3_coverage_rate']:.2%})"
            )
            review_lines.append(f"- topics missing primary.l3: {cov['topics_with_primary_l3_missing']}")
            review_lines.append(f"- candidate pool size: {len(candidates)}")
            review_lines.append("")
            review_lines.append("Top proposed candidate l3 labels:")
            for entry in candidates[:12]:
                review_lines.append(
                    f"- `{entry['label']}` | support={entry['support_topic_count']} | confidence={entry['confidence']}"
                )
            review_lines.append("")
            review_lines.append("Representative examples:")
            for entry in candidates[:6]:
                topic_examples = ", ".join(entry["example_topics"][:3]) if entry["example_topics"] else "-"
                snippet_examples = " | ".join(entry["example_question_snippets"][:2]) if entry["example_question_snippets"] else "-"
                review_lines.append(f"- `{entry['label']}`")
                review_lines.append(f"  - topics: {topic_examples}")
                review_lines.append(f"  - question snippets: {snippet_examples}")
            review_lines.append("")

            shortlist = [
                e["label"]
                for e in candidates
                if e["confidence"] in {"high", "medium"} and e["support_topic_count"] >= 1
            ][:12]
            if len(shortlist) < 5:
                shortlist = [e["label"] for e in candidates[:12]]
            review_lines.append("Recommended shortlist:")
            for label in shortlist[:12]:
                review_lines.append(f"- `{label}`")
            review_lines.append("")

    write_text(OUT_REVIEW_PATH, "\n".join(review_lines).strip() + "\n")

    print(f"topics processed: {summary_stats['total_topics']}")
    print(f"primary.l3 null count: {summary_stats['topics_with_primary_l3_null']}")
    print(f"l2 buckets: {summary_stats['l2_bucket_count']}")
    print(f"unique candidate l3: {summary_stats['total_unique_candidate_l3']}")
    print(f"Wrote candidate bank to: {OUT_BANK_PATH}")
    print(f"Wrote review markdown to: {OUT_REVIEW_PATH}")


if __name__ == "__main__":
    main()

