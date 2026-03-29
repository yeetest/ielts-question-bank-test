# IELTS Question Bank

Static IELTS site with one shared visual system and two top-level sections:

- `speaking`
- `writing`

The site remains a static HTML/CSS/JS app on Vercel with JSON loaded at runtime.

## Current writing implementation

- The site now defaults to `?section=writing`.
- Writing uses the same existing visual style as the static question-bank project.
- Opening a writing card launches the main practice workspace.
- The workspace now follows the current product rule set:
  - one AI correction action only
  - one AI call deducts exactly 1 credit
  - one correction returns both:
    - IELTS band-score feedback
    - revised Band 9 version
  - right panel has only 2 tabs:
    - `Sample Band 9`
    - `My Revised Band 9`
  - left panel is the personal writing-library tree
  - manual save writes to the same library data source used by the left sidebar
  - highlights generate the flashcards used in `Practice High-Score Expressions`
  - auth and payment stay in modal flow and resume the pending action on return
  - OpenRouter is the only AI provider

## Current information architecture

- The old `May–Aug 2026` placeholder tab is removed from the UI.
- Speaking now uses only the real `2026-01-to-04` dataset.
- Writing is integrated into the same static project and rendered with the same card / modal system.
- The top menu is now the main navigation: `speaking / writing`.

## URL

- `?section=speaking`
- `?section=writing`

If the param is missing or invalid, the site defaults to `writing`.

## Data layout

Speaking files:

```
data/quarters/
  2026-01-to-04/
    merged_part1.json
    merged_part2.json
    topic_taxonomy_v2_final.json
```

Writing files:

```
data/
  writing_questions.json
```

Root `merged_part1.json` / `merged_part2.json` / `data/topic_taxonomy_v2_final.json` are **legacy** mirrors for older workflows.

## Local preview

From the repo root (needed so `fetch()` paths resolve):

```bash
python3 -m http.server 8765
```

Then open e.g.:

- `http://127.0.0.1:8765/?section=speaking`
- `http://127.0.0.1:8765/?section=writing`

## AI environment

Writing correction uses OpenRouter only.

Required env vars:

```bash
OPENROUTER_API_KEY=placeholder
OPENROUTER_MODEL=deepseek/deepseek-r1-0528
```

If either env var is missing, `api/ai.js` returns a clear error and does not generate any fallback output.

## Docs

- `CLAUDE.md` — day-to-day conventions for assistants
- `README_ARCH.md` — architecture and file roles
- `docs/writing_practice_flow.md` — current writing practice logic, data model, auth/credit flow
- **`docs/season_rollover_runbook.md`** — **quarter / season handoff** (new `data/quarters/<id>/`, taxonomy pipeline, verification)
- `data/quarters/README.md` — quarter directory contract
- `docs/taxonomy_runtime_runbook.md` — assign → backfill → export → check (detail)
- `docs/CLAUDE_tagging.md` — tagging rules

## Deploy

Push to `main` → Vercel deploys. Git push from this machine may need:

```bash
export https_proxy=http://127.0.0.1:7897
git push
```
