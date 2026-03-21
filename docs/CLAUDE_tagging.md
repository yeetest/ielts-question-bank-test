# Tagging Rules — IELTS Part 1 & Part 2

This file is the permanent reference for how to tag topics and questions in `merged_part1.json` and `merged_part2.json`.
Follow it exactly for all current and future question banks.

**Where those files live for the live site:** under `data/quarters/<quarter-id>/` (e.g. frozen `2026-01-to-04`, editable placeholder `2026-05-to-08`). Root `merged_part*.json` may still exist as legacy copies — tagging rules are the same regardless of path.

---

## Content Tags (`content_tags`) — 3-Layer System

A structured JSON object with 3 layers. Full hierarchy in `tags/tags.txt`.

```json
"content_tags": {"l1": "experience/activity", "l2": ["leisure"], "l3": ["exercise"]}
"content_tags": {"l1": "abstract_concepts", "l2": ["emotion", "personal_growth"], "l3": ["happiness", "learning"]}
"content_tags": {"l1": "object", "l2": ["intangible"], "l3": ["technology"]}
```

- **l1** — exactly one of 5 fixed categories
- **l2** — 1–3 thematic clusters (must belong to the selected l1)
- **l3** — 0–2 specific tags (must belong to one of the selected l2s)

Qualifier tags (`qualifier_tags`) are stored separately: `memorable` | `peaceful` | `sentimental` | `useful` | `interesting`

---

## Layer 1 — Category (l1)

Exactly one of:

| Value | Use when the topic is about… |
|---|---|
| `people` | A person or group — friends, family, celebrities, strangers, a child, a colleague |
| `place` | A location — indoor or outdoor: building, park, mountain, room, church, lake |
| `object` | A tangible or intangible *thing* — book, film, technology, app, food, toy, gift |
| `experience/activity` | Something that happened or is done — event, travel, habit, routine, work, study |
| `abstract_concepts` | Ideas, emotions, values, traits — communication, pride, fairness, influence, time |

**When in doubt:** if the main noun is a thing → `object`. If it describes an event or "a time when" → `experience/activity`. If it centres on a person → `people`. If it centres on a location → `place`. If it's about ideas, feelings, traits, or values → `abstract_concepts`.

---

## Layer 2 — Theme (l2)

Each l2 belongs to exactly one l1. Pick 1–3 l2 tags.

### people
- `professions` — doctors, actors, athletes, leaders, famous persons
- `close_bonds` — family, friends, colleagues, neighbours
- `general` — society, citizens, crowd, generation, strangers

### place
- `outdoor` — nature, scenery, parks, mountains, cities, countries
- `indoor` — houses, buildings, museums, libraries, shops, schools

### object
- `tangible` — food, clothes, shoes, gifts, toys, cameras, instruments, plants
- `intangible` — non-physical objects (apps, books, music, money, media)

### experience/activity
- `work` — jobs, careers, business, companies, employment
- `study` — courses, subjects, education, language learning, exams
- `leisure` — free time activities (has L3 children)
- `routines` — daily habits, chores, morning/bedtime, schedule

### abstract_concepts
- `communication` — advice, arguing, chatting, speaking, apologizing
- `emotion` — feelings and emotional states (has L3 children)
- `personal_traits` — personal attributes, abilities, moral qualities (has L3 children)
- `values` — social/cultural norms and systems (has L3 children)
- `personal_growth` — development and self-improvement (has L3 children)
- `influence` — persuasion, inspiration, encouragement, impact
- `time` — life stages, generations, childhood, past vs present

---

## Layer 3 — Specific (l3)

Each l3 belongs to exactly one l2. Pick 0–2 l3 tags.

### Under `intangible` (object)
- `artwork` — books, music, movies, paintings, photographs
- `technology` — apps, computers, phones, internet, social media
- `money` — cash, fees, salary, prices, spending
- `media` — advertisements, news, TV programs, reports

### Under `leisure` (experience/activity)
- `exercise` — sports, games, walking, cycling, team activities
- `shopping` — buying, stores, malls, markets
- `cooking` — food prep, meals, restaurants, eating out
- `traveling` — journeys, trips, visits, tourism, transport
- `creative` — drawing, painting, photography, crafting
- `reading` — books, articles, e-books, libraries (leisure context)
- `entertainment` — movies, music, concerts, shows, games (consuming)

### Under `emotion` (abstract_concepts)
- `pride` — proud, accomplishment, achievement
- `happiness` — joy, smiling, enjoyment, fun
- `fear` — worry, anxiety, danger, reluctance
- `anger` — arguing, frustration, conflict
- `attachment` — missing, nostalgia, sentimental, keeping old things
- `regret` — sorry, apologize, mistake
- `patience` — waiting, tolerance, delayed gratification

