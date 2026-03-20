# IELTS Speaking Question Bank

Personal IELTS Speaking topic bank: static site on Vercel (GitHub `main`), JSON loaded at runtime.

## Quarter switching

The site supports **two quarters** in one UI. **All** frontend code is shared (same `js/`, `css/`, sidebar, filters, tags, cards, modal).

| Quarter ID | Role |
|------------|------|
| `2026-01-to-04` | **Frozen** stable dataset — do **not** edit for routine work |
| `2026-05-to-08` | **Placeholder** today (copy of Jan–Apr with `season` set to `2026-05-to-08`); replace when real May–Aug data exists |

- **URL:** add `?quarter=<id>`  
  - Jan–Apr: `?quarter=2026-01-to-04` (also the default if the param is missing or invalid)  
  - May–Aug: `?quarter=2026-05-to-08`  
- **UI:** use the quarter dropdown (top right). The address bar is updated with `replaceState` so links are shareable.

## Data layout

Per-quarter files (these are what the browser loads):

```
data/quarters/
  2026-01-to-04/
    merged_part1.json
    merged_part2.json
    topic_taxonomy_v2_final.json
  2026-05-to-08/
    merged_part1.json
    merged_part2.json
    topic_taxonomy_v2_final.json   ← replace all three for real May–Aug
    PLACEHOLDER.txt
```

Root `merged_part1.json` / `merged_part2.json` / `data/topic_taxonomy_v2_final.json` are **legacy** mirrors for older workflows; the **live site** reads only `data/quarters/<quarter-id>/`.

## Local preview

From the repo root (needed so `fetch()` paths resolve):

```bash
python3 -m http.server 8765
```

Then open e.g. `http://127.0.0.1:8765/?quarter=2026-01-to-04` or `?quarter=2026-05-to-08`.

## Docs

- `CLAUDE.md` — day-to-day conventions for assistants
- `README_ARCH.md` — architecture and file roles
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
