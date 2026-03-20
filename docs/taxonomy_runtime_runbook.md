# Taxonomy runtime runbook (convergent loop)

This is the **minimal closed loop** from topic `content_tags` in merged JSON → curated assignment → **flat runtime file** used by the website sidebar (`topic_taxonomy_v2_final.json`).

**Do not hand-edit** `data/quarters/<quarter>/topic_taxonomy_v2_final.json`. Regenerate it with **`pipeline/export_runtime_taxonomy_v2.py`** after assignment outputs change.

**Backfill (formal):** After assign, run **`pipeline/backfill_content_tags_l3_from_assignment.py`**: (1) topics with empty `content_tags.l3` receive the assignment `primary.l3` (append only); (2) **legacy canonical append** on all topics with non-empty l3 — appends YAML spellings for known legacy tokens (`traveling`→`travel`, `learning`→`learning_growth`, `decision`→`decision_making`, and `self_improvement` when only `self-improvement` appears). Keeps merged JSON aligned with the strict subset check without relaxing the checker.

---

## Step 1 — New topics in merged JSON with `content_tags`

| | |
|---|---|
| **Input** | Your editorial / ingest process |
| **Output** | `data/quarters/<quarter>/merged_part1.json`, `merged_part2.json` with structured `content_tags` `{l1, l2, l3}` per topic |
| **Scripts** | Ingest / `archive_legacy/pipeline_old/tag_content_v2.py` / manual — **not** part of this runbook |

No copy/symlink to repo root is required **for assignment** (Step 2b). **`build_topic_taxonomy_view_v2.py` (Step 2a)** still reads **root** `merged_part1.json` / `merged_part2.json` only — if you use that step for a quarter, sync root from the quarter folder or skip 2a.

---

## Step 2 — View / diagnostics / assignment

| | |
|---|---|
| **2a — Optional derived view (read-only)** | |
| Script | `pipeline/build_topic_taxonomy_view_v2.py` |
| Input | **Repo root** `merged_part1.json`, `merged_part2.json`, `config/topic_taxonomy_v2.yaml` |
| Output | `human-in-the-loop/topic_taxonomy_view_v2_part1.json`, `topic_taxonomy_view_v2_part2.json` |
| **2b — Primary L3 assignment (convergent layer)** | |
| Script | `pipeline/assign_primary_l3_v2.py` (or `pipeline/assign_primary_l3_v2_refined.py` + refined YAML) |
| Input | `config/topic_taxonomy_v2_curated.yaml` (or refined variant), **merged JSON via default root, `--quarter`, or `--part1`/`--part2`** |
| Output | `human-in-the-loop/topic_taxonomy_assignment_v2_part1.json`, `topic_taxonomy_assignment_v2_part2.json`, `l3_assignment_diagnostics_v2.md` |

```bash
# Optional: copy quarter merged to root if you need build_topic_taxonomy_view_v2.py
# cp data/quarters/2026-01-to-04/merged_part1.json merged_part1.json
# cp data/quarters/2026-01-to-04/merged_part2.json merged_part2.json
python3 pipeline/build_topic_taxonomy_view_v2.py   # optional

# Assign directly from quarter data (no root copy needed)
python3 pipeline/assign_primary_l3_v2.py --quarter 2026-01-to-04

# Or explicit paths:
python3 pipeline/assign_primary_l3_v2.py \
  --part1 data/quarters/2026-01-to-04/merged_part1.json \
  --part2 data/quarters/2026-01-to-04/merged_part2.json

# Default: unchanged — reads repo root merged_part*.json
python3 pipeline/assign_primary_l3_v2.py
```

Refined pass (same input flags):

```bash
python3 pipeline/assign_primary_l3_v2_refined.py --quarter 2026-01-to-04
```

Assign **does not** overwrite `content_tags` (see script docstring).

**Subset alignment (built-in):** When `content_tags.l3` is non-empty, the engine builds a set of **curated labels** from those strings (including `LEGACY_CONTENT_L3_TO_CURATED` in `assign_primary_l3_v2.py`: e.g. `learning`→`learning_growth`). If any aligned candidate scores above threshold, the winner is chosen **only from that aligned set** — otherwise the global top score wins. Tie-break uses the order of `content_tags.l2` on the card. `happiness` hints omit `enjoy` so phrases like “didn’t enjoy” do not steal the primary from `anger` / `learning_growth`.

---

## Step 2c — Backfill `content_tags.l3` from assignment (when empty)

| | |
|---|---|
| Script | **`pipeline/backfill_content_tags_l3_from_assignment.py`** |
| Input | Same quarter `merged_part*.json` + `human-in-the-loop/topic_taxonomy_assignment_v2_part*.json` |
| Output | Updates merged JSON in place (use `--dry-run` first) |
| Rule | (1) If `l3` is missing or `[]`, append assignment `primary.l3` if non-empty and not already listed. (2) **Always:** for non-empty `l3`, append canonical peers for legacy tokens (same map as assign; see script header). |

```bash
python3 pipeline/backfill_content_tags_l3_from_assignment.py --quarter 2026-01-to-04 --dry-run
python3 pipeline/backfill_content_tags_l3_from_assignment.py --quarter 2026-01-to-04
```

Topics whose assignment has **no** `primary.l3` (below score threshold) stay unchanged; see script audit lines `SKIP assignment_l3_empty`.

