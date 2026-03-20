# Taxonomy v2.0 Freeze Notes

## Freeze Status
- Taxonomy v2.0 is frozen.
- No further taxonomy redesign is in scope after this point.
- Canonical source remains fixed unless a new controlled versioning cycle is opened.

## Final Statistics
- total topics: 103
- assigned L3: 103
- unassigned: 0
- low-confidence: 1

## Final L1 Buckets
- `abstract_concepts`
- `experience_activity`
- `object`
- `people`
- `place`

## All L2 Buckets

### abstract_concepts
- `communication`
- `emotion`
- `personal_growth`
- `personal_traits`
- `time`
- `values`
- `influence`

### experience_activity
- `leisure`
- `routines`
- `study`
- `work`

### object
- `intangible`
- `tangible`

### people
- `close_bonds`
- `professions`
- `general`

### place
- `indoor`
- `outdoor`

## personal_traits Clarification

### planning_orientation
- Meaning: planner vs spontaneous personality orientation.
- Use case: whether a person tends to plan ahead or acts more spontaneously.
- Typical signals: planning habits, structure preference, advance preparation style.

### discipline
- Meaning: self-control, persistence, and ability to maintain habits.
- Use case: consistency, effort sustainability, sticking to routines or goals over time.
- Typical signals: perseverance, routine adherence, delayed gratification.

### Distinction Summary
- `planning_orientation` captures *style preference* (planner vs spontaneous).
- `discipline` captures *execution strength* (self-control and persistence).

## Canonical Taxonomy File
- `config/topic_taxonomy_v2_curated_final.yaml`

## Final Assignment Outputs
- `human-in-the-loop/topic_taxonomy_assignment_v2_final_part1.json`
- `human-in-the-loop/topic_taxonomy_assignment_v2_final_part2.json`

## Final Diagnostics File
- `human-in-the-loop/l3_assignment_diagnostics_v2_final.md`

## Freeze Baseline and Governance
- This freeze document captures v2.0 baseline semantics and artifact references.
- Any future updates should be managed as a new versioned calibration cycle with explicit migration notes.
