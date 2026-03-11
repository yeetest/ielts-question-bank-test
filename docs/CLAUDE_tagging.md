# Tagging Rules — IELTS Part 1 & Part 2

This file is the permanent reference for how to tag topics and questions in `merged_part1.json` and `merged_part2.json`.
Follow it exactly for all current and future question banks.

---

## What `content_tags` looks like

A flat JSON array. Always 2–4 elements.

```json
"content_tags": ["people", "nature", "conservation"]
"content_tags": ["experience/activity", "work", "international", "aspiration"]
"content_tags": ["object", "heirloom", "sentimental", "culture"]
```

- **Position 0** — category (fixed, exactly one of four values)
- **Positions 1–3** — thematic tags drawn from `tags/tags.txt`

---

## Position 0 — Category

Exactly one of:

| Value | Use when the topic is about… |
|---|---|
| `people` | A person or group of people — friends, family, celebrities, strangers, a child, a colleague |
| `place` | A location — indoor or outdoor, big or small: building, park, mountain, room, church, lake, natural environment |
| `object` | A tangible or intangible *thing* — book, film, technology, app, heirloom, animal, food, music, story, toy, talent, science subject |
| `experience/activity` | Something that happened, is happening, or will happen — event, travel, habit, routine, work experience, study, festival, celebration, a time you lost something, a plan |

**When in doubt:** if the topic sentence's main noun is a thing → `object`. If it describes an event or "a time when" → `experience/activity`. If it centres on a person → `people`. If it centres on a location → `place`.

---

## Positions 1–3 — Thematic Tags

### Source of truth
All valid tags live in **`tags/tags.txt`**. Always check that file before assigning a tag.
If no existing tag is close enough, create a new one and **append it to `tags/tags.txt`** with a one-line description before using it.

### How many tags
- Minimum 1, maximum 3 thematic tags (so the full array is 2–4 elements).
- Pick the most semantically meaningful words/phrases from the topic sentence — nouns, adjectives, key verbs, qualifiers.
- Do not pad with generic words. Fewer sharp tags beat more vague ones.

### Normalisation rules
Synonyms and semantically overlapping words must collapse to a single tag:

| Raw extractions | Normalised tag |
|---|---|
| film, movie, cinema | `movies` |
| job, career, occupation, dream job, part-time work, family business | `work` |
| journey, trip, vacation, vehicle used for travel | `travel` |
| kindness, generosity, volunteering | `helping_others` |
| apology, conflict, forgiveness, saying sorry | `conflict_resolution` |
| enjoyed, liked, loved, disliked, didn't enjoy, positive/negative experience | `likes_dislikes` |
| gadget, digital tool, electronic device | `technology` |
| program, software, digital app | `app` |
| outdoor, scenic, natural setting | `nature` |
| organised, goal-setting | `planning` |
| proud of, accomplishment, success | `achievement` |
| waiting, looking forward to | `anticipation` |
| self-taught, independent study, no teacher | `self-learning` |
| exciting, thrilling, bold | `adventure` |
| family member, relative, family gathering | `family` |
| close companion, trust, personal bond | `friendship` |

---

## The Five-Step Pipeline

Run these steps whenever tagging a new question bank. Steps 1–3 are intermediate files for transparency and review; Step 4 writes to JSON; Step 5 generates the human-editable `.txt` mirror.

### Step 1 — Initial extraction → `pipeline/initial_extraction_for_<file>.txt`

For each topic, extract raw tags using your own reading of the topic sentence.
Format — one topic per line:

```
topic sentence <category, extraction1, extraction2, …>
```

- Assign the fixed category first (see rules above).
- Then extract 1–3 of the most semantically meaningful words/phrases from the topic sentence.
- Do not normalise yet — capture the raw language of the topic.

**Example:**
```
a movie you watched and enjoyed recently <object, movie, likes_dislikes>
a time when you lost your way <experience/activity, lost, navigation, travel>
a wild animal that you want to know more about <object, animal, nature, curiosity>
```

### Step 2 — Normalise → `tags/tags.txt`

Read the initial extraction file. Identify synonyms and semantically similar extractions across all topics. Collapse them to a single mid-grain tag.

Rules:
- The category (position 0) is always fixed — leave it unchanged.
- Tags should be mid-grain: not so specific that each topic has a unique tag, not so broad they carry no meaning.
- Goal: **more topics sharing a tag = more useful** (enables grouping and filtering).
- Write all normalised tags into `tags/tags.txt` with a one-line description.
- For future files: first look up existing tags for matches. Only create new tags for extractions with no close match. Append new tags to `tags/tags.txt`.

### Step 3 — Apply normalisation → `pipeline/normalized_tags_for_<file>.txt`

Re-read the initial extraction file. Replace each raw extraction with its closest match from `tags/tags.txt`. Same format as Step 1.

