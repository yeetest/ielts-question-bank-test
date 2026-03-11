# IELTS Question Bank — Claude Code Instructions

## Project Overview
Personal IELTS Speaking question bank tool for Kathy (IELTS teacher).
- JSON = source of truth. `index.html` fetches data at runtime via `fetch()`.
- Deployed: GitHub main branch → Vercel auto-deploy.
- **No Claude API calls.** Use Claude Code intelligence only.
- Git push uses proxy: `http://127.0.0.1:7897`

## Folder Structure
```
ielts-question-bank-test/
├── CLAUDE.md
├── .gitignore
├── index.html
├── merged_part1.json
├── merged_part2.json
├── tags/
│   └── tags.txt             (ground truth tag vocabulary, tracked by git)
├── docs/
│   └── CLAUDE_tagging.md    (full tagging rules)
├── human-in-the-loop/       (local only — gitignored)
│   ├── json_to_txt.py       (JSON → human-editable .txt)
│   ├── txt_to_json.py       (.txt → JSON sync)
│   ├── merged_part1.txt     (generated mirror of part1 JSON)
│   ├── merged_part2.txt     (generated mirror of part2 JSON)
│   └── *.txt                (other generated txt reports)
└── pipeline/                (local dev only — gitignored)
    ├── dedup_questions.py       (one-time dedup for existing JSONs only)
    ├── renumber_questions.py    (renumbers questions sequentially within each topic)
    ├── tag_question_types.py    (auto-tags questions with skill_tags via keyword matching)
    ├── tag_content_v2.py        (auto-tags topics with content_tags v2 via keyword matching)
    ├── tag_content_topics.py    (auto-tags topics with content_tags via fuzzy lookup + Claude batch)
    ├── tag_time_frames.py       (auto-tags questions with time_frame via keyword matching)
    └── ingest_pipeline.py       (future: ingest new source files)
```

**Note:** `pipeline/`, `human-in-the-loop/`, and all `.txt` files (except `tags/tags.txt`) are gitignored. Only JSON, HTML, CSS, JS, `tags/tags.txt`, `docs/`, and `CLAUDE.md` are committed to GitHub.

## Human-in-the-Loop Edit Pattern

The `.txt` files in `human-in-the-loop/` are human-editable mirrors of the JSON files. Kathy edits `.txt`; scripts sync to/from JSON.

**Rules for Claude Code:**
- After any edit to `merged_part1.json` or `merged_part2.json`, immediately regenerate the matching `.txt`:
```bash
python3 human-in-the-loop/json_to_txt.py merged_part1.json
python3 human-in-the-loop/json_to_txt.py merged_part2.json
```
- When Kathy says she has edited a `.txt` file, run `txt_to_json.py` to sync back to JSON before doing anything else:
```bash
python3 human-in-the-loop/txt_to_json.py human-in-the-loop/merged_part1.txt
python3 human-in-the-loop/txt_to_json.py human-in-the-loop/merged_part2.txt
```

**TXT format for Part 1:**
```
== Daily routine ==
SEASON: 2026-Jan-Apr
TAGS: experience/activity | routines
[tongzhuo] 1. What is your daily study routine? [description] {present}
[tongzhuo] 2. Have you ever changed your routine? [experience, comparison] {past}
[tongzhuo] 3. Do you think it is important to have a daily routine? [evaluation] {present}
```

**TXT format for Part 2:**
```
== Describe a person who likes to look after the natural world ==
SEASON: 2026-Jan-Apr
TAGS: abstract_concepts | close_bonds, professions, values | environment, policy
- Who this person is
- What he or she does
PART3:
[tongzhuo][description,evaluation]{present} 1. Do you think parents should teach their children how to protect the environment?
[laokaoya][analyze]{present} 2. Why are some people more willing to protect wild animals than others?
```

## JSON Schemas

### Part 1 topic (`merged_part1.json`)
```json
{
  "topic_en": "Daily routine",
  "part": 1,
  "season": "2026-Jan-Apr",
  "content_tags": {
    "l1": "experience/activity",
    "l2": ["routines"],
    "l3": []
  },
  "qualifier_tags": [],
  "questions": [
    { "text": "1. Question text", "source": "tongzhuo", "skill_tags": ["description"], "time_frame": "present" }
  ],
  "tags": []
}
```

### Part 2 topic (`merged_part2.json`)
```json
{
  "topic": "a person who likes to look after the natural world",
  "part": 2,
  "season": "2026-Jan-Apr",
  "cue_card": {
    "prompt": "Describe a person who likes to look after the natural world",
    "you_should_say": ["Who this person is", "What he or she does"]
  },
  "part3": [
    { "text": "1. Question text", "source": "tongzhuo", "skill_tags": ["evaluation"], "time_frame": "present" }
  ],
  "tags": [],
  "content_tags": {
    "l1": "abstract_concepts",
    "l2": ["close_bonds", "professions", "values"],
    "l3": ["environment", "policy"]
  },
  "qualifier_tags": []
}
```

