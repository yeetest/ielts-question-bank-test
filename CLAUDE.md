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
├── merged_part1.txt         (gitignored — regenerate with json_to_txt.py)
├── merged_part2.txt         (gitignored — regenerate with json_to_txt.py)
├── tags/
│   └── tags.txt             (ground truth tag vocabulary, tracked by git)
├── docs/
│   └── CLAUDE_tagging.md    (full tagging rules)
└── pipeline/                (local dev only — gitignored)
    ├── dedup_questions.py       (one-time dedup for existing JSONs only)
    ├── renumber_questions.py    (renumbers questions sequentially within each topic)
    ├── json_to_txt.py           (JSON → human-editable .txt)
    ├── txt_to_json.py           (.txt → JSON sync)
    ├── tag_question_types.py    (auto-tags Part 3 questions with type_tags via keyword matching)
    ├── tag_content_topics.py    (auto-tags Part 2 topics with content_tags via fuzzy lookup + Claude batch)
    └── ingest_pipeline.py       (future: ingest new source files)
```

**Note:** `pipeline/` and all `.txt` files (except `tags/tags.txt`) are gitignored. Only JSON, HTML, `tags/tags.txt`, `docs/`, and `CLAUDE.md` are committed to GitHub.

## Human-in-the-Loop Edit Pattern

The `.txt` files are human-editable mirrors of the JSON files. Kathy edits `.txt`; scripts sync to/from JSON.

**Rules for Claude Code:**
- After any edit to `merged_part1.json` or `merged_part2.json`, immediately regenerate the matching `.txt`:
```bash
python3 pipeline/json_to_txt.py merged_part1.json
python3 pipeline/json_to_txt.py merged_part2.json
```
- When Kathy says she has edited a `.txt` file, run `txt_to_json.py` to sync back to JSON before doing anything else:
```bash
python3 pipeline/txt_to_json.py merged_part1.txt
python3 pipeline/txt_to_json.py merged_part2.txt
```

**TXT format for Part 1:**
```
== Daily routine ==
SEASON: 2026-Jan-Apr
[tongzhuo] 1. What is your daily study routine?
[tongzhuo] 2. Have you ever changed your routine?

== Life stages ==
SEASON: 2026-Jan-Apr
[tongzhuo] 1. What did you often do with your friends in your childhood?
```

**TXT format for Part 2:**
```
== Describe a person who likes to look after the natural world ==
SEASON: 2026-Jan-Apr
TAGS: people | nature | conservation
- Who this person is
- What he or she does
PART3:
[tongzhuo][evaluate] 1. Do you think parents should teach their children how to protect the environment?
[laokaoya][analyze] 2. Why are some people more willing to protect wild animals than others?
```

## JSON Schemas

### Part 1 topic (`merged_part1.json`)
```json
{
  "topic_en": "Daily routine",
  "part": 1,
  "season": "2026-Jan-Apr",
  "questions": [
    { "text": "1. Question text", "source": "tongzhuo" }
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
    { "text": "1. Question text", "source": "tongzhuo", "type_tags": ["evaluate"] }
  ],
  "tags": [],
  "content_tags": ["people", "nature", "conservation"]
}
```

## Tagging

Full tagging rules are in `docs/CLAUDE_tagging.md`. Summary:

### Topic-level (`content_tags`) — Part 2 only
Flat array. Position 0 is the **category**; positions 1–3 are **thematic tags** from `tags/tags.txt`.

**Categories:** `people` | `place` | `object` | `experience/activity`

**Thematic tags:** check `tags/tags.txt` before creating a new tag. Normalise synonyms (film/movie → `movies`, job/career → `work`, journey/trip → `travel`). Append new tags to `tags/tags.txt` with a description.

**Example:** `"content_tags": ["experience/activity", "music", "likes_dislikes"]`

### Question-level (`type_tags`) — Part 3 only
Per-question array. Values: `describe` | `analyze` | `evaluate` | `predict` | `unclear`

## Data Sources
- **同桌英语** → `source: "tongzhuo"`
- **老烤鸭** → `source: "laokaoya"`

## Pipeline Scripts

### dedup_questions.py
Removes near-duplicate questions within each topic using fuzzy matching. **For existing JSONs only** — future ingest dedup is a separate script not yet built.
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

### tag_question_types.py
Auto-tags Part 3 questions with `type_tags` using keyword matching (describe / analyze / evaluate / predict / unclear). Full rules in `docs/CLAUDE_tagging.md`.
```bash
python3 pipeline/tag_question_types.py merged_part2.json
```

### tag_content_topics.py
Auto-tags Part 2 topics with `content_tags` using fuzzy lookup against `tags/tags.txt` + Claude batch prompting.
```bash
python3 pipeline/tag_content_topics.py merged_part2.json
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
- `content_tags` is a flat array — NOT an object (old `{category, substance, frame_angle}` format is obsolete)
- After any JSON edit, always regenerate the matching `.txt` mirror
