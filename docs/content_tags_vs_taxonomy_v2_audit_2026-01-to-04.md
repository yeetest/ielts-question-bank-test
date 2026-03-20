# Audit: `content_tags` vs `topic_taxonomy_v2_final` (Part 2)

**Quarter:** `data/quarters/2026-01-to-04/`  
**Sources:** `merged_part2.json` × `topic_taxonomy_v2_final.json`  
**Generated:** automated scan (see methodology below).

## Methodology

- **Part 2 topics:** every object in `merged_part2.json` with `"part": 2`.
- **Join key:** `merged_part2[].topic` trimmed ↔ `topic_taxonomy_v2_final.json[].topic` trimmed (same as runtime `js/data.js`).
- **L1 compare:** normalize `experience/activity` → `experience_activity` on both sides.
- **L2 / L3 compare:** taxonomy row has at most one `l2` and one `l3` (primary path). Treat as **consistent** only if that value appears in the corresponding **`content_tags` array** (`l2` list / `l3` list). Empty taxonomy `l2`/`l3` does not fail the layer.
- **Fully consistent:** no failing layer (L1 equal, and non-empty tax l2/l3 ⊆ content_tags arrays).

> Note: `content_tags` often lists **multiple** l2/l3; taxonomy stores a **single** primary. Mismatch here means the chosen primary is **not** among the topic’s declared l2/l3 in JSON.

### Caveats

- **String normalization:** This scan does **not** fold hyphen vs underscore (e.g. `self-improvement` in `content_tags.l3` vs `self_improvement` in taxonomy). A small number of **L3** flags may be **alias noise**, not semantic disagreement.
- **Empty `content_tags.l3`:** If `l3` is `[]` but taxonomy assigns an `l3`, that counts as **L3 mismatch** (taxonomy asserts a leaf tag the merged JSON did not list).

## Summary

| Metric | Count |
|--------|-------|
| Total Part 2 topics | 59 |
| Fully consistent | 21 |
| Inconsistent (layer mismatch) | 38 |
| Missing taxonomy row | 0 |

**Mismatch signature (among inconsistent rows only):**
- `L3`: 37 topic(s)
- `L1+L2+L3`: 1 topic(s)

- Orphan taxonomy rows (in JSON but not a Part 2 `topic` in merged_part2): **44** (Part 1 titles, etc.)

## Interpretation

- **Systemic:** ~**64%** of Part 2 topics (38/59) fail the strict “primary ⊆ content_tags” test; **37/38** are **L3-only** (taxonomy primary L3 not listed under `content_tags.l3`).
- **Local / one-off:** **1** topic fails **L1+L2+L3** simultaneously (see table).

## Recommendation (for humans; no code change in this audit)

1. **Default to `content_tags` as display + filter source of truth** unless you explicitly want a *different* primary for navigation than what editors stored in merged JSON.
2. **Why:** Cards, modal inline tags, and `renderContentTags` already use `content_tags`; sidebar currently prefers `taxonomy_v2_primary`, which **often points at an L3 not present in `content_tags.l3`** — that is exactly the user-visible split-brain.
3. **When to prefer taxonomy file:** If you intentionally maintain a **curated primary path** (e.g. after `assign_primary_l3` pipeline) and plan to **backfill or replace** `content_tags` to match, then keep taxonomy as master **only after** merging that primary into `content_tags` (or stop using taxonomy for filter until aligned).

## Inconsistent topics (detail)

