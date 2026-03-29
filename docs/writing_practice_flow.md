# Writing Practice Flow

This file is the current source of truth for the writing practice implementation inside the static `ielts-question-bank-test` project.

## UI boundary

- Keep the existing static site visual style.
- Writing cards open a dedicated full-page practice workspace.
- Auth and payment are modal overlays on top of that practice page.
- In practice mode, the site-level top menu is hidden.

## Main practice structure

- Left collapsible sidebar:
  - `Return to Question Page`
  - `My Practice Records`
  - each saved question has exactly 3 children:
    - `My Practice Record`
    - `Sample Band 9`
    - `Practice High-Score Expressions`
- Main content:
  - left = writing editor
  - right = result tabs
- The editor and result panes are separated by a draggable divider.
- If the left library is collapsed, the remaining workspace expands automatically.

## Right panel tabs

Only 2 tabs are used:

1. `Sample Band 9`
2. `My Revised Band 9`

Rules:

- Before correction, `My Revised Band 9` shows only `Correct My Essay`.
- After correction, the same tab shows:
  - IELTS band-score feedback
  - revised Band 9 version
  - `Save to My Private Template Library`

There is no separate feedback tab.
There is no separate band-descriptor tab.
Band descriptors are embedded into the AI prompt only.

## AI correction rule

- One click = one AI call = one combined result = one credit.
- The correction result always includes both:
  - concise 4-dimension IELTS feedback
  - revised Band 9 version
- OpenRouter is the only AI provider.
- Endpoint:
  - `POST https://openrouter.ai/api/v1/chat/completions`
- Required env vars:
  - `OPENROUTER_API_KEY`
  - `OPENROUTER_MODEL`
- Recommended default env value:
  - `OPENROUTER_MODEL=deepseek/deepseek-r1-0528`
- Project root local env file:
  - `.env`
- If either env var is missing, the API returns a clear error.
- There is no mock output and no fallback provider.

## Auth / credit / payment flow

This project now uses credit-only access control.

- No free / paid / admin roles
- If not logged in and the user clicks `Correct My Essay`:
  - open auth modal
- If logged in with 0 credits:
  - switch the auth modal into payment state
- If logged in with credits:
  - continue the pending correction immediately

The pending action is kept in the front-end auth state so the user returns to the same practice context after auth/payment.

## Save rule

- Official save is manual only.
- Local workspace restore exists, but it is not the official writing-library record.
- One user can have only one saved practice record per task.
- `Save to My Private Template Library` writes to the same underlying record store that powers the left sidebar.

## Highlight / flashcard rule

- Highlights can be created in:
  - `Sample Band 9`
  - `My Revised Band 9`
- When text is selected, actions appear near the selected text instead of at the bottom.
- Highlight data generates the flashcard data for the same task.
- Flashcard direction is Chinese -> English.
- If a saved task has no highlights, show exactly:

`当前你还没有高光选中你想要学习的表达，快去右侧 sample 部分选中吧`

## Current local storage model

Two browser-side stores are used right now:

1. `ielts_writing_workspace_v3`
   - temporary per-task workspace
   - essay draft
   - active tab
   - current view mode
   - correction result
   - highlights
   - flashcards
   - dirty flag

2. `ielts_writing_library_v3`
   - manual saved records grouped by user identity
   - one record per user per task
   - original essay
   - correction result
   - sample answer
   - highlights
   - flashcards
   - saved timestamp

## Current server-side API files

- `api/auth/send-code.js`
- `api/auth/verify-code.js`
- `api/auth/session.js`
- `api/auth/logout.js`
- `api/billing/starter-pack.js`
- `api/ai.js`
- `api/_lib/auth.js`

## Known limitation

- Payment is still a placeholder `Buy 5 credits` action, not a real payment provider.
- Verification currently returns a preview code outside production unless a real delivery provider is added.
- If a question does not have a real pre-generated sample in the data source, the sample tab now shows an explicit unavailable message instead of a fake local sample.