**Example:**
```
a time when you lost your way <experience/activity, navigation, travel>
a wild animal that you want to know more about <object, animals, nature, curiosity>
```

### Step 4 — Update JSON

In the target JSON file, replace each topic's `content_tags` value with the flat array from Step 3.

```json
"content_tags": ["experience/activity", "navigation", "travel"]
```

Write a small Python script to do this in bulk (use topic string as key). Delete the script after running.

### Step 5 — Generate `.txt` mirror

Run `json_to_txt.py` to regenerate the human-editable mirror:

```bash
python3 pipeline/json_to_txt.py merged_part2.json
```

This produces `merged_part2.txt`. Always run this after any JSON edit.

---

## Current tag vocabulary (summary)

Full definitions are in `tags/tags.txt`. Key tags by group:

**People & social**
`helping_others` · `influence` · `conflict_resolution` · `advice` · `friendship` · `celebrity` · `admiration` · `family`

**Work & career**
`work`

**Travel & places**
`travel` · `international` · `navigation` · `home`

**Money & shopping**
`money` · `shopping` · `service`

**Learning & intellect**
`self-learning` · `learning` · `science` · `reading` · `books` · `intelligence` · `problem-solving` · `creativity` · `planning`

**Technology & media**
`technology` · `app` · `phone` · `social_media` · `media`

**Arts & culture**
`art` · `music` · `movies` · `stories` · `culture`

**Personal qualities & emotions**
`passion` · `talent` · `self-improvement` · `aspiration` · `achievement` · `likes_dislikes` · `happiness` · `anticipation` · `memorable` · `sentimental`

**Objects & possessions**
`heirloom` · `toy` · `childhood` · `everyday_life` · `useful`

**Events & situations**
`social_event` · `celebration` · `restriction` · `mistake` · `disruption` · `first_time` · `adventure`

**Nature**
`nature` · `conservation` · `animals`

**Other**
`child` · `curiosity` · `communication` · `language` · `peaceful` · `food` · `architecture` · `interesting`

---

## All 52 current tags (reference)

```
a person who likes to look after the natural world         → people | nature | conservation
a short-term job you want to have in a foreign country     → experience/activity | work | international | aspiration
a time when you encouraged someone to do something         → experience/activity | influence
a person who often helps others                            → people | helping_others
an item on which you spent more than expected              → object | shopping | money
a time you needed to use your imagination                  → experience/activity | creativity
an interesting building                                    → place | architecture | interesting
a friend who learned something without a teacher           → people | friendship | self-learning
a movie you watched and enjoyed recently                   → object | movies | likes_dislikes
an event you attended in which you didn't enjoy the music  → experience/activity | music | social_event | likes_dislikes
a person who solved a problem in a smart way               → people | problem-solving | intelligence
something important kept in your family for a long time    → object | heirloom | sentimental | culture
a bicycle/motorcycle/car trip you would like to take       → experience/activity | travel | aspiration
a piece of technology you would like to own                → object | technology | aspiration
a program or app on your computer or phone                 → object | app | technology
a person who makes plans and is good at planning           → people | planning
a child who loves drawing/painting                         → people | child | art | passion
a time when you gave advice to others                      → experience/activity | advice | helping_others
a time when you felt proud of a family member              → experience/activity | family | achievement
an occasion when many people were smiling                  → experience/activity | happiness | celebration
an occasion when you were not allowed to use your phone    → experience/activity | phone | restriction
a famous person you would like to meet                     → people | celebrity | aspiration | admiration
a perfect job you would like to have in the future         → experience/activity | work | aspiration
a TV/online program you enjoy watching                     → object | media | likes_dislikes
a natural place (e.g. park, mountain)                      → place | nature
a time when you waited for something special               → experience/activity | anticipation | memorable
an important decision made with the help of other people   → experience/activity | decision | collaboration
a book you read that you found useful                      → object | books | reading | useful
a sportsperson you admire                                  → people | sports | admiration
a time when you broke something                            → experience/activity | mistake
a time you saw something interesting on social media       → experience/activity | social_media | interesting
a creative person (artist, musician, etc.) you admire      → people | creativity | admiration | art
an important old thing your family has kept for a long time→ object | heirloom | sentimental | culture
the time you first talked with others in a foreign language→ experience/activity | language | first_time | communication
an exciting activity you have tried for the first time     → experience/activity | first_time | adventure
a time when someone apologized to you                      → experience/activity | conflict_resolution
a long journey you had and would like to take again        → experience/activity | travel | aspiration
a great dinner you and your friend or family enjoyed       → experience/activity | food | family | likes_dislikes
a time when the electricity suddenly went off              → experience/activity | disruption | home
a time when you received good service in a shop            → experience/activity | shopping | service | likes_dislikes
a person who enjoys working for a family business          → people | work | family | likes_dislikes
a toy you liked in your childhood                          → object | toy | childhood | likes_dislikes
a natural talent you would like to improve                 → object | talent | self-improvement | aspiration
a time when you lost your way                              → experience/activity | navigation | travel
a good friend who is important to you                      → people | friendship
an interesting traditional story                           → object | stories | culture | interesting
a habit your friend has and you want to develop            → experience/activity | habit | self-improvement | aspiration
a wild animal that you want to know more about             → object | animals | nature | curiosity
a friend who is good at music/singing                      → people | friendship | music | talent
an area/subject of science you are interested in           → object | science | learning | aspiration
a quiet place you like to go                               → place | peaceful | likes_dislikes
something that you can't live without                      → object | everyday_life
```




