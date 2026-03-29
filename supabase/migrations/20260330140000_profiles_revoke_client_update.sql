-- Users must not UPDATE their own profiles row via PostgREST (they could set credits arbitrarily).
-- Credit changes are done only from Vercel serverless using SUPABASE_SERVICE_ROLE_KEY (see api/_lib/auth.js).
drop policy if exists "profiles_update_own" on public.profiles;
