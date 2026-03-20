# Taxonomy Calibration Notes v2 (Refined Pass)

## Scope and Constraints
- Targeted calibration pass only.
- No changes to old production files.
- No new dimensions added.
- All outputs are additive `_refined` artifacts.

## Targeted Taxonomy Refinements

### 1) `people > general`
- Replaced weak/fragment labels with:
  - `elderly_people`
  - `intergenerational_contact`
  - `social_support`
  - `aging_experience`
  - `older_generation`
- Removed prompt-like forms such as `old`, `staying`, and comparative fragments.

### 2) `people > professions`
- Consolidated to role-based semantic labels:
  - `sportsperson`
  - `public_figure`
  - `admired_professional`
  - `achievement`
  - `professional_role`
- Removed pronoun/fragment-like or over-specific forms.

### 3) `experience_activity > work`
- Locked to work-domain concepts:
  - `job_role`
  - `workplace_experience`
  - `career_planning`
  - `professional_growth`
  - `service_experience`
  - `work_life_balance`
- Removed vague life-stage drift labels.

### 4) `experience_activity > study`
- Kept only stable study concepts:
  - `study_subject`
  - `learning_method`
  - `self_study`
  - `academic_interest`
  - `exam_preparation`
  - `language_learning`

### 5) `object > intangible`
- Refined toward informational/digital intangible objects:
  - `technology`
  - `media`
  - `money`
  - `book_or_reading_material`
  - `digital_service`
  - `information_resource`
- Removed `artwork` from this bucket to reduce ambiguity for reading/useful-book topics.

### 6) `place > indoor`
- Normalized indoor place vocabulary:
  - `home`
  - `accommodation`
  - `building`
  - `museum`
  - `shopping_venue`
  - `workplace`
- Reduced near-duplicate building variants.

### 7) Emotion and Personal Growth Guardrails
- `abstract_concepts > emotion` keeps core emotional labels and adds `frustration`.
- `abstract_concepts > personal_growth` remains focused on growth/process labels, including `problem_solving`.
- This separation supports better disambiguation for breakage/problem narratives.

## Cross-Bucket Duplication Reduction
- Removed `childhood` from `people > close_bonds` to reduce overlap with `abstract_concepts > time`.
- Added `family_memory` to preserve family-history semantics without duplicating time labels.

## Refined Assignment Logic Changes

### A) Deterministic Tie-Break Priority
When score gaps are tiny, ranking resolves by:
1. exact concept match in title
2. cue-card prompt support
3. part3 support
4. old `content_tags.l3` overlap
5. bucket-specific priority table

### B) Bucket-Sensitive Calibration
- Book/useful topics favor `book_or_reading_material` over artistic interpretation.
- Breakage topics favor `problem_solving` when repair/fix language is present; `regret` requires explicit regret/apology signals.
- Family-kept-important topics favor `family_bond`/`family_memory` over generic activity framing.
- Work topics default toward `job_role`/`workplace_experience`; `work_life_balance` requires explicit balance language.
- Intergenerational topics prefer `intergenerational_contact` when contact/interaction wording dominates.

### C) Deterministic Fallbacks for Previous Unassigned Topics
- Added explicit, non-random fallback mappings for previously unassigned titles.
- Fallback outputs are tagged in diagnostics for auditability.

## Output Artifacts
- `config/topic_taxonomy_v2_curated_refined.yaml`
- `pipeline/assign_primary_l3_v2_refined.py`
- `human-in-the-loop/topic_taxonomy_assignment_v2_refined_part1.json`
- `human-in-the-loop/topic_taxonomy_assignment_v2_refined_part2.json`
- `human-in-the-loop/l3_assignment_diagnostics_v2_refined.md`