| topic | content_tags (l1 / l2 / l3) | taxonomy (l1 / l2 / l3) | mismatch |
|-------|------------------------------|-------------------------|----------|
| a bicycle/motorcycle/car trip you would like to take | `object` / ['tangible'] / [] | `object` / `tangible` / `transport_item` | L3 |
| a book you read that you found useful | `object` / ['intangible'] / ['artwork', 'technology'] | `object` / `intangible` / `book_or_reading_material` | L3 |
| a child who loves drawing/painting | `object` / ['intangible', 'tangible'] / ['artwork'] | `object` / `intangible` / `book_or_reading_material` | L3 |
| a city that you have been to and would like to visit again | `place` / ['outdoor'] / [] | `place` / `outdoor` / `city_space` | L3 |
| a famous person you would like to meet | `people` / ['professions'] / [] | `people` / `professions` / `public_figure` | L3 |
| a good friend who is important to you | `people` / ['close_bonds'] / [] | `people` / `close_bonds` / `friendship` | L3 |
| a great dinner you and your friend or family members enjoyed | `people` / ['close_bonds'] / [] | `people` / `close_bonds` / `family_activity` | L3 |
| a habit your friend has and you want to develop | `abstract_concepts` / ['personal_growth'] / ['self-improvement'] | `abstract_concepts` / `personal_growth` / `self_improvement` | L3 |
| a long journey you had and would like to take again | `experience_activity` / ['leisure'] / ['traveling'] | `experience_activity` / `leisure` / `travel` | L3 |
| a movie you watched and enjoyed recently | `object` / ['intangible', 'tangible'] / ['artwork'] | `object` / `intangible` / `media` | L3 |
| a natural place (e.g. park, mountain) | `place` / ['outdoor'] / [] | `place` / `outdoor` / `nature_place` | L3 |
| a perfect job you would like to have in the future | `experience_activity` / ['work'] / [] | `experience_activity` / `work` / `job_role` | L3 |
| a person who makes plans a lot and is good at planning | `people` / ['close_bonds', 'professions'] / [] | `abstract_concepts` / `personal_traits` / `planning_orientation` | L1,L2,L3 |
| a person who often helps others | `people` / ['close_bonds', 'professions'] / [] | `people` / `close_bonds` / `supportive_relationship` | L3 |
| a person who solved a problem in a smart way | `abstract_concepts` / ['personal_traits', 'time'] / ['problem-solving'] | `abstract_concepts` / `personal_traits` / `confidence` | L3 |
| a quiet place you like to go | `place` / ['outdoor'] / [] | `place` / `outdoor` / `nature_place` | L3 |
| a short-term job you want to have in a foreign country | `experience_activity` / ['leisure', 'work'] / ['traveling'] | `experience_activity` / `work` / `job_role` | L3 |
| a sportsperson you admire | `people` / ['professions'] / [] | `people` / `professions` / `sportsperson` | L3 |
| a successful sportsperson you admire | `people` / ['professions'] / [] | `people` / `professions` / `sportsperson` | L3 |
| a time when someone apologized to you | `abstract_concepts` / ['communication', 'emotion'] / ['regret'] | `abstract_concepts` / `communication` / `apology_repair` | L3 |
| a time when you broke something | `abstract_concepts` / ['emotion', 'personal_growth', 'personal_traits'] / ['problem-solving', 'regret'] | `abstract_concepts` / `personal_growth` / `problem_solving` | L3 |
| a time when you encouraged someone to do something that he/she didn't want to do | `abstract_concepts` / ['communication', 'influence'] / [] | `abstract_concepts` / `communication` / `encouragement` | L3 |
| a time when you felt proud of a family member | `people` / ['close_bonds'] / [] | `people` / `close_bonds` / `family_pride_moment` | L3 |
| a time when you gave advice to others | `abstract_concepts` / ['communication'] / [] | `abstract_concepts` / `communication` / `advice_support` | L3 |
| a time when you lost your way | `experience_activity` / ['leisure'] / ['traveling'] | `experience_activity` / `leisure` / `travel` | L3 |
| a time when you received good service in a shop/store | `place` / ['indoor'] / [] | `place` / `indoor` / `shopping_venue` | L3 |
| a time you saw something interesting on social media | `object` / ['intangible'] / ['technology'] | `object` / `intangible` / `media` | L3 |
| a toy you liked in your childhood | `abstract_concepts` / ['time'] / [] | `abstract_concepts` / `time` / `childhood` | L3 |
| a wild animal that you want to know more about | `abstract_concepts` / ['values'] / ['environment'] | `abstract_concepts` / `values` / `animal_welfare` | L3 |
| an area/subject of science (biology,robotics, etc.) that you are interested in and would like to learn more about | `experience_activity` / ['study'] / [] | `experience_activity` / `study` / `study_subject` | L3 |
| an event you attended in which you didn't enjoy the music played | `abstract_concepts` / ['emotion', 'personal_growth'] / ['anger', 'learning'] | `abstract_concepts` / `emotion` / `happiness` | L3 |
| an important decision made with the help of other people | `abstract_concepts` / ['personal_growth'] / ['decision'] | `abstract_concepts` / `personal_growth` / `decision_making` | L3 |
| an interesting building | `place` / ['indoor', 'outdoor'] / [] | `place` / `indoor` / `building` | L3 |
| an interesting traditional story | `object` / ['intangible'] / ['artwork'] | `object` / `intangible` / `book_or_reading_material` | L3 |
| an occasion when you lost your way | `experience_activity` / ['leisure'] / ['traveling'] | `experience_activity` / `leisure` / `travel` | L3 |
| one of your friends who learned something without a teacher | `abstract_concepts` / ['emotion', 'personal_growth'] / ['happiness', 'learning'] | `abstract_concepts` / `personal_growth` / `learning_growth` | L3 |
| something important that has been kept in your family for a long time | `people` / ['close_bonds'] / [] | `people` / `close_bonds` / `family_memory` | L3 |
| the time when you first talked with others in a foreign language | `abstract_concepts` / ['communication', 'personal_growth'] / ['self-improvement'] | `abstract_concepts` / `communication` / `foreign_language_communication` | L3 |

## Orphan taxonomy topics (first 20)

- `Advertisement`
- `Borrowing/ Lending`
- `Building`
- `Chatting`
- `Chatting/Conversation`
- `Childhood activities`
- `Crowded place`
- `Daily routine`
- `Day off`
- `Doing something well`
- `Dreams`
- `Food`
- `Gifts`
- `Going out`
- `Growing vegetables/ fruits`
- `Happy things`
- `Having a break`
- `Hobby`
- `Home/Accommodation`
- `Hometown`
- … and 24 more