---

## Step 3 — Minimal curated YAML changes (only when needed)

| | |
|---|---|
| **Input** | `l3_assignment_diagnostics_v2.md`, optional candidate/shortlist artifacts from `generate_l3_candidates_v2.py` / `build_l3_canonical_shortlist_v2.py` |
| **Output** | Edited `config/topic_taxonomy_v2_curated.yaml` (or refined/final variant your project uses) |
| **人工** | **Required** when vocabulary or tie-break rules must change; keep changes **minimal** (reuse existing l2/l3; add l3 only with evidence — see `docs/taxonomy_calibration_notes_v2.md`) |

---

## Step 4 — Export runtime taxonomy (deterministic)

Run **after** assign and (when used) backfill so checks reflect the same assignment pass.

| | |
|---|---|
| Script | **`pipeline/export_runtime_taxonomy_v2.py`** |
| Input | `human-in-the-loop/topic_taxonomy_assignment_v2_part1.json`, `..._part2.json` |
| Output | `data/quarters/<quarter>/topic_taxonomy_v2_final.json` |

```bash
python3 pipeline/export_runtime_taxonomy_v2.py --quarter 2026-01-to-04
```

Explicit paths:

```bash
python3 pipeline/export_runtime_taxonomy_v2.py \
  --assignment-p1 human-in-the-loop/topic_taxonomy_assignment_v2_part1.json \
  --assignment-p2 human-in-the-loop/topic_taxonomy_assignment_v2_part2.json \
  --out data/quarters/2026-01-to-04/topic_taxonomy_v2_final.json
```

If you used **refined** assign outputs, pass those filenames via `--assignment-p1` / `--assignment-p2`.

---

## Step 5 — Consistency check (pre-release)

| | |
|---|---|
| Script | **`pipeline/check_taxonomy_runtime_consistency.py`** |
| Input | `data/quarters/<quarter>/merged_part1.json`, `merged_part2.json`, `topic_taxonomy_v2_final.json` |
| Output | stdout summary; **`--strict`** exits non-zero if any topic lacks taxonomy row or has empty `l1` |

```bash
python3 pipeline/check_taxonomy_runtime_consistency.py --quarter 2026-01-to-04
python3 pipeline/check_taxonomy_runtime_consistency.py --quarter 2026-01-to-04 --strict
```

Deeper **content_tags vs taxonomy** audit (report only): `docs/content_tags_vs_taxonomy_v2_audit_2026-01-to-04.md` methodology; **缺失:** single automated markdown reporter for arbitrary quarter (optional future).

---

## Alignment validation (rebuild + diff)

Use this when you want to **regenerate** `topic_taxonomy_v2_final.json` from the current merged JSON + curated YAML (same path the site loads), then measure drift from any previous snapshot and content_tags fit.

```bash
# optional: save current runtime file for diff
cp data/quarters/2026-01-to-04/topic_taxonomy_v2_final.json /tmp/taxonomy_before.json

python3 pipeline/assign_primary_l3_v2.py --quarter 2026-01-to-04
python3 pipeline/backfill_content_tags_l3_from_assignment.py --quarter 2026-01-to-04
python3 pipeline/export_runtime_taxonomy_v2.py --quarter 2026-01-to-04
python3 pipeline/check_taxonomy_runtime_consistency.py --quarter 2026-01-to-04
# add --strict to fail CI if any merged topic lacks a taxonomy row or l1 is empty
```

**Interpreting `check_taxonomy_runtime_consistency.py`:** the printed line *Part2 topics with content_tags vs taxonomy primary mismatch (strict subset rule)* counts Part 2 topics where taxonomy `l1/l2/l3` is **not** a subset of `content_tags` lists (after L1 normalization). A **lower** number usually means **better** sidebar–card agreement; zero is ideal but not always reachable without changing merged data or curated vocabulary.

**Drift vs an old file:** after re-export, diff the JSON (e.g. compare `(topic → l1,l2,l3)` tuples). Any prior `topic_taxonomy_v2_final.json` that was **not** produced by this assign→export chain may differ widely; that is expected once the unified flow is adopted.

---

## Command order (copy-paste)

```bash
python3 pipeline/build_topic_taxonomy_view_v2.py    # optional; needs root merged copies
python3 pipeline/assign_primary_l3_v2.py --quarter 2026-01-to-04
python3 pipeline/backfill_content_tags_l3_from_assignment.py --quarter 2026-01-to-04
# (human) edit config if needed, then re-run assign + backfill

python3 pipeline/export_runtime_taxonomy_v2.py --quarter 2026-01-to-04
python3 pipeline/check_taxonomy_runtime_consistency.py --quarter 2026-01-to-04 --strict
```

---

## Related design docs

- `docs/season_rollover_runbook.md` — onboarding a **new quarter folder** end-to-end (merged JSON → pipeline → `?quarter=` → git)
- `docs/pipeline_v2_design.md` — view derivation, no production overwrite
- `docs/taxonomy_v2_freeze_notes.md` — freeze artifacts naming
- `docs/taxonomy_calibration_notes_v2.md` — refined calibration rules
- `docs/l3_rebuild_strategy_v2.md` / `docs/l3_canonicalization_strategy_v2.md` — bottom-up candidates (governance, not runtime export)
- `docs/working_rules.md` — code + memory file delivery protocol