### Under `personal_traits` (abstract_concepts)
- `creativity` — artistic ability, innovation, imagination
- `problem-solving` — finding solutions, fixing issues
- `craftsmanship` — making by hand, quality of handmade work
- `responsibility` — duty, accountability, ownership
- `honesty` — truthfulness, sincerity, authenticity

### Under `values` (abstract_concepts)
- `policy` — laws, government rules, regulations, bans
- `environment` — conservation, pollution, green choices, wildlife
- `economics` — spending, consumption, economic growth
- `fairness` — equality, justice, access, equity

### Under `personal_growth` (abstract_concepts)
- `learning` — education, acquiring knowledge
- `self-improvement` — getting better at something, practice
- `adaptation` — adjusting to change, coping
- `goal-setting` — plans, ambitions, future aspirations
- `decision` — choices, weighing options, judgement

---

## Hierarchy Rules

1. **L2 must belong to the selected L1.** e.g. `leisure` only under `experience/activity`, never under `object`.
2. **L3 must belong to one of the selected L2s.** e.g. `exercise` only under `leisure`, never under `routines`.
3. **Multi-tag is allowed** — a topic can have 2+ L2 tags if they all belong to the same L1.
4. **Tag based on what the topic actually asks**, not just keywords.
5. **Check `tags/tags.txt`** before creating a new tag. Normalise synonyms.

---

## Skill Tags (`skill_tags`) — Unified 7-Type Taxonomy

Both Part 1 questions and Part 3 questions use the same 7-type taxonomy. Each question gets **one** primary top-level skill stored as `skill_tags: [<primary>]`. If genuinely ambiguous after rules, Part 1 may leave `skill_tags` empty for manual follow-up (`claude_p1_type_response.json`).

**Primary-based semantics:** `skill_tags[0]` is the **primary L1** skill type. Sidebar filtering (L1), modal highlighting, and counts use this field. The auto-tagger can match several keyword groups; **`pick_primary_l1` / `PRIMARY_WIN_ORDER` in `pipeline/tag_question_types.py`** selects a single winner (e.g. `evaluation` beats `description` when both match). The displayed badge text is **`skill_subtype` (L2)**; badge color uses parent L1 (`skill_tags[0]`, or L1 inferred from subtype in `js/skillTaxonomy.js`).

**Keyword rule order** (which patterns are tested first) differs from **primary win order** (which single L1 is stored). See `PRIMARY_WIN_ORDER` in `tag_question_types.py`.

Note: `frequency` was merged into `experience` as subtypes (`how_often`, `do_you_usually`).

**Script:** `pipeline/tag_question_types.py` — auto-tags questions using keyword matching. Use `--audit-only --part1 <P1> --part2 <P2>` for read-only auditing (detects missing tags, multi-L1 arrays, subtype mismatches, suspicious description assignments).

---

### experience
Past personal actions, events, memories, frequency of activities.

Keywords: `have you`, `did you`, `what did you`, `when did you`, `when was`, `can you remember`, `how often`, `do you usually`, `do you often`

**Example:** *Have you ever visited a museum?* / *How often do you go to the gym?*

**Subtypes:**
- `have_you_ever` — specific past actions ("Have you ever X?", "Did you X?")
- `remember_when` — recollection of childhood/past states ("Can you remember?", "When you were young?")
- `how_often` — explicit frequency ("How often?", "How frequently?")
- `do_you_usually` — habitual patterns ("Do you usually?", "Do you often?", "Every day?")

---

### description
Factual recall, listing, reporting what exists or what people do.

Keywords: `what is/are`, `which`, `how many/much/long`, `tell me`, `describe`, `do you have`, `is there`, `where`, `who`

**Example:** *What kinds of shops are popular in your city?*

**Subtypes:**
- `what_types` — enumerating types, kinds, examples ("What kinds of?", "What activities?")
- `what_is_it` — characteristics, properties, attributes ("What is X?", "What does X look like?")
- `where_when_who` — location, time, person identification ("Where?", "When?", "Who?")
- `how_to` — methods, procedures, amounts ("How do you X?", "How long?")

---

### preference
Personal likes, dislikes, favorites, enjoyment.

Keywords: `do you like`, `do you prefer`, `favourite`, `do you enjoy`, `which do you prefer`, `do you mind`

**Example:** *Do you prefer shopping online or in stores?*

**Subtypes:**
- `do_you_like` — simple enjoyment ("Do you like?", "Do you enjoy?")
- `which_prefer` — selection between alternatives ("Do you prefer X or Y?", "Favourite?")

