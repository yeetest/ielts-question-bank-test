# `people` vs `personal_traits` vs `work/study/activity` (Part 2)

Operational rules for **`content_tags`** and the assign → backfill → export → check loop.

---

## What `people` (L1) is for

Use **`people`** when the cue is mainly about **who someone is in a social or role sense**:

- **Relationship / bond**: friend, family member, someone important to you, someone you know well  
- **Public / professional identity**: famous person, sportsperson, teacher, someone in a job role  
- **Pure-identity "someone you know"** where the cue card focuses on the **person themselves** (who they are, why you admire them, what they're like)

The candidate still *describes* a person, but the **exam focus** is relationship, identity, or role in a network.

## What `personal_traits` (L2 under `abstract_concepts`) is for

Use **`abstract_concepts`** with **`personal_traits`** when the cue is mainly **disposition, habit, ability, or behavioural style**:

- Helping behaviour, kindness, reliability  
- Planning / organisation / discipline as a **trait**  
- Cleverness / creativity in solving problems **as a character quality** (not a generic "event" card)

The grammatical subject may still be "a person who …", but the **scoring construct** is the **trait or tendency**, not "describe your relationship with X".

## What `experience/activity` (L1) is for — the work/study boundary

Use **`experience/activity`** (L2 `work` or `study`) when the cue's grammatical subject is "a person" but the **core exam content is the work/study/activity itself**:

- **Work context**: "a person you know who enjoys **working for** a family business" — cue card bullets ask about the business, the job, why they enjoy working there  
- **Study context**: "a person you know who **studies** at …" — cue card bullets focus on what they study, their learning experience  
- **Activity context**: "a person you know who **runs** a community project" — cue card focuses on the project, not the person's identity

**Key test**: if ≥50% of cue-card bullets ask about the **activity/workplace/study setting** rather than "who is this person", the topic belongs under `experience/activity`, not `people`.

### Examples

| Topic | L1 | Reasoning |
|-------|-----|-----------|
| a sportsperson you admire | `people` | focus is on who they are, their achievements, why you admire them |
| a famous person you'd like to meet | `people` | focus is on the person's identity and your interest |
| a person you know who enjoys working for a family business | `experience/activity` | focus is on the business, the job, the work experience |
| a person who often helps others | `abstract_concepts` | focus is on the trait of helpfulness |

---

## `a person who …` — decision order

1. **Work/activity remap** (runs first in `remap_content_tags_disposition.py`):
   - Title matches `^a person.*who [work/study verb] for/at/in [work context noun]`
   - Exclude pure identity cues (famous, sportsperson, teacher, admire, etc.)
   - If matched → `experience/activity` > `work` (or `study`)

2. **Exclude** from auto-trait remap (keep **`people`** or other L1):  
   - Title contains: **`you know`** (without work/study signals), **`friend`**, **`family`** (relationship sense), **`famous`**, **`sportsperson`**, **`teacher`**, **`older than`**, **`younger`**, **`important to you`**, **`natural world`**, **`admire`**, **`child who`**

3. **Trait remap**: if title matches **`^a person who `** and the remainder matches **trait / disposition** patterns → `abstract_concepts` > `personal_traits`

4. Otherwise keep existing tags unless another documented remap applies.

---

## Where this is enforced

| Layer | Role |
|--------|------|
| **`pipeline/remap_content_tags_disposition.py`** | **Source of truth for batch correction** of mis-tags on quarter `merged_part2.json`. Handles: (a) `people` → `experience/activity > work` for work-context cues, (b) `people` → `abstract_concepts > personal_traits` for trait-disposition cues, (c) problem-solver canonical fix. Run after ingest / auto-tag, **before** assign. |
| **`assign_primary_l3_v2.py`** | Chooses primary L3 **only inside** `content_tags.l2` under `content_tags.l1`; adds light title-based hints for trait wording when `personal_traits` is in play. |
| **backfill / export / check** | Propagate and validate; they **do not** invent L1 boundaries — fix **`content_tags` first**. |

---

## Topic dedup and modifier variants

Near-duplicate Part 2 topics (e.g. "a sportsperson you admire" vs "a successful sportsperson you admire") must be merged **before** taxonomy remap and assign. The dedup script (`pipeline/dedup_topics_part2.py`) uses:

1. **Base fingerprint**: normalizes place suffixes, watch-verb variants, slashes, etc.
2. **Aggressive fingerprint**: additionally strips modifier adjectives (`successful`, `well-known`, `popular`, `favourite`), normalizes temporal phrases (`an occasion` → `a time`), and removes role-noun prepositional phrases (`from a staff member`). When aggressive fingerprints score ≥90 via fuzz.ratio, the pair gets a boosted similarity score (capped at 97).
3. **Keep-best (survivor)**: more Part 3 questions → more bullets → richer tags → has season → higher source tier → shorter title.

---

## Season rollover checklist

After placing new `merged_part2.json`, run (see `docs/season_rollover_runbook.md`):

1. **`dedup_topics_part2.py --quarter <id>`** (removes duplicate topic rows including modifier variants)
2. **`dedup_questions.py`** + **`renumber_questions.py`** on the same file
3. **`remap_content_tags_disposition.py --quarter <id>`** (fixes people vs work/study/activity and people vs personal_traits)
4. assign → backfill → export → check `--strict`

**Post-pipeline spot-checks:**
- Part 2 cards titled `a person who …` are under the correct L1 (people vs work vs traits)
- No modifier-variant near-duplicates remain (run dedup with `--dry-run` to verify)
