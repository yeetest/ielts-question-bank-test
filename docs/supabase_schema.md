# Supabase Schema

This project now includes a first-pass remote-manageable Supabase schema in:

- `supabase/migrations/20260330013000_init_writing_schema.sql`

It creates and configures:

- `profiles`
- `credit_transactions`
- `writing_tasks`
- `practice_records`
- `highlights`
- `flashcards`
- `pending_actions`

It also adds:

- a signup trigger from `auth.users` to `public.profiles`
- an `updated_at` trigger helper
- a highlight -> flashcard sync trigger
- RLS policies for user-owned rows

## Remote apply

Use:

```bash
zsh scripts/apply-supabase-schema.sh
```

Required env:

```bash
SUPABASE_URL=...
SUPABASE_ANON_KEY=...
SUPABASE_PROJECT_REF=...
SUPABASE_ACCESS_TOKEN=...
```

Notes:

- `SUPABASE_PROJECT_REF` can be derived from `SUPABASE_URL`, but explicit configuration is safer.
- `SUPABASE_ACCESS_TOKEN` is a Supabase personal access token for CLI auth.
- The default apply script now uses the Supabase Management API, so `SUPABASE_DB_PASSWORD` is not required.
