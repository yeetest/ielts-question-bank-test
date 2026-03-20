# IELTS Question Bank — Architecture Guide

This document explains the project architecture for any future AI assistant (ChatGPT, Claude, Cursor Agent, etc.).
It focuses on what is implemented now, how files collaborate, what is legacy, and what is planned.

## 1) Project Purpose

This is a personal IELTS Speaking question bank for teaching use.

- **Primary data source (browser):** `data/quarters/<quarter-id>/merged_part1.json`, `merged_part2.json`, and `topic_taxonomy_v2_final.json`
- **Quarters:** `2026-01-to-04` (frozen stable) and `2026-05-to-08` (placeholder until real May–Aug data replaces the three JSON files)
- **Shared UI:** one frontend — same `js/`, `css/`, sidebar, filters, tags, grid, modal for both quarters
- Frontend: static site (`index.html` + modular `js/` + modular `css/`)
- Deployment: GitHub `main` branch to Vercel
- Editing model: JSON is source of truth; human-editable TXT mirrors are generated for manual workflow
- **Legacy:** root `merged_part1.json` / `merged_part2.json` remain for older scripts; the live app does not read them as the main source

Core principle: data stays in JSON files and is loaded at runtime via `fetch()`. No hardcoded question data in HTML.

## 2) What The App Currently Implements

### Frontend features already working

- Part switch: `Part 1` and `Part 2 + Part 3`
- Topic card grid rendering from JSON
- Modal detail view per topic
- Tag-driven navigation:
  - click content tag => topic summary by that tag
  - click skill tag => question summary by that skill type
- Sidebar filter system:
  - mode: `focused` / `blended`
  - skill tags (`skill_tags`)
  - time frame (`past` / `present` / `future`)
  - content hierarchy (`l1` -> `l2` -> `l3`)
- Dynamic counts in sidebar and header topic counter
- Filter reset, tab switching, sidebar collapse/expand
- **Quarter switcher** (top right) + URL `?quarter=2026-01-to-04` | `?quarter=2026-05-to-08` (default: `2026-01-to-04`)

### Data engineering utilities already present

- Auto-tag question skill types: `pipeline/tag_question_types.py`
- Auto-tag question time frames: `pipeline/tag_time_frames.py`
- Auto-tag topic content hierarchy v2: `pipeline/tag_content_v2.py`
- Renumber and dedup helpers: `pipeline/renumber_questions.py`, `pipeline/dedup_questions.py`, etc.
- Human-in-the-loop mirror generation: `human-in-the-loop/json_to_txt.py`

## 3) High-Level Architecture

### Runtime architecture (browser)

1. `index.html` loads CSS and `js/app.js`
2. `js/app.js` initializes sidebar/events, quarter switcher, and `loadData(quarterId)`
3. `js/data.js` fetches (paths depend on selected quarter, default `2026-01-to-04`):
   - `data/quarters/<id>/merged_part1.json`
   - `data/quarters/<id>/merged_part2.json`
   - `data/quarters/<id>/topic_taxonomy_v2_final.json`
4. Data is stored in `js/state.js`
5. UI renders through components:
   - `js/components/grid.js`
   - `js/components/sidebar.js`
   - `js/components/modal.js`
   - `js/components/tagSummary.js`
6. Utility rendering helpers in `js/utils.js`

### Authoring architecture (local maintenance)

1. Update JSON directly or via scripts
2. Run tagging/cleanup scripts as needed
3. Regenerate TXT mirrors (`human-in-the-loop/json_to_txt.py`)
4. Validate output in frontend

## 4) File-by-File Roles

## Frontend entry

- `index.html`
  - App shell and mount points
  - Loads all CSS modules and `js/app.js`
  - Contains Google Analytics snippet

## JavaScript modules

- `js/app.js`
  - App bootstrap, quarter switch + URL sync (`?quarter=`)
  - Event delegation for grid and modal interactions
  - Modal open/close wiring
- `js/data.js`
  - Resolves quarter (URL or default), fetches three JSONs under `data/quarters/<id>/`
  - Triggers `renderGrid()` and `renderSidebar()` after load
- `js/state.js`
  - Shared in-memory app state (`currentQuarterId`, active tab, filters, datasets)
- `js/utils.js`
  - Render helpers for skill tags/content tags
  - Backward compatibility for old flat `content_tags` arrays
  - Topic title cleanup helper
- `js/components/grid.js`
  - Topic cards rendering logic
- `js/components/modal.js`
  - Topic detail modal rendering and back navigation
- `js/components/sidebar.js`
  - Full filter engine, cascade counting, hierarchy-constrained display
  - Tab change and sidebar collapse behavior
