# Working rules — code + project memory

## 1. Full delivery = code + memory

A task is **complete** only when:

1. **Code / data / config** changes needed for the feature are done, **and**
2. **Project memory files** are updated whenever the change is **non-trivial** (see below).

Agents and humans should treat **“memory update”** as part of the same PR or commit series as the implementation, not an optional follow-up.

---

## 2. What counts as “memory files”

**Memory files** are documentation that future you (or an AI) will read first to run, extend, or debug the project:

| Priority | Paths (examples) |
|----------|------------------|
| **Always in scope** | `CLAUDE.md`, `README.md`, `README_ARCH.md` |
| **Feature / workflow docs** | `docs/taxonomy_runtime_runbook.md`, `docs/CLAUDE_tagging.md`, other `docs/*.md` that describe how something works **after your change** |
| **Data contracts** | `data/quarters/README.md` when quarter layout or runtime files change |

**Not** memory files: throwaway notes, personal scratchpads outside the repo, `human-in-the-loop/` (gitignored) unless you intentionally promote a pattern into `docs/`.

---

## 3. When you must update memory files

Update when the change is **not** a tiny fix (typo, one-line comment, formatting only).

**Non-exhaustive triggers:**

- New or changed **CLI flags**, **paths**, **env vars**, or **run order**
- New **directories** (e.g. `data/quarters/`), **scripts**, or **runtime JSON** contracts
- **Behavior** visible to Kathy or deploy (Vercel, filters, ingest)
- **Deprecation** of an old workflow (remove copy-paste steps; document the replacement)

**Tiny / optional:** spelling in UI string, rename of internal variable with no doc mention.

---

## 4. What to update in those files

- **CLAUDE.md** — operational commands, conventions, “what not to break”
- **README.md** — quick start, URLs, preview, anything a new contributor needs on day one
- **README_ARCH.md** — architecture, data flow, file roles, workflow sections
- **Focused docs** — e.g. runbooks, tagging rules, audit methodology when that subsystem changed

Keep edits **minimal**: only what prevents the docs from **lying** about the repo.

---

## 5. End-of-task summary (required for non-trivial work)

Before closing a task, output a short summary that includes:

1. **Files touched** (created / modified / deleted)
2. **How to run** the new or changed flow (exact commands if applicable)
3. **Known gaps** (e.g. another script still reads root-only paths)

This summary is the handshake that memory files and the implementation stay aligned.

---

## 6. Short reminder for new chats

Paste at the start of a session:

> **Follow `docs/working_rules.md`:** non-trivial changes must update `CLAUDE.md` / `README_ARCH.md` (and any affected `docs/*`) in the same delivery; end with files changed + commands + gaps.

Cursor / Claude Code already load `CLAUDE.md`; keeping **`docs/working_rules.md`** linked from there reinforces the protocol.
