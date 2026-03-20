# Schema Drift Audit v2

Scope: read-only audit against canonical schema (`docs/canonical_tag_schema_v2.md`, `config/canonical_tag_schema_v2.yaml`)  
Date: 2026-03-14  
Constraint: no code/data modification during this audit.

---

## Executive Summary

- Current production JSON already uses structured `content_tags` in 100% topics (`103/103`), no flat arrays found.
- Canonical alias gap exists: data uses `experience/activity`; canonical preferred `experience_activity` is not present.
- `content_tags` has no `l2 -> l1` parent collision in current data (`0` multi-parent `l2` tags).
- `l3` shows 15 multi-parent co-occurrence cases, but many are amplified by schema ambiguity (no explicit `l3 -> l2` binding per topic when multiple `l2` are present).
- `skill_tags` is fully populated and uses only current compatible set; canonical future names (`describe/evaluate/analysis`) are not present.
- `time_frame` is fully populated, only valid closed-set values (`past/present/future`), no illegal values.
- `qualifier_tags` is present with low volume and currently does not overlap with `content_tags.l2/l3`.
- Legacy `tags` field still appears (1 non-empty record), indicating residual legacy payload in production data.
- Legacy `category/substance/frame_angle` is not found in production JSON fields.
- `tag_content_v2.py` and `sidebar.js` still hardcode taxonomy, so source-of-truth duplication remains unresolved.
- `tag_question_types.py` has asymmetric behavior: Part 1 can output empty arrays (`[]`) for unmatched; Part 2 falls back to `["description"]`.
- `tag_time_frames.py` defines exclusions (`PAST_EXCLUSIONS`) but does not apply them in classifier logic.
- UI still supports flat `content_tags` fallback even though data is fully structured.
- Hierarchy markdown exporter currently expands `l2 x l3` cartesian combinations and can overstate tree branching.
- Current markdown export is still usable for rough exploration, but not reliable as canonical primary-path topology.

---

## Data Reality vs Canonical

### content_tags

#### Structure type coverage

- Total topics audited: `103`
- Structured object (`{l1,l2,l3}`): `103` (`100.00%`)
- Flat array: `0` (`0.00%`)
- Missing/null: `0` (`0.00%`)
- Other abnormal structure: `0` (`0.00%`)

By file:
- `merged_part1.json`: `44/44` structured
- `merged_part2.json`: `59/59` structured

#### `l1` unique values (frequency desc)

- `abstract_concepts`: `30`
- `experience/activity`: `25`
- `object`: `23`
- `place`: `15`
- `people`: `10`

Alias check:
- `experience/activity` present: **Yes**
- `experience_activity` present: **No**

#### `l2` unique values grouped by `l1`

- `people`: `close_bonds (6)`, `professions (5)`, `general (1)`
- `place`: `outdoor (11)`, `indoor (5)`
- `object`: `intangible (15)`, `tangible (13)`
- `experience/activity`: `leisure (12)`, `routines (8)`, `study (4)`, `work (4)`
- `abstract_concepts`: `personal_growth (9)`, `emotion (9)`, `communication (8)`, `time (5)`, `values (4)`, `personal_traits (4)`, `influence (2)`

#### `l3` unique values grouped by observed `l2` co-occurrence

Observed under `intangible`:
- `technology (10)`, `artwork (4)`, `media (3)`, `money (1)`

Observed under `tangible`:
- `artwork (2)`, `media (2)`, `technology (2)`, `money (1)`

Observed under `leisure`:
- `traveling (4)`, `exercise (3)`, `shopping (3)`, `entertainment (2)`, `reading (1)`

Observed under `work`:
- `traveling (1)`, `shopping (1)`

Observed under `values`:
- `environment (3)`, `policy (2)`

Observed under `emotion`:
- `happiness (3)`, `learning (2)`, `regret (2)`, `anger (1)`, `patience (1)`, `problem-solving (1)`, `attachment (1)`, `adaptation (1)`, `fear (1)`

Observed under `personal_growth`:
- `self-improvement (3)`, `learning (2)`, `goal-setting (1)`, `happiness (1)`, `anger (1)`, `decision (1)`, `problem-solving (1)`, `regret (1)`, `adaptation (1)`, `fear (1)`

