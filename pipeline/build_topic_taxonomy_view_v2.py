#!/usr/bin/env python3
"""
build_topic_taxonomy_view_v2.py

Read-only derivation script:
- reads merged_part1.json / merged_part2.json
- derives taxonomy_v2 view (primary + secondary + bindings + diagnostics)
- writes side outputs only, without modifying source JSON

Outputs:
- human-in-the-loop/topic_taxonomy_view_v2_part1.json
- human-in-the-loop/topic_taxonomy_view_v2_part2.json
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError as exc:  # pragma: no cover
    raise SystemExit(
        "PyYAML is required. Install with: pip3 install pyyaml"
    ) from exc


ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "config" / "topic_taxonomy_v2.yaml"
P1_IN = ROOT / "merged_part1.json"
P2_IN = ROOT / "merged_part2.json"
OUT_DIR = ROOT / "human-in-the-loop"
P1_OUT = OUT_DIR / "topic_taxonomy_view_v2_part1.json"
P2_OUT = OUT_DIR / "topic_taxonomy_view_v2_part2.json"


def load_json(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def load_config(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as f:
        return yaml.safe_load(f)


def topic_label(topic: dict[str, Any], part: int) -> str:
    if part == 1:
        return str(topic.get("topic_en", "")).strip()
    return str(topic.get("topic", "")).strip()


def dedupe_keep_order(values: list[str]) -> list[str]:
    seen = set()
    out = []
    for v in values:
        if v in seen:
            continue
        seen.add(v)
        out.append(v)
    return out


def normalize_l1(raw_l1: str, aliases_l1: dict[str, str]) -> tuple[str, bool]:
    if not isinstance(raw_l1, str):
        return "", False
    normalized = aliases_l1.get(raw_l1, raw_l1)
    return normalized, normalized != raw_l1


def infer_topic_view(topic: dict[str, Any], part: int, cfg: dict[str, Any]) -> tuple[dict[str, Any], dict[str, int]]:
    aliases_l1 = cfg.get("aliases", {}).get("l1", {})
    canonical_l1 = set(cfg.get("canonical_l1", []))
    l1_to_l2 = cfg.get("l1_to_l2", {})
    l2_to_l3 = cfg.get("l2_to_l3", {})

    raw_ct = topic.get("content_tags", {})
    raw_l1 = raw_ct.get("l1", "") if isinstance(raw_ct, dict) else ""
    raw_l2 = raw_ct.get("l2", []) if isinstance(raw_ct, dict) else []
    raw_l3 = raw_ct.get("l3", []) if isinstance(raw_ct, dict) else []

    raw_l2 = [str(x).strip() for x in raw_l2 if str(x).strip()]
    raw_l3 = [str(x).strip() for x in raw_l3 if str(x).strip()]
    raw_l2 = dedupe_keep_order(raw_l2)
    raw_l3 = dedupe_keep_order(raw_l3)

    l1_norm, used_alias = normalize_l1(str(raw_l1).strip(), aliases_l1)
    notes: list[str] = []

    if l1_norm not in canonical_l1:
        notes.append(f"l1_not_in_canonical:{l1_norm}")

    l2_priority = l1_to_l2.get(l1_norm, [])
    l2_priority_set = set(l2_priority)

    # primary.l2: first valid l2 by configured priority order
    valid_l2_from_input = [l2 for l2 in raw_l2 if l2 in l2_priority_set]
    primary_l2 = None
    if valid_l2_from_input:
        for candidate in l2_priority:
            if candidate in valid_l2_from_input:
                primary_l2 = candidate
                break
    else:
        if raw_l2:
            notes.append("no_valid_l2_for_l1")

    # primary.l3: first l3 that belongs to chosen primary l2
    primary_l3 = None
    if primary_l2 is not None:
        allowed_for_primary_l2 = set(l2_to_l3.get(primary_l2, []))
        for l3 in raw_l3:
            if l3 in allowed_for_primary_l2:
                primary_l3 = l3
                break
    if primary_l3 is None and raw_l3:
        notes.append("primary_l3_null_after_match")

    secondary_l2 = [x for x in valid_l2_from_input if x != primary_l2]
    secondary_l3 = [x for x in raw_l3 if x != primary_l3]

    bindings: list[dict[str, str]] = []
    ambiguous_l3_parent = False

    if raw_l3:
        if len(valid_l2_from_input) == 1:
            only_l2 = valid_l2_from_input[0]
            for l3 in raw_l3:
                bindings.append({"l2": only_l2, "l3": l3, "source": "inferred"})
        elif len(valid_l2_from_input) > 1:
            for l3 in raw_l3:
                matching_l2 = [l2 for l2 in valid_l2_from_input if l3 in set(l2_to_l3.get(l2, []))]
                if len(matching_l2) == 1:
                    bindings.append({"l2": matching_l2[0], "l3": l3, "source": "inferred"})
                elif len(matching_l2) > 1:
                    if primary_l2 in matching_l2:
                        bindings.append({"l2": primary_l2, "l3": l3, "source": "inferred"})
                        for alt in matching_l2:
                            if alt == primary_l2:
                                continue
                            bindings.append({"l2": alt, "l3": l3, "source": "inferred_secondary"})
                    else:
                        ambiguous_l3_parent = True
                        notes.append(f"ambiguous_l3_no_primary_match:{l3}")
                        # deterministic fallback for temporary view
                        selected = matching_l2[0]
                        bindings.append({"l2": selected, "l3": l3, "source": "inferred_fallback"})
                else:
                    ambiguous_l3_parent = True
                    notes.append(f"no_parent_match_for_l3:{l3}")
        else:
            if raw_l3:
                ambiguous_l3_parent = True
                notes.append("l3_present_without_valid_l2")

    if not primary_l2:
        confidence = "low"
    elif ambiguous_l3_parent:
        confidence = "low"
    elif primary_l3 is None and raw_l3:
        confidence = "medium"
    else:
        confidence = "high"

    record = {
        "topic": topic_label(topic, part),
        "taxonomy_v2": {
            "primary": {
                "l1": l1_norm or None,
                "l2": primary_l2,
                "l3": primary_l3,
            },
            "secondary": {
                "l2": secondary_l2,
                "l3": secondary_l3,
            },
            "bindings": bindings,
            "diagnostics": {
                "ambiguous_l3_parent": ambiguous_l3_parent,
                "used_alias_normalization": used_alias,
                "inference_confidence": confidence,
                "notes": notes,
            },
        },
    }

    stat = {
        "alias_normalized": 1 if used_alias else 0,
        "ambiguous_binding": 1 if ambiguous_l3_parent else 0,
        "primary_l3_null": 1 if (primary_l3 is None) else 0,
    }
    return record, stat


def process_file(path: Path, part: int, cfg: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    data = load_json(path)
    out_rows: list[dict[str, Any]] = []

    alias_count = 0
    ambiguous_count = 0
    primary_l3_null_count = 0
    primary_path_counter: Counter[tuple[str, str, str]] = Counter()

    for topic in data:
        row, stat = infer_topic_view(topic, part, cfg)
        out_rows.append(row)
        alias_count += stat["alias_normalized"]
        ambiguous_count += stat["ambiguous_binding"]
        primary_l3_null_count += stat["primary_l3_null"]

        p = row["taxonomy_v2"]["primary"]
        path_key = (
            p.get("l1") or "null_l1",
            p.get("l2") or "null_l2",
            p.get("l3") or "null_l3",
        )
        primary_path_counter[path_key] += 1

    summary = {
        "topics_processed": len(out_rows),
        "alias_normalized_count": alias_count,
        "ambiguous_bindings_count": ambiguous_count,
        "primary_l3_null_count": primary_l3_null_count,
        "top_primary_paths": primary_path_counter.most_common(10),
    }
    return out_rows, summary


def write_json(path: Path, payload: Any):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def print_summary(label: str, summary: dict[str, Any]):
    print(f"\n[{label}]")
    print(f"topics processed: {summary['topics_processed']}")
    print(f"alias normalized count: {summary['alias_normalized_count']}")
    print(f"ambiguous bindings count: {summary['ambiguous_bindings_count']}")
    print(f"primary.l3 null count: {summary['primary_l3_null_count']}")
    print("most common primary paths top 10:")
    for (l1, l2, l3), cnt in summary["top_primary_paths"]:
        print(f"  - {l1} > {l2} > {l3}: {cnt}")


def main():
    cfg = load_config(CONFIG_PATH)

    part1_rows, part1_summary = process_file(P1_IN, part=1, cfg=cfg)
    part2_rows, part2_summary = process_file(P2_IN, part=2, cfg=cfg)

    write_json(P1_OUT, part1_rows)
    write_json(P2_OUT, part2_rows)

    print(f"Wrote {P1_OUT}")
    print(f"Wrote {P2_OUT}")
    print_summary("Part 1", part1_summary)
    print_summary("Part 2", part2_summary)

    merged = {
        "topics_processed": part1_summary["topics_processed"] + part2_summary["topics_processed"],
        "alias_normalized_count": part1_summary["alias_normalized_count"] + part2_summary["alias_normalized_count"],
        "ambiguous_bindings_count": part1_summary["ambiguous_bindings_count"] + part2_summary["ambiguous_bindings_count"],
        "primary_l3_null_count": part1_summary["primary_l3_null_count"] + part2_summary["primary_l3_null_count"],
    }
    print("\n[Overall]")
    print(f"topics processed: {merged['topics_processed']}")
    print(f"alias normalized count: {merged['alias_normalized_count']}")
    print(f"ambiguous bindings count: {merged['ambiguous_bindings_count']}")
    print(f"primary.l3 null count: {merged['primary_l3_null_count']}")


if __name__ == "__main__":
    main()