## Question Type Tags (`type_tags`) — Unified 8-Type Taxonomy

Both Part 1 questions and Part 3 questions use the same 8-type taxonomy. Each question gets a `type_tags` array with 1–3 values. Assign all that apply (up to 3, in priority order); if genuinely ambiguous, use `unclear`.

**Priority order:** `experience` → `frequency` → `description` → `preference` → `evaluation` → `analyze` → `comparison` → `hypothetical`

**Script:** `pipeline/tag_question_types.py` — auto-tags questions using keyword matching.

---

### experience
Past personal actions or events — what you did, saw, tried, or remember.

Keywords: `have you`, `did you`, `what did you`, `when did you`, `when was`, `can you remember`

**Example:** *Have you ever visited a museum?*

---

### frequency
How often or how regularly something happens.

Keywords: `how often`, `do you usually`, `do you often`, `every day`, `how frequently/regularly`

**Example:** *How often do you go to the gym?*

---

### description
Factual recall, listing, reporting what exists or what people do.

Keywords: `what is/are`, `which`, `how many/much/long`, `tell me`, `describe`, `do you have`, `is there`, `where`, `who`

**Example:** *What kinds of shops are popular in your city?*

---

### preference
Personal likes, dislikes, favorites, enjoyment.

Keywords: `do you like`, `do you prefer`, `favourite`, `do you enjoy`, `which do you prefer`, `do you mind`

**Example:** *Do you prefer shopping online or in stores?*

---

### evaluation
Judgment, opinion, or recommendation — assessing good/bad, agreeing/disagreeing, weighing options.

Keywords: `do you think`, `should/shouldn't`, `is it important/necessary/good/bad`, `do you agree/believe`, `worth`, `advantages or disadvantages`

**Example:** *Do you think it's important for people to support local shops?*

---

### analyze
Causal or relational reasoning — explaining how or why things work, what the effects are.

Keywords: `why` (sentence-initial), `how does/do/did`, `what causes/reasons/factors`, `what impact/effect/influence`, `what are the benefits/disadvantages/challenges`

**Example:** *Why do some people prefer shopping online?*

---

### comparison
Differences, changes over time, contrasts between things.

Keywords: `what are the differences`, `are there differences`, `has/have changed`, `compared`, `better/worse than`, `difference between`, `similarities`

**Example:** *What are the differences between team sports and individual sports?*

---

### hypothetical
Future-oriented, imagined scenarios, plans, wishes, predictions.

Keywords: `would you like`, `if you`, `would you want/prefer/rather`, `imagine`, `will`, `in the future`, `do you want to`, `plans for`

**Example:** *Do you think more people will shop online in the future?*

---

### unclear
Use when the question genuinely does not fit any of the above, or is too vague to classify confidently.

---

## Tagging with `tag_question_types.py`

`pipeline/tag_question_types.py` auto-tags questions by keyword matching against the rules above. Uses the same 8-type taxonomy for both parts.

```bash
python3 pipeline/tag_question_types.py merged_part1.json --part 1   # tags questions[] array
python3 pipeline/tag_question_types.py merged_part2.json             # tags part3[] array
```

- For Part 1: writes `type_tags` into each item in the `questions` array.
- For Part 2: writes `type_tags` into each item in the `part3` array.
- After running, always regenerate the `.txt` mirror.
- Review output in the `.txt` file and correct any misclassifications manually, then sync back with `txt_to_json.py`.

---

---

# Part 1 Tagging Rules

Part 1 topics are short abstract noun phrases (e.g. "Food", "Reading", "Shoes") rather than full sentences. The same two-layer tagging system applies, with some adjustments.

---

## Part 1 JSON Schema (after tagging)

```json
{
  "topic_en": "Reading",
  "part": 1,
  "season": "2026-Jan-Apr",
  "content_tags": ["experience/activity", "reading", "likes_dislikes"],
  "questions": [
    { "text": "1. Do you like reading?", "source": "laokaoya", "type_tags": ["preference"] }
  ],
  "tags": []
}
```