Observed under `personal_traits`:
- `creativity (2)`, `problem-solving (2)`, `regret (1)`

Observed under `communication`:
- `self-improvement (1)`, `regret (1)`

Observed under `time`:
- `problem-solving (1)`, `adaptation (1)`, `fear (1)`

Observed under `influence`:
- `creativity (1)`

#### Illegal/unstable hierarchy combination checks

`l2` under multiple `l1`:
- Count: `0`
- Interpretation: no direct `l2` parent collision detected in current data.

`l3` under multiple `l2` (top):
- `technology`: `{intangible:10, tangible:2}`
- `artwork`: `{intangible:4, tangible:2}`
- `media`: `{intangible:3, tangible:2}`
- `problem-solving`: `{personal_traits:2, time:1, emotion:1, personal_growth:1}`
- `regret`: `{emotion:2, personal_growth:1, personal_traits:1, communication:1}`
- `adaptation`: `{emotion:1, personal_growth:1, time:1}`
- `fear`: `{emotion:1, personal_growth:1, time:1}`
- `traveling`: `{leisure:4, work:1}`
- `shopping`: `{leisure:3, work:1}`
- `happiness`: `{emotion:3, personal_growth:1}`

Important caveat:
- Current schema stores `l2[]` and `l3[]` as separate arrays without explicit pair mapping.
- Therefore, when a topic has multiple `l2`, exact parent for each `l3` is ambiguous.
- Some multi-parent results above may reflect modeling ambiguity, not necessarily true semantic mislabel.

#### Multi-path analysis

Legitimate multi-tag candidates (content truly spans multiple domains):
- `media + technology` on TV/online program topics
- `environment + policy` on natural world/government intervention topics
- `communication + influence` on encouragement/persuasion topics
- `close_bonds + professions` on people topics with social + role dimensions

Suspected drift candidates (need review):
- `technology/artwork/media/money` co-occurring under `tangible`
- `problem-solving/regret/fear/adaptation` spreading across `emotion/personal_growth/time/personal_traits`
- `shopping/traveling` under `work` in otherwise leisure-centered topics

Diagnosis:
- Not all are labeling errors; a portion is likely caused by missing explicit parent binding between `l2` and `l3`.

---

### skill_tags

#### Unique values (frequency desc)

- `description`: `324`
- `evaluation`: `142`
- `analyze`: `113`
- `preference`: `61`
- `comparison`: `40`
- `frequency`: `38`
- `hypothetical`: `36`
- `experience`: `32`

#### Old vs canonical-target value presence

Old/current-compatible values:
- `description`: **present**
- `evaluation`: **present**
- `analyze`: **present**

Canonical target values:
- `describe`: **absent**
- `evaluate`: **absent**
- `analysis`: **absent**

#### Per-question skill tag length distribution

- `0 tags`: `0`
- `1 tag`: `460` (`75.41%`)
- `2 tags`: `124` (`20.33%`)
- `3+ tags`: `26` (`4.26%`)

#### Anomalies

- Empty string tags: not found
- Non-string skill tag entries: not found
- Typo-like unknown values: not found in audited data

---

### time_frame

#### Unique values (frequency desc)

- `present`: `531` (`87.05%`)
- `past`: `42` (`6.89%`)
- `future`: `37` (`6.07%`)

#### Validity checks

- Illegal values (outside `past|present|future`): `0`
- Missing values: `0/610` (`0.00%`)

#### Substitution trace

- No question-level `time_frame` gaps detected.
- Therefore no evidence that topic-level fields are currently substituting missing question-level time labels.

---

### qualifier_tags

#### Unique values (frequency desc)

- `sentimental`: `3`
- `memorable`: `3`
- `interesting`: `3`
- `useful`: `1`
- `peaceful`: `1`

#### Baseline consistency

- Canonical baseline outside values found: **None**
- Overlap with `content_tags.l2`: **None**
- Overlap with `content_tags.l3`: **None**

#### Topic-noun contamination check

- No obvious topic noun contamination found in current qualifier set.
- Current usage appears aligned with tone/quality modifier intent.

---

### legacy fields

#### `tags` field

- Field exists broadly as empty array in topics.
- Non-empty records: `1`
  - Topic: `something that you can’t live without (not a computer/phone)`
  - Value: `["事物类"]`
  - File: `merged_part2.json`