## Tagging

Full tagging rules are in `docs/CLAUDE_tagging.md`. Summary:

### Topic-level (`content_tags`) — v2 3-Layer System

Structured object with 3 layers. 5 L1 → 15 L2 → 30 L3.

```json
"content_tags": {"l1": "experience/activity", "l2": ["leisure"], "l3": ["exercise"]}
"qualifier_tags": ["memorable"]
```

**Layer 1 (l1):** Single primary category — `people` | `place` | `object` | `experience/activity` | `abstract_concepts`
**Layer 2 (l2):** Thematic clusters:
- people: `professions`, `close_bonds`, `general`
- place: `outdoor`, `indoor`
- object: `tangible`, `intangible`
- experience/activity: `work`, `study`, `leisure`, `routines`
- abstract_concepts: `communication`, `emotion`, `personal_traits`, `values`, `personal_growth`, `influence`, `time`

**Layer 3 (l3):** Specific tags under L2 (e.g. `artwork`, `technology`, `exercise`, `shopping`, `pride`, `creativity`, `policy`, `learning`)
**Qualifiers:** Stored separately in `qualifier_tags`

Full v2 hierarchy in `human-in-the-loop/content_tags_v2_draft.md`.

### Question-level (`skill_tags`) — unified 8-type taxonomy (Part 1 and Part 2+3)
Per-question array. 1–3 tags per question:
`experience` | `frequency` | `description` | `preference` | `evaluation` | `analyze` | `comparison` | `hypothetical`

Priority order (for auto-tagging): experience → frequency → description → preference → evaluation → analyze → comparison → hypothetical

### Question-level (`time_frame`) — 3-value system (Part 1 and Part 2+3)
Per-question single value: `"past"` | `"present"` | `"future"`
- **past:** past simple, present perfect experience ("have you ever"), past-referring phrases
- **present:** current state/habit, preference, opinion, general analysis (default)
- **future:** future tense, plans, hypothetical/subjunctive, desires

Full rules and keyword lists in `docs/CLAUDE_tagging.md`.

## Data Sources
- **同桌英语** → `source: "tongzhuo"`
- **老烤鸭** → `source: "laokaoya"`

## Pipeline Scripts

### tag_question_types.py
Auto-tags questions with `skill_tags` via keyword matching. Unified 8-type taxonomy for both parts. Unmatched Part 1 questions saved to `claude_p1_type_response.json` for manual review. Auto-regenerates `.txt` mirror after running.
```bash
python3 pipeline/tag_question_types.py merged_part1.json --part 1
python3 pipeline/tag_question_types.py merged_part2.json
```

### tag_content_v2.py
Auto-tags topics with `content_tags` using v2 taxonomy (5 L1 → 15 L2 → 30 L3) via weighted keyword matching. Topic name gets higher weight than question text.
```bash
python3 pipeline/tag_content_v2.py merged_part1.json --part 1 --dry-run
python3 pipeline/tag_content_v2.py merged_part2.json --dry-run
python3 pipeline/tag_content_v2.py merged_part1.json --part 1 --overwrite   # write
python3 pipeline/tag_content_v2.py merged_part2.json --overwrite            # write
```

### tag_time_frames.py
Auto-tags questions with `time_frame` (past/present/future) via keyword matching. Supports `--dry-run` and `--overwrite`.
```bash
python3 pipeline/tag_time_frames.py merged_part1.json --part 1
python3 pipeline/tag_time_frames.py merged_part2.json
python3 pipeline/tag_time_frames.py merged_part1.json --part 1 --overwrite  # re-tag all
```

### dedup_questions.py
Removes near-duplicate questions within each topic using fuzzy matching.
```bash
python3 dedup_questions.py merged_part1.json
python3 dedup_questions.py merged_part2.json
```

### renumber_questions.py
Renumbers questions sequentially within each topic after edits or dedup.
```bash
python3 pipeline/renumber_questions.py merged_part1.json
python3 pipeline/renumber_questions.py merged_part2.json
```

### ingest_pipeline.py
For ingesting new source files into the question bank (future use).

## Git / Push
Proxy must be set for push:
```bash
export https_proxy=http://127.0.0.1:7897
git push
```

## Conventions
- Never embed data in `index.html` — always `fetch()` from JSON files
- Always preserve `season` field as-is (e.g. `"2026-Jan-Apr"`)
- Strip all Chinese characters and zero-width chars from English fields
- `content_tags` is a 3-layer object `{"l1": str, "l2": [...], "l3": [...]}` — NOT a flat array
- `qualifier_tags` is a separate flat array for tone/quality descriptors
- `skill_tags` (formerly `type_tags`) is a per-question array of 1-3 skill types
- After any JSON edit, always regenerate the matching `.txt` mirror
