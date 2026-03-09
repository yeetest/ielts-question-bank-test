# IELTS Question Bank — Claude Code Instructions

## Project Overview
Personal IELTS Speaking question bank tool for Kathy (IELTS teacher).
- JSON = source of truth. `index.html` fetches data at runtime via `fetch()`.
- Deployed: GitHub main branch → Vercel auto-deploy.
- **No Claude API calls.** Use Claude Code intelligence + lightweight local tools only.
- Git push uses proxy: `http://127.0.0.1:7897`

## Folder Structure
```
/
├── CLAUDE.md               This file
├── .gitignore              Excludes /pipeline/, *.txt (except tags/tags.txt)
├── index.html              Internal viewer (fetches JSON at runtime)
├── merged_part1.json       Part 1 question bank
├── merged_part2.json       Part 2+3 question bank (with content_tags)
├── docs/
│   └── CLAUDE_tagging.md  Full tagging rules and pipeline documentation
├── tags/
│   └── tags.txt            Master tag vocabulary (tracked by git)
└── pipeline/               Local-only dev tools — gitignored
    ├── json_to_txt.py      JSON → human-editable .txt mirror
    ├── txt_to_json.py      Edited .txt → back to JSON
    ├── auto_tag_questions.py  Tags Part 3 questions (type_tags) via spaCy+keywords
    ├── auto_tag_topics.py  Tags Part 2 topics (content_tags) via spaCy
    ├── ingest_pipeline.py  Full ingest pipeline for new question banks
    ├── merged_part1.txt    Human-editable mirror of merged_part1.json
    ├── merged_part2.txt    Human-editable mirror of merged_part2.json
    ├── initial_extraction_for_merged_part2.txt  Step 1 raw tag extractions
    └── normalized_tags_for_merged_part2.txt     Step 3 normalised tags
```

**Note:** `pipeline/` and all `.txt` files are gitignored (local dev only). Only JSON, HTML, `tags/tags.txt`, `docs/`, and `CLAUDE.md` are committed to GitHub.

## Human-in-the-Loop Edit Pattern

The `.txt` files are human-editable mirrors of the JSON files. Kathy edits `.txt`; scripts sync to/from JSON.

**Rule for Claude Code:**
- Whenever you create or modify `merged_part1.json` or `merged_part2.json`, immediately run `json_to_txt.py` to regenerate the matching `.txt`.
- When Kathy says she has edited a `.txt` file, run `txt_to_json.py` to sync changes back to JSON before doing anything else.

**Scripts** (both live in `pipeline/`):
```bash
# JSON → TXT (run after any JSON change)
python3 pipeline/json_to_txt.py --part 1   # regenerates merged_part1.txt
python3 pipeline/json_to_txt.py --part 2   # regenerates merged_part2.txt

# TXT → JSON (run when Kathy edits a .txt)
python3 pipeline/txt_to_json.py --part 1   # syncs merged_part1.txt → merged_part1.json
python3 pipeline/txt_to_json.py --part 2   # syncs merged_part2.txt → merged_part2.json
```

**TXT format for Part 1:**
```
== Daily routine ==
[tongzhuo] 1. What is your daily study routine?
[tongzhuo] 2. Have you ever changed your routine?

== Life stages ==
[tongzhuo] 1. What did you often do with your friends in your childhood?
```

**TXT format for Part 2:**
```
== Describe a person who likes to look after the natural world ==
TAGS: people | environment | conservation
- Who this person is
- What he or she does
PART3:
[tongzhuo][evaluate] 1. Do you think parents should teach their children how to protect the environment?
[laokaoya][analyze] Why are some people more willing to protect wild animals than others?
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

## Tagging Taxonomy

### Topic-level (`content_tags`) — Part 2 only
Flat array. Position 0 is always the **category**; positions 1–3 are **thematic tags**.

**category** (position 0): `people` | `place` | `object` | `experience/activity`
- `people` — topic is about a person or group of people
- `place` — topic is about a location (building, park, mountain, room, etc.)
- `object` — tangible or intangible thing (book, film, technology, heirloom, animal, etc.)
- `experience/activity` — something that happened, a plan, habit, event, travel, routine, etc.

**thematic tags** (positions 1–3): most semantically meaningful words from the topic.
- Always check `tags/tags.txt` before creating a new tag.
- Normalise synonyms: film/movie → `movies`; job/career/occupation → `work`; journey/trip/vacation → `travel`.
- Key recurring tags: `aspiration`, `admiration`, `likes_dislikes`, `first_time`, `helping_others`, `interesting`, `sentimental`, `travel`, `work`, `nature`.

**Example:** `"content_tags": ["people", "nature", "conservation"]`

### Question-level (`type_tags`) — Part 3 only
- List from: `describe`, `analyze`, `evaluate`, `predict`, `unclear`

## Data Sources
- **同桌英语** → `source: "tongzhuo"`
- **老烤鸭** → `source: "laokaoya"`

## Ingest Pipeline (for new question banks)
Correct order — run `pipeline/ingest_pipeline.py`:
1. Parse raw file (JSON or TXT)
2. Clean (strip Chinese chars, fix spacing, strip numbering)
3. Format to exact schema above
4. Tag topics (`content_tags`) — Part 2 only
5. Tag questions (`type_tags`) — Part 3 only
6. Write `temp_review.txt` for human inspection
7. On approval → `--merge` flag, then commit & push

```bash
python3 pipeline/ingest_pipeline.py <input_file> --part 2 --source tongzhuo [--season "2026-Jan-Apr"] [--merge]
```

## Git / Push
Proxy must be set for push:
```bash
export https_proxy=http://127.0.0.1:7897
git push
```
Or set in git config:
```bash
git config http.proxy http://127.0.0.1:7897
```

## Conventions
- Always preserve `season` field as-is (e.g. `"2026-Jan-Apr"`)
- Strip all Chinese characters and zero-width chars from English fields
- Never embed data in `index.html` — always `fetch()` from JSON files
- When adding new thematic tags, append them to `tags/tags.txt` with a description
- `content_tags` is a flat array — NOT a `{category, substance, frame_angle}` object (that was the old format)
- After any JSON edit, always regenerate the matching `.txt` mirror (see Human-in-the-Loop section above)