---

### evaluation
Judgment, opinion, or recommendation — assessing good/bad, agreeing/disagreeing, weighing options.

Keywords: `do you think`, `should/shouldn't`, `is it important/necessary/good/bad`, `do you agree/believe`, `worth`, `advantages or disadvantages`

**Example:** *Do you think it's important for people to support local shops?*

**Subtypes:**
- `is_it_important` — assessing significance ("Is it important?", "Is it necessary?")
- `should_people` — prescriptive advice ("Should X?", "What should?")
- `good_or_bad` — quality assessment ("Is it good/bad?", "Advantages vs disadvantages?")
- `do_you_agree` — opinion/stance ("Do you agree?", "Do you think?")

---

### analysis
Causal or relational reasoning — explaining how or why things work, what the effects are.

Keywords: `why` (sentence-initial), `how does/do/did`, `what causes/reasons/factors`, `what impact/effect/influence`, `what are the benefits/disadvantages/challenges`

**Example:** *Why do some people prefer shopping online?*

**Subtypes:**
- `why` — explaining causes and reasons ("Why?", "What causes?", "What reasons?")
- `what_effect` — consequences and influence ("What impact?", "How does X affect?")
- `what_pros_cons` — benefits and drawbacks ("What are the benefits/disadvantages?")
- `how_does_it_work` — how something works ("How does X work?", "In what way?")

---

### comparison
Differences, changes over time, contrasts between things.

Keywords: `what are the differences`, `are there differences`, `has/have changed`, `compared`, `better/worse than`, `difference between`, `similarities`

**Example:** *What are the differences between team sports and individual sports?*

**Subtypes:**
- `what_differences` — contrasting two things ("What are the differences?", "Similarities?")
- `has_it_changed` — temporal comparison ("Has X changed?", "Compared to the past?")
- `better_or_worse` — relative quality ("Better/worse than?")

---

### hypothetical
Future-oriented, imagined scenarios, plans, wishes, predictions.

Keywords: `would you like`, `if you`, `would you want/prefer/rather`, `imagine`, `will`, `in the future`, `do you want to`, `plans for`

**Example:** *Do you think more people will shop online in the future?*

**Subtypes:**
- `do_you_want_to` — intentions and desires ("Do you want to?", "Plans for?")
- `what_if` — if-then scenarios ("If you could?", "Would you?")
- `will_it_happen` — forecasting ("Will X?", "In the future?")

---

### unclear
Use when the question genuinely does not fit any of the above, or is too vague to classify confidently.

---

## Skill Subtype (`skill_subtype`) — Second-Level Taxonomy

Every question also gets a `skill_subtype` string — the subtype of its primary (first) `skill_tags` value. 23 subtypes across 7 categories, named to reflect how questions are phrased. Assigned by `pipeline/tag_question_types.py` using keyword matching with confidence tracking.

**Confidence levels:**
- `high` — matched a specific subtype pattern
- `default` — assigned the category's catch-all default subtype

**Audit:** Run with `--audit` flag to generate `human-in-the-loop/skill_subtype_audit.md` listing all default-confidence assignments for manual review.

**Preference vs surface “what/which”:** After L1 keyword rules, `apply_semantic_preference_boost` may add `preference` when `PREFERENCE_SEMANTIC_PATTERNS` match (e.g. *like best*, *do you like*, *your favourite*, *enjoy most*, *would rather*). `pick_primary_l1` then keeps **preference** above **description** so questions such as *What part of your day do you like best?* are not left as description / `what_is_it`.

**Subtype order (preference):** Within `preference`, **`do_you_like`** patterns are evaluated before **`which_prefer`** so liking/favour phrasing wins over broad “A or B” / `or` patterns.

### Sidebar Drill-Down
The frontend sidebar shows skill tags as a two-level hierarchy. Clicking a top-level skill tag reveals its subtypes as clickable tags below. Clicking a subtype filters to questions matching that specific subtype and highlights them in the modal.

---

## Time Frame Tags (`time_frame`) — 3-Value System

Every question gets exactly **one** `time_frame` value: `"past"`, `"present"`, or `"future"`.

**Script:** `pipeline/tag_time_frames.py` — auto-tags questions using keyword matching.

---

### past
Questions about past experiences, memories, completed actions. Covers all past-referring tenses **except** subjunctive mood (which goes to `future`).

**Signals:**
- Past simple: `did`, `was`, `were`, `when you were`, `in your childhood`, `used to`, `grew up`
- Present perfect (experience): `have you ever`, `have you been`, `have you tried`
- Past-referring phrases: `the last time`, `when you were young/a child`, `as a child`, `in the past`, `before`, `recently` (past event)

