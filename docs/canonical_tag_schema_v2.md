# Canonical Tag Schema v2

Status: Draft (design baseline only, no runtime wiring yet)  
Scope: Defines the single canonical schema for all tagging dimensions.  
Non-goal: This file does **not** change current pipeline/UI behavior.

---

## 1) Official Dimensions (Canonical)

This project has exactly 4 formal tagging dimensions:

1. `content_tags` (topic taxonomy)
2. `skill_tags` (question type / answer-frame related)
3. `time_frame` (tense training dimension)
4. `qualifier_tags` (tone/quality modifiers, outside main taxonomy tree)

Any other tagging-like structures are considered legacy or experimental.

---

## 2) Responsibility Boundaries

### 2.1 `content_tags`
- Purpose: topic-level semantic navigation and topic filtering.
- Scope: topic object only.
- Structure:
  - `l1`: exactly one category (closed set)
  - `l2`: 1..3 thematic clusters (controlled set per `l1`)
  - `l3`: 0..2 specific tags (controlled set per `l2`)
- Non-scope:
  - Not for question task type classification
  - Not for tense classification
  - Not for sentiment/tone markers

### 2.2 `skill_tags`
- Purpose: classify question task type (answer-frame related).
- Scope: per question (`questions[]` and `part3[]` items).
- Non-scope:
  - Not a substitute for topic taxonomy
  - Not a topic-level field

### 2.3 `time_frame`
- Purpose: tense-training classification only.
- Scope: per question (single value).
- Closed set: `past | present | future`.
- Non-scope:
  - Must not be inferred from topic-level tags to overwrite question-level truth.

### 2.4 `qualifier_tags`
- Purpose: subjective tone/quality modifiers at topic level.
- Scope: topic object only.
- Design rule: separate channel from taxonomy tree.
- Non-scope:
  - Must not enter `content_tags.l3`.

---

## 3) Hard Non-Mixing Rules (MUST)

1. `qualifier_tags` MUST NOT be encoded as `content_tags.l2` or `content_tags.l3`.
2. `skill_tags` MUST NOT be used for topic grouping.
3. `time_frame` MUST remain question-level and MUST NOT be topic-derived overwrite.
4. Legacy `frame_angle` MUST NOT be treated as an official production dimension.
5. Experimental NLP keywords/sentiment signals MUST NOT be treated as production tags unless promoted by schema governance.

---

## 4) Canonical Field Model

### 4.1 Topic-level fields
- `content_tags`:
  - `l1: string`
  - `l2: string[]`
  - `l3: string[]`
- `qualifier_tags: string[]`

### 4.2 Question-level fields
- `skill_tags: string[]` (1..3 recommended)
- `time_frame: "past" | "present" | "future"`

---

## 5) First-Version Canonical Recommendations

### 5.1 `content_tags.l1`

Current compatible values in data/runtime:
- `people`
- `place`
- `object`
- `experience/activity`
- `abstract_concepts`

Recommended canonical naming (future-facing):
- `people`
- `place`
- `object`
- `experience_activity`   (normalized from `experience/activity`)
- `abstract_concepts`

Compatibility policy:
- Current slash form `experience/activity` remains accepted during migration window.
- Canonical config will define alias mapping to normalized underscore form.

### 5.2 `content_tags.l2` / `content_tags.l3`
- Keep existing taxonomy content as baseline (no forced relabel in this phase).
- Enforce hierarchy constraints:
  - `l2` must be valid children of chosen `l1`
  - `l3` must be valid children of selected `l2`
- Naming convention:
  - `snake_case` for multi-word tags
  - ASCII lower-case only
  - avoid punctuation except underscore

### 5.3 `skill_tags`

Current compatible values:
- `experience`
- `frequency`
- `description`
- `preference`
- `evaluation`
- `analyze`
- `comparison`
- `hypothetical`

Recommended canonical values (future-facing):
- `experience`
- `frequency`
- `describe`      (canonical target for `description`)
- `preference`
- `evaluate`      (canonical target for `evaluation`)
- `analysis`      (canonical target for `analyze`)
- `comparison`
- `hypothetical`

Compatibility policy:
- Existing values remain valid in current runtime.
- Canonical config defines alias map (`description -> describe`, `evaluation -> evaluate`, `analyze -> analysis`).

### 5.4 `time_frame`
- Canonical closed set:
  - `past`
  - `present`
  - `future`
- No alias expansion recommended in v2.

### 5.5 `qualifier_tags`

Current observed baseline:
- `memorable`
- `peaceful`
- `sentimental`
- `useful`
- `interesting`

Policy:
- Type: open-but-curated.
- Additions allowed only if all conditions hold:
  1. Adjective-like tone/quality descriptor (not topic content noun)
  2. Cross-topic reusable (not one-topic-specific)
  3. Not already representable by existing `content_tags`
  4. Approved through schema review

Disallowed additions:
- Domain nouns (e.g. `technology`, `policy`, `traveling`)
- Question task types (e.g. `analysis`, `comparison`)
- Time values (e.g. `past`, `future`)

---

## 6) Legacy / Experimental Status

### 6.1 Legacy (compatibility reference only)
- Flat `content_tags` arrays
- Legacy `category/substance/frame_angle`
- Generic `tags` field

These are not official dimensions in canonical v2.

### 6.2 Experimental (research only)
- NLP keyword extraction and adjective/sentiment candidate layers
- ConceptNet-assisted keyword relations

These are not production source-of-truth dimensions.

---

## 7) Source-of-Truth Policy

Canonical hierarchy:
1. `config/canonical_tag_schema_v2.yaml` = normative machine-readable source
2. `docs/canonical_tag_schema_v2.md` = normative human-readable source
3. Other docs/scripts = descriptive or implementation-specific projections

Policy intent:
- Runtime scripts should eventually read canonical config.
- UI hierarchy mappings should eventually be generated from canonical config.
- Hardcoded duplicates in scripts/UI should eventually be removed.

---

## 8) Conflict Matrix (Current -> Target Role)

### Canonical (target)
- `config/canonical_tag_schema_v2.yaml` -> canonical machine policy
- `docs/canonical_tag_schema_v2.md` -> canonical human specification

### Descriptive reference only (future)
- `docs/CLAUDE_tagging.md`
- `tags/tags.txt`

### Should eventually be generated from canonical config
- `js/components/sidebar.js` hierarchy maps (`L1_TO_L2`, `L2_TO_L3`)
- topic taxonomy rule tables currently embedded in `pipeline/tag_content_v2.py`

### Legacy compatibility only
- `pipeline/tag_content_topics.py` (flat array workflow)
- `pipeline/rewrite_content_tags.py` (historical migration)
- `pipeline/ingest_pipeline.py` legacy `frame_angle` model

### Experimental only
- `pipeline/extract_keywords.py`
- `pipeline/filter_*`
- `pipeline/query_conceptnet.py`

---

## 9) Migration Guardrails (No behavior change yet)

This schema file is intentionally non-invasive in phase 1:
- No JSON rewrite
- No pipeline rewrite
- No UI refactor
- No deletion of legacy files

It only establishes the canonical contract for later controlled migration.