#### `category` / `substance` / `frame_angle` in production JSON

- Not found in merged production data fields.

#### Other likely legacy residues

- Flat-array `content_tags`: not present in current production data.
- Backward-compatibility code paths still exist in consumer scripts/UI.

---

## Rule Drift (pipeline scripts)

### `pipeline/tag_content_v2.py`

Drift checks:
- Hardcoded `experience/activity` slash form: **Yes** (not canonical underscore form)
- Generates flat `content_tags`: **No** (writes dict `{l1,l2,l3}`)
- Qualifier mixed into taxonomy output: **No** (script only writes `content_tags`)
- Parent-binding model:
  - Produces one `l1`, top-N `l2`, top-N `l3`
  - Does **not** encode explicit `l3 -> l2` linkage
  - Multi-tag is unconstrained by per-path ownership (array-only model)

Output contract:
- Input: CLI file path (`merged_part1.json`/`merged_part2.json`) + part flag
- Output: overwrites same input JSON file (unless dry-run)
- Side effects: triggers `human-in-the-loop/json_to_txt.py` when writing
- Called by a master pipeline script: **No direct orchestrator found** (doc-driven manual sequence)

### `pipeline/tag_question_types.py`

Drift checks:
- Outputs old names (`description/evaluation/analyze`): **Yes**
- Outputs canonical names (`describe/evaluate/analysis`): **No**
- Possible empty arrays/fallback:
  - Part 1 unmatched -> `[]` (and logs to `claude_p1_type_response.json`)
  - Part 2 unmatched -> fallback `["description"]`
- `unclear` support:
  - Mentioned in comments/doc context, but current Part 1 branch stores `[]`; Part 2 uses `description` fallback

Output contract:
- Input: CLI file path + optional `--part 1`
- Output: overwrites same input JSON
- Side effects:
  - Part 1: writes `claude_p1_type_response.json` for unmatched
  - Part 1: triggers `json_to_txt.py`
  - Part 2: does **not** trigger txt regeneration in current implementation
- Called by a master pipeline script: **No direct orchestrator found**

### `pipeline/tag_time_frames.py`

Drift checks:
- Unused rule block: `PAST_EXCLUSIONS` defined but not applied in classifier
- Illegal value generation risk: low (classifier only returns `past|present|future`)
- Empty output risk: low for normal questions (default `present`)

Output contract:
- Input: CLI file path + optional `--part`, `--dry-run`, `--overwrite`
- Output: overwrites same input JSON (unless dry-run)
- Side effects: triggers `json_to_txt.py` when writing
- Called by a master pipeline script: **No direct orchestrator found**

---

## UI Drift (runtime consumers)

Files audited:
- `js/components/sidebar.js`
- `js/utils.js`
- `js/components/tagSummary.js`

### 1) Hardcoded hierarchy / schema drift

- `sidebar.js` hardcodes `L1_TO_L2` and `L2_TO_L3` maps.
- Still hardcodes slash form `experience/activity`.
- Canonical preferred alias (`experience_activity`) is not supported in UI mapping.
- `utils.js` still includes flat-array compatibility fallback.

### 2) Runtime data contract assumptions

- `content_tags` assumed as:
  - primary path root `l1` (single string)
  - multi-value arrays `l2[]`, `l3[]`
- UI filter behavior does not model explicit `l3 -> l2` ownership per topic.
- With multiple `l2`, all topic `l3` are effectively treated as jointly attached once topic passes filters.

### 3) Tag summary behavior

- `tagSummary.js` (`hasContentTag`) matches tag presence across any layer (`l1/l2/l3`).
- Secondary tags and primary-path tags are treated uniformly for summary navigation.
- This supports exploration but can blur strict tree semantics.

### 4) Alias risk

- If data migrates to `experience_activity` before UI mapping update, category filters/counts can misalign.
- Current data still uses slash form, so current runtime is stable but alias migration is brittle.

---

## Export Drift (markdown hierarchy)

File audited:
- `pipeline/generate_topic_hierarchy_markdown.py`

### 1) Logic-fit assessment

- Export expands every topic as nested loops: `for l2 in l2_list` + `for l3 in l3_list`.
- This is a cartesian expansion when topic has multiple `l2` and multiple `l3`.
- Consequence:
  - duplicates across branches
  - possible parent misattribution of `l3`
  - amplified tree breadth in markmap

