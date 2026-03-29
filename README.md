# IELTS Question Bank

Static IELTS site with one shared visual system and two top-level sections:

- `speaking`
- `writing`

The site remains a static HTML/CSS/JS app on Vercel with JSON loaded at runtime.

## Current writing implementation

- The site now defaults to `?section=writing`.
- Writing uses the same existing visual style as the static question-bank project.
- Opening a writing card now enters a dedicated full-page practice workspace.
- Writing card pages now have a quick left-sidebar filter for immediate use:
  - `Task 1`: action / register / topic
  - `Task 2`: mode / topic
- The workspace now follows the current product rule set:
  - one AI correction action only
  - one AI call deducts exactly 1 credit
  - one correction returns both:
    - IELTS band-score feedback
    - revised Band 9 version
    - keyword outline
  - right panel now shows only the user-specific revised Band 9 result
  - left panel is the personal writing-library tree
  - manual save writes to the same library data source used by the left sidebar
  - highlights generate the flashcards used in `Practice High-Score Expressions`
  - auth and payment stay in modal flow and resume the pending action on return
  - OpenRouter is the only AI provider
  - the editor and result panel can be resized by dragging the middle divider
  - selected text now shows floating actions near the selection
  - writing cards are deduped, cleaned, and tagged in a more speaking-like way

## Current information architecture

- The old `May–Aug 2026` placeholder tab is removed from the UI.
- Speaking now uses only the real `2026-01-to-04` dataset.
- Writing is integrated into the same static project and rendered with the same card system plus a dedicated practice page.
- Writing cards now display only the approved manual core sentence, not the old auto-extracted duplicate preview.
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
OPENROUTER_MODEL=anthropic/claude-opus-4.6
SUPABASE_URL=placeholder
SUPABASE_ANON_KEY=placeholder
SUPABASE_PROJECT_REF=placeholder
SUPABASE_ACCESS_TOKEN=placeholder
SUPABASE_DB_PASSWORD=placeholder
SUPABASE_SERVICE_ROLE_KEY=placeholder
```

**Vercel / server:** set `SUPABASE_SERVICE_ROLE_KEY` to your project’s **service_role** key (Settings → API). It is used only in `api/_lib/auth.js` to PATCH `profiles.credits` after AI correction; never expose it in frontend or commit it. After pulling migration `20260330140000_profiles_revoke_client_update.sql`, apply it to your Supabase project so users cannot self-update `profiles` via the anon key.

Optional (defaults avoid truncated JSON from long assessments): `OPENROUTER_MODEL_ASSESSMENT`, `OPENROUTER_MAX_TOKENS_ASSESSMENT` (default `4096`), `OPENROUTER_MAX_TOKENS_REWRITE` (default `8192`).

If OpenRouter env is missing, `api/ai.js` returns a clear error and does not generate any fallback output.
Writing auth now uses Supabase email auth only.

## Supabase schema

The repo now includes formal Supabase migrations under:

```bash
supabase/migrations/
```

They create:

- `profiles`
- `credit_transactions`
- `writing_tasks`
- `practice_records`
- `highlights`
- `flashcards`
- `pending_actions`

They also:

- enable RLS on user-owned tables
- add the `auth.users` -> `profiles` signup trigger
- backfill profile rows for existing auth users

To apply the schema to a remote Supabase project without using Table Editor manually:

```bash
zsh scripts/apply-supabase-schema.sh
```

This requires these env vars to be set locally:

- `SUPABASE_PROJECT_REF`
- `SUPABASE_ACCESS_TOKEN`

`SUPABASE_DB_PASSWORD` is no longer required for the default path because the apply script now uses the Supabase Management API instead of direct Postgres TLS.

## Docs

- `CLAUDE.md` — day-to-day conventions for assistants
- `README_ARCH.md` — architecture and file roles
- `docs/PROJECT_STRUCTURE.md` — where speaking / writing / shared files live now
- `docs/writing/writing_practice_flow.md` — current writing practice logic, data model, auth/credit flow
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