**Examples:**
- *What did you often do with your friends in your childhood?* → `past`
- *Have you ever been part of a sports team?* → `past`

---

### present
Questions about current states, habits, preferences, opinions, general truths. The default when no clear past or future signal is present.

**Signals:**
- Present simple state/habit: `do you`, `are you`, `what is/are`, `is there`
- Preference: `do you like`, `do you prefer`, `favourite`
- Opinion/evaluation: `do you think`, `is it important`, `should` (prescriptive)
- General/analytical: `why do`, `what can`, `how do`, `what kind of`
- Frequency: `how often`, `do you usually`

**Key rules:**
- "Do you think..." → `present` (opinion held now)
- "What can/should people do..." → `present` (general analysis)
- Comparison across time → `present` (asking for current analysis)

---

### future
Questions about future plans, predictions, hypothetical/imagined scenarios, desires, and wishes.

**Signals:**
- Future tense: `will`, `going to`, `in the future`
- Plans: `plans for`, `plan to`, `next five years`
- Hypothetical/subjunctive: `would you like`, `if you could`, `if you were`, `if you had`, `imagine`
- Desire/aspiration: `want to`, `would like to`, `hope to`

---

### Priority & conflict resolution
1. **Explicit past signal wins** over present frame: "Have you ever..." → `past`
2. **Explicit future signal wins** over present frame: "Do you think X will...?" → `future`
3. **Default is `present`** when no past or future signal is detected
4. **One tag only** — no multi-tagging

---

## JSON Schemas (after tagging)

### Part 1

```json
{
  "topic_en": "Reading",
  "part": 1,
  "season": "2026-Jan-Apr",
  "content_tags": {"l1": "experience/activity", "l2": ["leisure"], "l3": ["reading"]},
  "qualifier_tags": [],
  "questions": [
    { "text": "1. Do you like reading?", "source": "laokaoya", "skill_tags": ["preference"], "skill_subtype": "do_you_like", "time_frame": "present" }
  ],
  "tags": []
}
```

### Part 2

```json
{
  "topic": "a person who likes to look after the natural world",
  "part": 2,
  "season": "2026-Jan-Apr",
  "cue_card": {
    "prompt": "Describe a person who likes to look after the natural world",
    "you_should_say": ["Who this person is", "What he or she does"]
  },
  "part3": [
    { "text": "1. Do you think parents should teach their children?", "source": "tongzhuo", "skill_tags": ["evaluation"], "skill_subtype": "should_people", "time_frame": "present" }
  ],
  "tags": [],
  "content_tags": {"l1": "abstract_concepts", "l2": ["values"], "l3": ["environment", "policy"]},
  "qualifier_tags": []
}
```

---

## Pipeline Scripts

### tag_content_v2.py
Auto-tags topics with `content_tags` via weighted keyword matching against the 3-layer hierarchy. Supports `--dry-run` and `--overwrite`.
```bash
python3 pipeline/tag_content_v2.py merged_part1.json --part 1 --overwrite
python3 pipeline/tag_content_v2.py merged_part2.json --overwrite
```

### tag_question_types.py
Auto-tags questions with `skill_tags` (7 top-level) and `skill_subtype` (23 second-level) via keyword matching. Modes: default (empty only), `--overwrite` (all), `--subtype-only` (keep skill_tags, add subtypes). `--audit` generates `human-in-the-loop/skill_subtype_audit.md`.

**Text normalization (`clean()`):** Strips leading `1.` numbering; rewrites common source typos **`ls` → `is`** at the start of the utterance (so *Is there…* tags correctly); expands **`what's` → `what is`** so description/preference rules match contracted forms. This is tagging-only normalization — prefer fixing obvious typos in source JSON when you notice them.

**Part 1 unclear batch:** If no `RULES_PART1` pattern matches, the question is left without `skill_tags` and listed in `claude_p1_type_response.json` next to the quarter. After a full `--overwrite`, that file is **overwritten** (empty array when all questions match). This is **skill-tag coverage**, not content taxonomy.

```bash
python3 pipeline/tag_question_types.py merged_part1.json --part 1
python3 pipeline/tag_question_types.py merged_part2.json
python3 pipeline/tag_question_types.py merged_part2.json --subtype-only --audit
```

### tag_time_frames.py
Auto-tags questions with `time_frame` (past/present/future) via keyword matching.
```bash
python3 pipeline/tag_time_frames.py merged_part1.json --part 1
python3 pipeline/tag_time_frames.py merged_part2.json
```
