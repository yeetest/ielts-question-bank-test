# IELTS Question Bank — Claude Code Instructions

## Project Overview
Personal IELTS Speaking question bank tool for Kathy (IELTS teacher).
- JSON = source of truth. `index.html` fetches data at runtime via `fetch()` from `data/quarters/<quarter-id>/` (quarter switcher + `?quarter=`). Root `merged_part1.json` / `merged_part2.json` are legacy mirrors; **edit May–Aug only under `data/quarters/2026-05-to-08/`**. **Do not change `data/quarters/2026-01-to-04/`** except intentional freeze corrections.
- Deployed: GitHub main branch → Vercel auto-deploy.
- **No Claude API calls.** Use Claude Code intelligence only.
- Git push uses proxy: `http://127.0.0.1:7897`

## Project memory (delivery protocol)

Non-trivial work must **update project memory in the same delivery** as code. See **`docs/working_rules.md`** for definitions (“memory files”), when to update `CLAUDE.md` / `README_ARCH.md` / `docs/*`, and the required end-of-task summary (files touched, commands, gaps). **Full delivery = implementation + memory sync.**

## Quarter switching (website)

- The **same** frontend (all `js/`, `css/`, sidebar, filters, tags, grid, modal) serves **two** datasets.
- **Quarter IDs:** `2026-01-to-04` | `2026-05-to-08`
- **Load paths:** `data/quarters/<quarter-id>/merged_part1.json`, `merged_part2.json`, `topic_taxonomy_v2_final.json`
- **`2026-01-to-04`:** frozen stable copy — **do not edit** for routine work or May–Aug updates.
- **`2026-05-to-08`:** currently **placeholder** (copy of 1–4 with `season` rewritten). Real May–Aug: replace only these three files in that folder.
- **URL:** `?quarter=2026-01-to-04` or `?quarter=2026-05-to-08`. Missing/invalid param → default **`2026-01-to-04`**. UI dropdown syncs the URL via `history.replaceState`.
- **Local preview:** from repo root, `python3 -m http.server <port>` then open `/` with optional `?quarter=…` (avoid `file://` for `fetch`).
- **Root** `merged_part1.json` / `merged_part2.json` are legacy mirrors; site reads **`data/quarters/…`**.

