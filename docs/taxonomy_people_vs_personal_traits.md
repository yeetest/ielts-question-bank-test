# `people` vs `abstract_concepts` → `personal_traits` (Part 2)

Operational rules for **`content_tags`** and the assign → backfill → export → check loop.

## What `people` (L1) is for

Use **`people`** when the cue is mainly about **who someone is in a social or role sense**:

- **Relationship / bond**: friend, family member, someone important to you, someone you know well  
- **Public / professional identity**: famous person, sportsperson, teacher, someone in a job role  
- **Situational “someone you know”** with **work / family business / study** context (the story is the relationship + setting)

The candidate still *describes* a person, but the **exam focus** is relationship, identity, or role in a network.

## What `personal_traits` (L2 under `abstract_concepts`) is for

Use **`abstract_concepts`** with **`personal_traits`** when the cue is mainly **disposition, habit, ability, or behavioural style**:

- Helping behaviour, kindness, reliability  
- Planning / organisation / discipline as a **trait**  
- Cleverness / creativity in solving problems **as a character quality** (not a generic “event” card)

The grammatical subject may still be “a person who …”, but the **scoring construct** is the **trait or tendency**, not “describe your relationship with X”.

## `a person who …` — decision order

1. **Exclude** from auto-trait remap (keep **`people`** or other L1, fix only if obviously mis-tagged elsewhere):  
   - Title contains: **`you know`**, **`friend`**, **`family`**, **`famous`**, **`sportsperson`**, **`teacher`**, **`older than`**, **`younger`**, **`important to you`**, **`natural world`**, **`admire`** (public figure / athlete cues), **`child who`** (different template).

2. **If** title matches **`^a person who `** (case-insensitive) **and** the remainder matches **trait / disposition** patterns (see `pipeline/remap_content_tags_disposition.py`), set:  
   - `l1`: **`abstract_concepts`**  
   - `l2`: **`["personal_traits"]`** (optionally union with other L2 later if needed)  
   - `l3`: inferred canonical token (**`kindness`**, **`discipline`**). For **“solved a problem in a smart way”**, `remap_content_tags_disposition.py` sets `l2` to **`personal_traits` + `personal_growth`** and `l3` to **`problem_solving`** (canonical underscore); assign may choose primary **`problem_solving`** (bucket `personal_growth`) — still under **`abstract_concepts`**, not `people`.

3. Otherwise keep existing tags unless another documented remap applies.

## Where this is enforced

| Layer | Role |
|--------|------|
| **`pipeline/remap_content_tags_disposition.py`** | **Source of truth for batch correction** of known mis-tags on quarter `merged_part2.json`. Run after ingest / auto-tag, **before** assign. |
| **`assign_primary_l3_v2.py`** | Chooses primary L3 **only inside** `content_tags.l2` under `content_tags.l1`; adds light title-based hints for trait wording when `personal_traits` is in play. |
| **backfill / export / check** | Propagate and validate; they **do not** invent `people` vs `personal_traits` — fix **`content_tags` first**. |

## Season rollover

After placing new `merged_part2.json`, run (see `docs/season_rollover_runbook.md`):

1. Topic dedup scripts if needed  
2. **`python3 pipeline/remap_content_tags_disposition.py --quarter <id> [--dry-run]`**  
3. assign → backfill → export → check `--strict`  

Spot-check Part 2 cards whose titles are **`a person who …`** but are **not** relationship/famous/job cues.
