# Quarter datasets (`data/quarters/`)

The **live website** loads question data and taxonomy **only** from here, based on the selected quarter.

## Supported quarters

| Folder | ID (for `?quarter=` and the UI dropdown) | Status |
|--------|------------------------------------------|--------|
| `2026-01-to-04/` | `2026-01-to-04` | **Frozen** — stable Jan–Apr snapshot; **do not change** for routine maintenance or May–Aug work |
| `2026-05-to-08/` | `2026-05-to-08` | **Placeholder** — initialized from 1–4 copy with `season: "2026-05-to-08"`; replace with real data when ready |

## Shared frontend

One `index.html`, one `js/` tree, one `css/` tree. Switching quarters **only** swaps which directory the three JSON files are loaded from. Sidebar, filters, content tags, skill tags, and card/modal rendering are unchanged.

## Files per quarter (required)

Each folder must contain:

1. `merged_part1.json`
2. `merged_part2.json`
3. `topic_taxonomy_v2_final.json` — per-quarter taxonomy map so topic sets can differ without cross-quarter pollution

## Updating real May–Aug data later

Replace **only** under `2026-05-to-08/`:

- `merged_part1.json`
- `merged_part2.json`
- `topic_taxonomy_v2_final.json`

You may remove or rewrite `PLACEHOLDER.txt` once the dataset is real.

## Season rollover (operational)

For step-by-step handoff when adding or replacing a quarter’s data, use **`docs/season_rollover_runbook.md`** (assign → backfill → export → check `--strict`, then frontend `?quarter=`).

## URL switching

- Default (no or invalid `quarter`): **`2026-01-to-04`**
- Examples: `?quarter=2026-01-to-04`, `?quarter=2026-05-to-08`

## Root JSON (legacy)

Repository root `merged_part1.json` / `merged_part2.json` (and `data/topic_taxonomy_v2_final.json`) are kept for legacy scripts/docs; they are **not** the browser’s primary source after quarter support shipped.
