# Pipeline V2 Design (Minimal Skeleton)

Status: additive prototype  
Scope: introduce a non-breaking v2 side-chain for taxonomy view + markdown export correctness  
Non-goal: this phase does not retrain classifiers, replace old scripts, or modify production JSON.

---

## 1) Goals

Pipeline v2 is **not** a classifier retraining effort in this phase.

Pipeline v2 first targets:

1. Primary path vs secondary tags separation
2. Explicit `l3 -> l2` binding (in derived view)
3. Markdown export topology correctness (no cartesian tree inflation)
4. Future controllability for answer-frame/content-frame integration

---

## 2) Core Principles

### A. Unique Primary Path

Each topic must have exactly one primary tree path in v2 view:

- `primary.l1`
- `primary.l2`
- `primary.l3` (nullable)

Primary path is used only for:

- tree navigation
- markdown hierarchy
- markmap
- primary statistical grouping
- future content-frame primary indexing

### B. Secondary Tags

Multi-tags remain allowed but separated from main tree:

- `secondary.l2[]`
- `secondary.l3[]`

Secondary tags are used only for:

- search
- association
- retrieval/recall
- similar-topic expansion
- candidate corpus reuse

### C. No Cartesian Tree Expansion

Secondary tags must never be expanded as primary tree branches.

Main markdown hierarchy must only use primary path.

### D. Explicit Parent Binding

V2 derived view must explicitly carry `l3 -> l2` binding records:

- each binding has `l2`, `l3`, `source`
- no more implicit parent inference from parallel `l2[]` and `l3[]` arrays only

---

## 3) Backward Compatibility Strategy

Current production data remains:

```json
"content_tags": { "l1": "...", "l2": [...], "l3": [...] }
```

This phase does **not** re-tag data.

V2 only creates a deterministic derived view from existing JSON:

- no overwrite of `merged_part1.json` / `merged_part2.json`
- no LLM usage
- no runtime replacement

---

## 4) Risk Statement

Current production schema does not store explicit `l3 -> l2` links.

Therefore, v2 in this phase is a **temporary compatibility inference view**, not final labeling truth.

A full resolution requires future tagger output redesign to emit explicit parent-bound structures directly.

---

## 5) V2 Data Contracts (New Outputs Only)

### 5.1 Taxonomy view outputs

- `human-in-the-loop/topic_taxonomy_view_v2_part1.json`
- `human-in-the-loop/topic_taxonomy_view_v2_part2.json`

Each topic entry includes:

- canonicalized `taxonomy_v2.primary`
- `taxonomy_v2.secondary`
- inferred `taxonomy_v2.bindings[]`
- `taxonomy_v2.diagnostics`

### 5.2 Markdown output

- `human-in-the-loop/topic_hierarchy_v2.md`

Main tree uses only primary path.
Secondary tags are emitted in a separate `Secondary Index` appendix.

---

## 6) Deterministic Inference Rules (Phase 1)

1. Normalize `l1` alias:
   - `experience/activity -> experience_activity`
2. Choose `primary.l2`:
   - first valid `l2` by configured priority order
3. Choose `primary.l3`:
   - first `l3` that belongs to selected `primary.l2`
   - if none, set `null`
4. Secondary:
   - legal non-primary `l2`/`l3`
5. Bindings:
   - single `l2`: bind all `l3` to that `l2`
   - multi `l2`: bind each `l3` by matching allowed parent set
   - ambiguous parent: prefer `primary.l2` if valid; otherwise mark diagnostics

---

## 7) Output Safety

- Old scripts untouched
- Old markdown exporter untouched
- Old UI untouched
- Production JSON untouched
- V2 scripts are additive and side-channel only

---

## 8) Run Order

```bash
python pipeline/build_topic_taxonomy_view_v2.py
python pipeline/generate_topic_hierarchy_markdown_v2.py
```

Generated artifacts:

- `human-in-the-loop/topic_taxonomy_view_v2_part1.json`
- `human-in-the-loop/topic_taxonomy_view_v2_part2.json`
- `human-in-the-loop/topic_hierarchy_v2.md`