- `js/components/tagSummary.js`
  - "all topics by content tag" and "all questions by skill type" summaries

## CSS modules

- `css/base.css`: typography, base styles
- `css/layout.css`: page layout and global containers
- `css/components/cards.css`: topic cards
- `css/components/modal.css`: modal overlay/content
- `css/components/sidebar.css`: filter panel UI
- `css/components/tags.css`: content/skill/inline tag styling

## Data

- `data/quarters/2026-01-to-04/` and `data/quarters/2026-05-to-08/`
  - Each contains: `merged_part1.json` (Part 1 `questions[]`), `merged_part2.json` (Part 2 `part3[]`), `topic_taxonomy_v2_final.json` (per-quarter taxonomy map for filters)
  - **Frozen:** `2026-01-to-04` — do not edit for routine / May–Aug work
  - **Placeholder:** `2026-05-to-08` — replace the three JSON files when real data exists
- `merged_part1.json` / `merged_part2.json` (repo root)
  - Legacy duplicates; not the browser’s primary load path after quarter support
- `tags/tags.txt`
  - controlled vocabulary reference

## Documentation

- `README.md`
  - quick start: quarters, URLs, local preview, deploy note
- `CLAUDE.md`
  - highest-priority operational conventions
- `data/quarters/README.md`
  - quarter directory contract (frozen vs placeholder, which files to replace)
- `docs/taxonomy_runtime_runbook.md`
  - convergent loop: content_tags → assign → backfill empty `l3` from assignment → export `topic_taxonomy_v2_final.json` → consistency check
- **`docs/season_rollover_runbook.md`** — **next quarter onboarding:** new `data/quarters/<id>/`, merged JSON, full pipeline, `?quarter=` verify, memory updates (read this before seasonal data drops)
- `docs/working_rules.md`
  - code + memory file delivery; when to update docs; end-of-task summary
- `docs/CLAUDE_tagging.md`
  - full tagging rules and taxonomy details

## 5) How HTML / JS / JSON / CSS Work Together

- HTML defines structure only (tabs, sidebar root, grid root, modal root).
- JS fetches JSON and transforms it into interactive UI.
- JSON stores all question bank content and tags.
- CSS applies visual system to components generated by JS.

In short:
- `HTML` = skeleton
- `JSON` = content source of truth
- `JS` = rendering + interaction + filtering engine
- `CSS` = presentation layer

## 6) Current Data Schema (v2 in production)

## Topic-level tags

`content_tags` is now structured:

- `l1`: one primary category
- `l2`: array of thematic clusters
- `l3`: array of specific tags
- `qualifier_tags`: separate flat array

This applies to both Part 1 and Part 2 topic objects.

## Question-level tags

Each question can have:

- `skill_tags`: 1-3 values from unified 8-type taxonomy
- `time_frame`: one of `past` / `present` / `future`

## 7) Operational Workflows

## Standard frontend run/debug

Any static server is fine, because JSON is fetched at runtime. Run from **repo root**:

```bash
python3 -m http.server 8765
```

Open `http://127.0.0.1:8765/?quarter=2026-01-to-04` or `?quarter=2026-05-to-08`. Avoid `file://` (fetch paths break).

## Standard data update flow

1. Edit JSON or run a pipeline script — for May–Aug, target paths under **`data/quarters/2026-05-to-08/`** only (do not change `2026-01-to-04/` unless intentionally updating the freeze).
2. If JSON changed, regenerate TXT mirror(s) (pass the same path you edited):
   - `python3 human-in-the-loop/json_to_txt.py data/quarters/2026-05-to-08/merged_part1.json`
   - `python3 human-in-the-loop/json_to_txt.py data/quarters/2026-05-to-08/merged_part2.json`
3. Re-open frontend with the correct `?quarter=` and verify filtering/modal behavior

## Taxonomy runtime runbook (sidebar filters)

The site loads **`data/quarters/<quarter>/topic_taxonomy_v2_final.json`** for `taxonomy_v2_primary`. That file must be **exported from assignment outputs**, not edited by hand.

1. Merged JSON has **`content_tags`** (input layer).
2. Optional **`pipeline/build_topic_taxonomy_view_v2.py`** (reads **root** merged only). **`pipeline/assign_primary_l3_v2.py --quarter <id>`** (or `--part1` / `--part2`) → `human-in-the-loop/topic_taxonomy_assignment_v2_part*.json`.
3. **`python3 pipeline/backfill_content_tags_l3_from_assignment.py --quarter <id>`** — when `content_tags.l3` is empty, append assignment `primary.l3`; always run the **legacy canonical append** pass (e.g. `traveling`→`travel`, `learning`→`learning_growth`) so subset checks can see YAML spellings (see runbook).
4. If diagnostics require it, minimally edit **`config/topic_taxonomy_v2_curated.yaml`**, then re-run assign and backfill.
5. **`python3 pipeline/export_runtime_taxonomy_v2.py --quarter <id>`** → writes flat runtime taxonomy.
6. **`python3 pipeline/check_taxonomy_runtime_consistency.py --quarter <id> --strict`** before release.

