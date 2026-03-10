#!/usr/bin/env python3
"""
json_to_txt.py
Converts merged_part1.json or merged_part2.json to a human-editable .txt mirror.

Usage:
  python3 pipeline/json_to_txt.py merged_part2.json
  python3 pipeline/json_to_txt.py merged_part1.json

Output: same directory as input, with .txt extension.

Part 1 format:
  == Daily routine ==
  SEASON: 2026-Jan-Apr
  [tongzhuo] 1. What is your daily study routine?
  [laokaoya] Do you prefer morning or evening routines?
  (blank line between topics)

Part 2 format:
  == Describe a person who likes to look after the natural world ==
  SEASON: 2026-Jan-Apr
  TAGS: people | nature | conservation
  - Who this person is
  - What he or she does
  PART3:
  [tongzhuo][evaluate] 1. Do you think parents should teach their children?
  [laokaoya][analyze] Why are some people more willing to protect wild animals?
  (blank line between topics)
"""

import json
import os
import sys


def topic_to_txt_part1(item):
    lines = []
    lines.append(f"== {item['topic_en']} ==")
    if item.get("season"):
        lines.append(f"SEASON: {item['season']}")
    for q in item.get("questions", []):
        src = q.get("source", "unknown")
        lines.append(f"[{src}] {q['text']}")
    return "\n".join(lines)


def topic_to_txt_part2(item):
    lines = []
    cc = item.get("cue_card", {})
    prompt = cc.get("prompt", item.get("topic", ""))
    lines.append(f"== {prompt} ==")
    if item.get("season"):
        lines.append(f"SEASON: {item['season']}")

    # content_tags — flat array
    ct = item.get("content_tags", [])
    if isinstance(ct, list) and ct:
        lines.append("TAGS: " + " | ".join(ct))
    elif isinstance(ct, dict):
        # legacy structured format
        parts = [v for v in ct.values() if v and v != "null"]
        if parts:
            lines.append("TAGS: " + " | ".join(parts))

    # you_should_say bullets
    for bullet in cc.get("you_should_say", []):
        lines.append(f"- {bullet}")

    # part3
    part3 = item.get("part3", [])
    if part3:
        lines.append("PART3:")
        for q in part3:
            src = q.get("source", "unknown")
            type_tags = q.get("type_tags", [])
            tag_str = "[" + ",".join(type_tags) + "]" if type_tags else ""
            lines.append(f"[{src}]{tag_str} {q['text']}")

    return "\n".join(lines)


def convert(json_path):
    with open(json_path, encoding="utf-8") as f:
        data = json.load(f)

    if not data:
        print("Empty file.")
        return

    # Detect part from first item
    first = data[0]
    part = first.get("part")
    if part is None:
        part = 1 if "topic_en" in first else 2

    blocks = []
    for item in data:
        if part == 1:
            blocks.append(topic_to_txt_part1(item))
        else:
            blocks.append(topic_to_txt_part2(item))

    txt_path = os.path.splitext(json_path)[0] + ".txt"
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write("\n\n".join(blocks) + "\n")

    print(f"Written {len(blocks)} topics → {txt_path}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 pipeline/json_to_txt.py <path/to/file.json>")
        sys.exit(1)
    convert(sys.argv[1])
