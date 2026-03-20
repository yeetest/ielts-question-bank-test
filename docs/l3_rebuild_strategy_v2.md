# L3 Rebuild Strategy v2 (Bottom-Up Candidate Layer)

## Why `primary.l3 = null` Is the Main Signal
- The v2 primary path already stabilizes `l1` and `l2`, so null `primary.l3` is the highest-value gap signal.
- A null at `primary.l3` means tree navigation exists, but concept specificity is missing.
- This makes null-rate the best measurable target for L3 rebuild progress.

## Why L3 Must Be Rebuilt Bottom-Up
- Current top-down L3 coverage is incomplete and inconsistent across `l2` buckets.
- Rebuilding from real topic titles and question text captures actual teaching content instead of abstract taxonomy guesses.
- Bottom-up mining supports reusable, high-frequency concepts while preserving rare but valid niche concepts via review.

## Why L1/L2 Stays Stable During Rebuild
- `l1`/`l2` already function as the navigation skeleton and should not be churned during L3 reconstruction.
- Keeping the upper skeleton fixed isolates change risk to L3 vocabulary only.
- This allows iterative L3 expansion without breaking existing primary-path usability.

## Human-in-the-Loop Candidate Generation Layer
- This step creates candidate proposals only; it does not auto-rewrite canonical taxonomy or topic assignments.
- Candidate generation prioritizes topics where `taxonomy_v2.primary.l3` is null.
- Outputs are grouped by `l1 > l2` to support controlled vocabulary review at the right abstraction level.

## Governance Rule
- Human approves vocabulary.
- Machine applies approved vocabulary.
- Only low-confidence or unseen concepts go to review.

## Confidence and Escalation Policy
- High-confidence candidates: supported by multiple topics and clean semantic labels.
- Medium-confidence candidates: supported but potentially broad or cross-domain.
- Low-confidence candidates: sparse, noisy, or fallback-derived labels.
- Review flow should prioritize low-confidence and unseen labels before any application step.

## Normalization Rules for Candidate Labels
- Prefer short reusable semantic labels, not raw question fragments.
- Use `snake_case`, lower-case ASCII.
- Keep singular/plural consistent when possible.
- Exclude skill/time terms and qualifier-only adjectives unless clearly concept-bearing.

## Source Evidence Policy
- Candidate evidence should track whether each label comes from:
  - existing L3 reuse
  - topic title extraction
  - question text extraction
  - heuristic fallback
- Each candidate should retain representative topic and question evidence for auditability.

## Future Reuse: Answer-Frame and Content-Frame
- A cleaner L3 layer improves content-frame retrieval (topic semantics).
- Stable content semantics can later be combined with question-level `skill_tags` and `time_frame` (answer-frame dimensions).
- This separation supports cross-topic practice generation without mixing taxonomy and task-type dimensions.

## Non-Goals for This Step
- No overwrite of `config/topic_taxonomy_v2.yaml`.
- No global auto-assignment of final L3 to all topics.
- No UI changes.
- No modification of old production pipeline behavior.