Authoritative copy-paste workflow: **`docs/taxonomy_runtime_runbook.md`**. To **rebuild** the sidebar taxonomy from current quarter merged JSON (assign → backfill → export → check), follow the same doc § **Alignment validation**.

## Project memory protocol

Non-trivial changes should update **`CLAUDE.md`**, **`README_ARCH.md`**, and any affected **`docs/*`** in the same delivery. Rules and end-of-task summary expectations: **`docs/working_rules.md`**.

## Human-in-the-loop flow

- The intended workflow in `CLAUDE.md` says TXT can be edited then synced back.
- Current implementation status warning:
  - `json_to_txt.py` outputs block-format TXT (`== topic ==`, `SEASON:`, `PART3:`)
  - `txt_to_json.py` expects flat `key=value` format
  - These two are not format-compatible at the moment

This mismatch should be fixed before relying on TXT->JSON round-trip.

## 8) Legacy vs Active Script Tracks

## Active track (recommended)

- `pipeline/tag_content_v2.py`
- `pipeline/tag_question_types.py`
- `pipeline/tag_time_frames.py`
- `pipeline/renumber_questions.py`
- `pipeline/dedup_questions.py`
- `human-in-the-loop/json_to_txt.py`

## Legacy/experimental track (not mainline)

- `pipeline/tag_content_topics.py`
  - still assumes older flat `content_tags` array model in prompt/response
- `pipeline/rewrite_content_tags.py`
  - migration utility from old flat tags to structured v2
- `pipeline/ingest_pipeline.py`
  - marked future use and still uses old `category/substance/frame_angle` tagging schema
- keyword exploration helpers:
  - `pipeline/extract_keywords.py`
  - `pipeline/filter_nouns_verbs.py`
  - `pipeline/filter_adjs.py`
  - `pipeline/query_conceptnet.py`
  - `pos_split.py`

These may still be useful for research, but they are not the production tagging path.

## 9) Redundancy / Cleanup Guidance

## Safe to delete now

- All `.DS_Store` files
- `claude_tag_response.json` when not actively using `tag_content_topics.py --apply`

## Keep but review (not immediate deletion)

- `pipeline/ingest_pipeline.py` (future plan but schema outdated)
- `pipeline/tag_content_topics.py` (old flat-tag workflow)
- `pipeline/rewrite_content_tags.py` (historical migration script)
- `pipeline/analyze_tag_hierarchy.py` (paired with migration script)
- `human-in-the-loop/txt_to_json.py` (currently format-mismatched to `json_to_txt.py`)

## Minor code cleanup candidates

- `css/components/tags.css`: `.tftag*` classes appear unused in current UI
- `pipeline/tag_time_frames.py`: `PAST_EXCLUSIONS` is defined but not used

## 10) Known Gaps and Unfinished Plans

- Ingest pipeline is not aligned with current v2 taxonomy and needs redesign.
- TXT round-trip is only half-complete (JSON->TXT works; TXT->JSON parser incompatible).
- Some old scripts and docs still describe pre-v2 logic and can confuse future automation.
- Frontend currently supports old flat `content_tags` as fallback; this compatibility may be removable once all data is guaranteed v2.

## 11) Rules Future AI Must Follow

When an AI assistant edits this repo, prioritize:

1. `CLAUDE.md` conventions first
2. Do not embed dataset into `index.html`; always load JSON via `fetch()`
3. Preserve `season` values exactly
4. Keep `content_tags` as structured object (`l1/l2/l3`) and `qualifier_tags` separate
5. After JSON edits, regenerate corresponding TXT mirrors
6. Treat `pipeline/` and `human-in-the-loop/` as local tooling (usually gitignored)

## 12) Suggested Next Refactor Milestones

1. Unify TXT round-trip:
   - make `txt_to_json.py` parse current block format, or
   - change `json_to_txt.py` output to a format `txt_to_json.py` can read
2. Decide fate of legacy content-tag scripts:
   - archive in `pipeline/legacy/` or delete after confirmation
3. Align `ingest_pipeline.py` with v2 schema (`l1/l2/l3` + `qualifier_tags`)
4. Optionally prune compatibility code for old flat tags after dataset verification

---

If you are a future AI assistant: read `CLAUDE.md` first, then this file, then `docs/CLAUDE_tagging.md` before changing data scripts.
