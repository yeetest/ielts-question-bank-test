# Taxonomy structural rules

Rules for maintaining the 3-level hierarchy defined in `config/topic_taxonomy_v2_curated.yaml`.

## Hierarchy invariants

| Rule | Scope | Enforcement |
|------|-------|-------------|
| **One home per L3** | Each L3 tag appears under exactly one `(L1, L2)` parent. | `audit_taxonomy_structure.py` — `DUAL_HOME` / `CROSS_L1` (ERROR) |
| **No L2–L3 name collision** | An L3 tag must not share a name with any L2 bucket. | `audit_taxonomy_structure.py` — `NAME_COLLISION` (ERROR) |
| **L3 specificity** | L3 names should represent concrete, narrow concepts — not broad themes that overlap with L2. | `audit_taxonomy_structure.py` — `BROAD_L3` (WARNING) |
| **Canonical format** | L3 tags in `content_tags.l3` use underscores, not hyphens. | `audit_taxonomy_structure.py` — `LEGACY_FORMAT` (INFO); `LEGACY_CONTENT_L3_TO_CURATED` in assign/backfill scripts |
| **Content L3 ⊆ YAML** | Every L3 value in `content_tags.l3` must exist in the YAML taxonomy. | `audit_taxonomy_structure.py` — `ORPHAN_CONTENT_L3` (WARNING) |

## Dual-home exceptions

Default: forbidden. If a concept genuinely belongs to two L2 buckets, it must be added to `DUAL_HOME_WHITELIST` in `pipeline/audit_taxonomy_structure.py` with explicit human approval. Currently the whitelist is empty — all L3 tags have exactly one home.

## Naming conventions

Avoid these patterns in L3 names (they suggest L2-level breadth):
- `*_experience` — too broad, describe a specific aspect instead (e.g. `customer_service` not `service_experience`)
- `*_activity` — too broad, use the specific activity (e.g. `family_gathering` not `family_activity`)
- `*_growth` — too broad, specify the type (e.g. `life_lesson` not `learning_growth`, `career_development` not `professional_growth`)
- `*_time` — too broad if it overlaps with an L2 bucket (e.g. `leisure_time` under `routines` was removed; topic uses `hobby` under `leisure`)

## L3 renames applied (2026-03-20)

| Old L3 | New L3 | Parent L2 | Reason |
|--------|--------|-----------|--------|
| `leisure_time` | *(removed)* | was `routines` | semantic mismatch; topic "Spare time" reassigned to `leisure > hobby` |
| `learning_growth` | `life_lesson` | `personal_growth` | overly broad, overlaps L2 concept |
| `family_activity` | `family_gathering` | `close_bonds` | overly broad |
| `workplace_experience` | `work_environment` | `work` | overly broad |
| `professional_growth` | `career_development` | `work` | overly broad, overlaps L2 concept |
| `service_experience` | `customer_service` | `work` | overly broad |

## Dual-home removals (2026-03-20)

| L3 | Removed from | Kept in | Reason |
|----|-------------|---------|--------|
| `childhood` | `people > close_bonds` | `abstract_concepts > time` | one-home rule; topics use `abstract_concepts` |
| `memory_reflection` | `experience_activity > routines` | `abstract_concepts > time` | one-home rule; semantic fit is time/reflection |
| `responsibility` | `abstract_concepts > personal_traits` | `abstract_concepts > values` | one-home rule; responsibility is a social/moral value |

## When to run the audit

Run `pipeline/audit_taxonomy_structure.py --quarter <id> --strict` after any of:
- Editing `config/topic_taxonomy_v2_curated.yaml`
- Running `backfill_content_tags_l3_from_assignment.py`
- Ingesting new topics with new L3 tags
- Season rollover / new quarter setup

The `--strict` flag causes exit code 1 on any ERROR finding, suitable for CI/pre-commit checks.

## Common mis-classification patterns

Watch for these when reviewing `content_tags`:

| Pattern | Symptom | Correct action |
|---------|---------|----------------|
| Title contains "family" → tagged `people > close_bonds` | Topic is about an *object* kept in the family (heirloom, item) | Reclassify to `object > tangible > personal_item` |
| Title starts "a person who..." | May be about work/study/activity, not the person | Check cue card bullets: if "what it is" / "how it works" → object; if work context → `experience/activity > work` |
| Title mentions a role (teacher, worker) | May be about the profession/activity | Check if Part 3 asks about the person or the profession/field |

**Rule of thumb:** Read the cue card `you_should_say` bullets. If 2+ bullets ask about an object ("What it is", "How you got it"), the topic is about the object, not the person/family.