- `content_tags` is a new field — add it alongside the existing `tags: []` (do not replace `tags`).
- `type_tags` is added to each question object in the `questions` array.

---

## Layer 1 — `content_tags` for Part 1

Same flat array structure as Part 2: position 0 = category, positions 1–2 = thematic tags.

**Array size:** 2–3 elements (categories are more abstract, so 1–2 thematic tags usually sufficient).

### Category assignment for Part 1

Part 1 topics are single nouns/phrases. Apply these rules:

| Category | Example Part 1 topics |
|---|---|
| `experience/activity` | Daily routine, Reading, Walking, Chatting, Typing, Hobby, Having a break, Sharing, Going out, Spare time, Taking photos, Growing vegetables/fruits, Borrowing/Lending, Doing something well, Morning time, Sports team, Childhood activities |
| `place` | Museum, Building, Crowded place, Public places, The city you live in, Home/Accommodation, View, Scenery |
| `object` | Food, Shoes, Plants, Gifts, Advertisement, Pets and Animals |
| `people` | Staying with old people |

**Key rule:** if the topic is an *activity you do* or a *behaviour/habit*, use `experience/activity` even if the word sounds like a noun (e.g. "Reading" → `experience/activity`, not `object`).

### Thematic tags for Part 1

Same vocabulary as Part 2 (`tags/tags.txt`). Because Part 1 topics are abstract, pick the 1–2 tags that best capture what the topic is fundamentally about:

| Topic | Suggested tags |
|---|---|
| Daily routine | `everyday_life` |
| Life stages | `nostalgia`, `aspiration` |
| View / Scenery | `nature`, `travel` |
| Childhood activities | `childhood`, `likes_dislikes` |
| Building | `architecture` |
| Typing | `technology`, `learning` |
| Hobby | `likes_dislikes`, `passion` |
| Sports team | `social_event` |
| Reading | `reading`, `likes_dislikes` |
| Gifts | `shopping`, `sentimental` |
| Morning time | `everyday_life` |
| Walking | `nature`, `everyday_life` |
| Food | `food`, `likes_dislikes` |
| Pets and Animals | `animals`, `likes_dislikes` |
| Sharing | `helping_others`, `friendship` |
| Having a break | `everyday_life` |
| Borrowing/Lending | `money`, `friendship` |
| Advertisement | `media`, `technology` |
| Chatting | `communication`, `friendship` |
| Growing vegetables/fruits | `nature`, `food` |
| Museum | `culture`, `learning` |
| Crowded place | `social_event` |
| Going out | `everyday_life` |
| Staying with old people | `family`, `helping_others` |
| Doing something well | `achievement` |
| Shoes | `shopping`, `likes_dislikes` |
| Rules | `restriction`, `learning` |
| Public places | `social_event` |
| Plants | `nature`, `home` |
| Spare time | `likes_dislikes`, `everyday_life` |
| Taking photos | `art`, `likes_dislikes` |
| The city you live in | `home`, `travel` |
| Home/Accommodation | `home` |

These are suggestions — always check `tags/tags.txt` and use judgment. Do not over-tag; 1–2 thematic tags is usually enough.

---

## Layer 2 — `type_tags` for Part 1 Questions

Uses the same unified 8-type taxonomy as Part 2+3. See the "Question Type Tags" section above for full definitions.

### Characteristic patterns for Part 1:

**experience** — "Have you...?", "Did you...?", "Can you remember...?"
→ *"Have you ever had a pet?"* → `["experience"]`

**description** — most "What is/are...?", "Do you have...?", "Where...?" questions
→ *"What do you usually do in the morning?"* → `["description"]`

**preference** — "Do you like...?", "Do you prefer...?", "What is your favourite...?"
→ *"Do you like reading?"* → `["preference"]`

**evaluation** — "Do you think...?", "Is it important...?", "Should...?"
→ *"Do you think it's important to have a daily routine?"* → `["evaluation"]`

**analyze** — "Why...?" (sentence-initial), "How does...?"
→ *"Why do people like to walk in parks?"* → `["analyze"]`

**comparison** — "What are the differences...?", "Has X changed...?"
→ *"What are the differences between team sports and individual sports?"* → `["comparison"]`

**hypothetical** — "Would you like to...?", "If you...?", "Will...?"
→ *"Would you like to move to a different house in the future?"* → `["hypothetical"]`

---

## Tagging with `tag_content_topics.py` (Part 1)

```bash
python3 pipeline/tag_content_topics.py merged_part1.json
```

- Uses fuzzy lookup against `tags/tags.txt` + Claude batch for category assignment.
- Writes `content_tags` as a new field in each topic object.
- After running, regenerate `.txt` mirror: `python3 pipeline/json_to_txt.py merged_part1.json`