## Folder Structure
```
ielts-question-bank-test/
├── CLAUDE.md
├── .gitignore
├── index.html
├── merged_part1.json          (legacy; site uses data/quarters/…)
├── merged_part2.json
├── data/
│   ├── topic_taxonomy_v2_final.json   (legacy duplicate; site uses per-quarter copy)
│   └── quarters/
│       ├── 2026-01-to-04/   (frozen)
│       └── 2026-05-to-08/   (active new quarter)
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
    ├── generate_topic_hierarchy_markdown.py (exports topic hierarchy markdown for markmap check)
    ├── audit_taxonomy_structure.py (structural audit: dual-homes, broad L3s, orphan content L3s)
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
[laokaoya][analysis]{present} 2. Why are some people more willing to protect wild animals than others?
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
    { "text": "1. Question text", "source": "tongzhuo", "skill_tags": ["description"], "skill_subtype": "features", "time_frame": "present" }
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
    { "text": "1. Question text", "source": "tongzhuo", "skill_tags": ["evaluation"], "skill_subtype": "importance", "time_frame": "present" }
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
`experience` | `frequency` | `description` | `preference` | `evaluation` | `analysis` | `comparison` | `hypothetical`

Priority order (for auto-tagging): experience → frequency → description → preference → evaluation → analysis → comparison → hypothetical

### Question-level (`skill_subtype`) — second-level skill taxonomy
Per-question single string. Subtype of the primary (first) `skill_tags` value. 24 subtypes total:
- experience: `personal_event` | `memory_recall`
- frequency: `regularity` | `habit`
- description: `listing` | `features` | `context` | `process`
- preference: `like_dislike` | `choice`
- evaluation: `importance` | `recommendation` | `judgment` | `agreement`
- analysis: `cause_reason` | `effect_impact` | `pros_cons` | `mechanism`
- comparison: `difference` | `change_over_time` | `ranking`
- hypothetical: `future_plan` | `conditional` | `prediction`

**Script:** `pipeline/tag_question_types.py --subtype-only` (add subtypes without changing skill_tags). Use `--audit` to generate `human-in-the-loop/skill_subtype_audit.md` for review of low-confidence assignments.

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
Auto-tags questions with `skill_tags` (8 top-level types) and `skill_subtype` (24 second-level subtypes) via keyword matching. Unified taxonomy for both parts. Unmatched Part 1 questions saved to `claude_p1_type_response.json` for manual review. Modes: default (tag empty only), `--overwrite` (re-tag all), `--subtype-only` (keep skill_tags, add/update subtypes). `--audit` generates `human-in-the-loop/skill_subtype_audit.md`.
```bash
python3 pipeline/tag_question_types.py merged_part1.json --part 1
python3 pipeline/tag_question_types.py merged_part2.json
python3 pipeline/tag_question_types.py merged_part1.json --part 1 --subtype-only  # subtypes only
python3 pipeline/tag_question_types.py merged_part2.json --subtype-only --audit   # with audit report
```
For **May–Aug** quarter files, pass paths under `data/quarters/2026-05-to-08/` (do not run against `data/quarters/2026-01-to-04/` unless intentionally updating the freeze).

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

### remap_content_tags_disposition.py
Batch-fixes Part 2 **`content_tags`** mis-tags. Three remap layers (run in order): (1) **`people` → `experience/activity > work`** when the cue focuses on work/business activity, not person identity (e.g. "a person who enjoys working for a family business"); (2) problem-solver canonical fix (hyphenated l3, `personal_growth`); (3) **`people` → `abstract_concepts > personal_traits`** for disposition/trait cues. Run **`--quarter <id>`** after topic dedup / `dedup_questions` / `renumber`, **before** assign → backfill → export. Rules: **`docs/taxonomy_people_vs_personal_traits.md`**.

```bash
python3 pipeline/remap_content_tags_disposition.py --quarter 2026-01-to-04 --dry-run
python3 pipeline/remap_content_tags_disposition.py --quarter 2026-01-to-04
```

### dedup_topics_part2.py
Merges **near-duplicate Part 2 topic objects** into one **survivor** and **deletes the loser row** from `merged_part2.json` — not just Part 3 question dedup inside a topic. Fixes duplicate grid cards and **empty Part 3 "shell" topics** (same cue, second row with `part3: []`). Clustering uses normalized **fingerprints** (optional trailing phrases stripped) plus fuzzy ratio, **contiguous substring** rules, and an **aggressive fingerprint** that strips modifier adjectives (`successful`, `well-known`, etc.) and normalizes temporal phrases (`an occasion` → `a time`) to catch modifier-variant near-duplicates. Run **before** assign → backfill → export.

**Keep-best (survivor):** more Part 3 questions → more `you_should_say` → richer `content_tags` → non-empty `season` → source tier (tongzhuo > laokaoya > yasige) → shorter `topic` string. Loser’s bullets / Part 3 / tags are merged into the survivor, then `dedup_questions` on the combined Part 3 list.

```bash
python3 pipeline/dedup_topics_part2.py --quarter 2026-01-to-04 --dry-run
python3 pipeline/dedup_topics_part2.py --quarter 2026-01-to-04
python3 pipeline/dedup_questions.py data/quarters/2026-01-to-04/merged_part2.json
python3 pipeline/renumber_questions.py data/quarters/2026-01-to-04/merged_part2.json
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

### generate_topic_hierarchy_markdown.py
Exports a topic hierarchy markdown for quick visual validation in TryMarkmap.
Hierarchy is fixed to:
- L1 (`content_tags.l1`)
- L2 (`content_tags.l2`)
- L3 (`content_tags.l3`)
- Questions/contents under each path

Output file (overwritten each run):
`human-in-the-loop/topic_hierarchy.md`

```bash
python3 pipeline/generate_topic_hierarchy_markdown.py
```

### audit_taxonomy_structure.py
Structural audit of the 3-level taxonomy hierarchy. Checks `config/topic_taxonomy_v2_curated.yaml` for: (1) **DUAL_HOME** — L3 under >1 L2 bucket (ERROR unless whitelisted); (2) **CROSS_L1** — L3 spanning different L1 categories (ERROR); (3) **NAME_COLLISION** — L3 name matching an L2 name (ERROR); (4) **CROSS_PARENT_NAME** — L3 name containing a non-parent L2 name (WARNING); (5) **BROAD_L3** — L3 with L2-level breadth patterns (WARNING); (6) **ORPHAN_CONTENT_L3** — L3 in `content_tags` but absent from YAML (WARNING); (7) **LEGACY_FORMAT** — hyphenated L3 in `content_tags` (INFO). Rules: each L3 must have exactly **one home** (L1>L2 parent); exceptions require explicit whitelist in the script.