Checks requested:
- Uses all `l2/l3` expansions: **Yes**
- Assumes a single explicit primary path: **No**
- Can render secondary tags as if they were primary tree branches: **Yes**
- Can produce visual repetition/misalignment even when source tagging is intended multi-label: **Yes**

### 2) Decision

- Can current markdown export still be used? **Yes, for rough coverage/debug only.**
- Is it topology-accurate for canonical primary tree? **No.**
- Recommended future export mode:
  - Tree: primary path only
  - Secondary tags: separate appendix/index (cross-links), not merged into primary tree branching

---

## Top 10 Highest-Risk Inconsistencies

1. Canonical alias mismatch: `experience/activity` still active everywhere; canonical underscore form absent.
2. Multi-source taxonomy duplication (`docs`, `tags`, `pipeline`, `UI`) increases divergence risk.
3. No explicit `l3 -> l2` binding in data model; downstream tools infer via ambiguity.
4. Markdown hierarchy exporter cartesian-expands multi-tags, overstating structural branching.
5. UI hardcoded hierarchy may drift from canonical config if one side updates first.
6. `tag_question_types.py` still emits legacy naming set; canonical naming layer not yet represented.
7. `tag_question_types.py` Part 1/Part 2 fallback semantics are inconsistent (`[]` vs `["description"]`).
8. `tag_time_frames.py` contains unused exclusion rules, indicating spec/implementation drift.
9. Legacy `tags` field still has at least one non-empty production record (mixed old metadata).
10. Flat-compatibility branches remain in runtime code, masking schema migration issues until late.

---

## Recommended Migration Order (only sequence, no code changes)

1. Freeze canonical vocabulary and alias policy (`experience/activity` -> `experience_activity` decision window).
2. Define authoritative hierarchy source generation path (config -> docs/UI/script artifacts).
3. Introduce explicit parent-binding strategy for `l3` under multi-`l2` topics (design decision first).
4. Align script output contract for `skill_tags` naming and fallback behavior.
5. Align UI hierarchy ingestion with canonical config (generated mapping target).
6. Replace cartesian export with primary-path + secondary-index export design.
7. Sunset legacy fields/workflows (`tags`, flat compatibility paths, legacy frame model) after read-only validation.

---

## Appendix

### A) Actual unique values

#### `content_tags.l1`
- `abstract_concepts`, `experience/activity`, `object`, `place`, `people`

#### `skill_tags`
- `analyze`, `comparison`, `description`, `evaluation`, `experience`, `frequency`, `hypothetical`, `preference`

#### `time_frame`
- `past`, `present`, `future`

#### `qualifier_tags`
- `interesting`, `memorable`, `peaceful`, `sentimental`, `useful`

### B) Suspicious overlaps / cross-parent co-occurrence

Top `l3` under multiple observed `l2`:
- `technology`: `intangible`, `tangible`
- `artwork`: `intangible`, `tangible`
- `media`: `intangible`, `tangible`
- `problem-solving`: `personal_traits`, `time`, `emotion`, `personal_growth`
- `regret`: `emotion`, `personal_growth`, `personal_traits`, `communication`
- `traveling`: `leisure`, `work`
- `shopping`: `leisure`, `work`

Qualifier overlap with taxonomy:
- qualifier vs `l2`: none
- qualifier vs `l3`: none

### C) Sample problematic records

1. Legacy `tags` residue:
- Topic: `something that you can’t live without (not a computer/phone)`
- Field: `"tags": ["事物类"]`
- File: `merged_part2.json`

2. Potential taxonomy drift examples:
- Topic: `a TV/online program you enjoy watching`
- `l2`: `["intangible","tangible"]`
- `l3`: `["media","technology"]`

- Topic: `a person who solved a problem in a smart way`
- `l2`: `["personal_traits","time"]`
- `l3`: `["problem-solving"]`

- Topic: `an exciting activity you have tried for the first time`
- `l2`: `["emotion","personal_growth","time"]`
- `l3`: `["adaptation","fear"]`

3. Question-type naming drift snapshot:
- Data still uses `description/evaluation/analyze`
- Canonical future names (`describe/evaluate/analysis`) not yet observed.