```bash
python3 pipeline/audit_taxonomy_structure.py --quarter 2026-01-to-04
python3 pipeline/audit_taxonomy_structure.py --quarter 2026-01-to-04 --strict
```

### ingest_pipeline.py
For ingesting new source files into the question bank (future use).

### Taxonomy runtime loop (sidebar `topic_taxonomy_v2_final.json`)

**Do not hand-edit** `data/quarters/<quarter>/topic_taxonomy_v2_final.json`. Flow: **`content_tags`** in merged JSON → after ingest, **`dedup_topics_part2.py`** + **`dedup_questions.py`** / **`renumber_questions.py`** on quarter `merged_part2.json` when needed → **`remap_content_tags_disposition.py`** (people vs `experience/activity > work` and people vs `personal_traits` etc., see **`docs/taxonomy_people_vs_personal_traits.md`**) → optional **`build_topic_taxonomy_view_v2.py`** (still reads **root** merged only) → **`assign_primary_l3_v2.py`** (if the card already lists `content_tags.l3`, primary is chosen only from those labels plus a small **legacy→canonical** map, so runtime primary stays a subset of the card) → **`backfill_content_tags_l3_from_assignment.py`** (empty `l3` → append assignment primary; **plus** global append of canonical peers for legacy tokens e.g. `traveling`→`travel`) → optional minimal edit **`config/topic_taxonomy_v2_curated.yaml`** → **`export_runtime_taxonomy_v2.py`** → **`check_taxonomy_runtime_consistency.py`** → **`audit_taxonomy_structure.py --strict`** (verify no dual-home, no orphan L3, no structural violations).

Full steps: **`docs/taxonomy_runtime_runbook.md`**.

**Quarter / season handoff (new May–Aug data, new folder, `?quarter=`):** start with **`docs/season_rollover_runbook.md`** — fixed checklist from new `data/quarters/<id>/` through assign → backfill → export → check → local verify → git.

```bash
python3 pipeline/assign_primary_l3_v2.py --quarter 2026-01-to-04
python3 pipeline/backfill_content_tags_l3_from_assignment.py --quarter 2026-01-to-04
python3 pipeline/export_runtime_taxonomy_v2.py --quarter 2026-01-to-04
python3 pipeline/check_taxonomy_runtime_consistency.py --quarter 2026-01-to-04 --strict
python3 pipeline/audit_taxonomy_structure.py --quarter 2026-01-to-04 --strict
```

**Assign inputs:** `--quarter <id>` or `--part1` + `--part2` paths, or default root `merged_part*.json`. **`assign_primary_l3_v2_refined.py`** supports the same flags.

**Refined:** `python3 pipeline/assign_primary_l3_v2_refined.py --quarter 2026-01-to-04`

**Regenerate runtime taxonomy (align with current merged + YAML):** run assign → `backfill_content_tags_l3_from_assignment.py` → `export_runtime_taxonomy_v2.py` → `check_taxonomy_runtime_consistency.py` for the quarter (`docs/taxonomy_runtime_runbook.md` § Alignment validation). Do not edit `topic_taxonomy_v2_final.json` by hand. After a full rebuild, expect tuple-level drift vs any older snapshot that was not produced by this chain; `check_taxonomy_runtime_consistency.py`’s Part2 subset mismatch count tracks sidebar vs `content_tags` agreement.

## Git / Push
Proxy must be set for push:
```bash
export https_proxy=http://127.0.0.1:7897
git push
```

## Conventions
- Never embed data in `index.html` — always `fetch()` from JSON files under `data/quarters/<quarter-id>/`
- Preserve each topic’s `season` consistently within its quarter folder (frozen 1–4 topics keep e.g. `"2026-Jan-Apr"`; May–Aug folder uses `"2026-05-to-08"` unless you standardize otherwise)
- Strip all Chinese characters and zero-width chars from English fields
- `content_tags` is a 3-layer object `{"l1": str, "l2": [...], "l3": [...]}` — NOT a flat array
- `qualifier_tags` is a separate flat array for tone/quality descriptors
- `skill_tags` is a per-question array of 1-3 skill types
- After any JSON edit, always regenerate the matching `.txt` mirror
