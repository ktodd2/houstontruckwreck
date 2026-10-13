# Private Home network feed — operator runbook

Status: implemented and tested locally only. Nothing in this document has been applied to production. Target: ktodd2/houstontruckwreck, Render houstontruckwreck (srv-d0v6i2a4d50c73e7f9rg), Supabase driveshaftcable / twrihhyfvomqiqbxkitc. Do not use another service/project. Only authenticated admin `/live` and `/api/live` receive this panel; `/tow` and `/api/tow` never receive it.

## Data and trust boundaries

Mac -> HTTPS netmon-ingest -> private PostgreSQL -> netmon-status -> Render backend -> authenticated admin browser. Never put Supabase credentials or either token in HTML/JS, a public build variable, URL, git, logs, screenshots, or chat. The edge functions alone use built-in `SUPABASE_SERVICE_ROLE_KEY` and `SUPABASE_URL`. Do not copy the service role to Render or the Mac.

Ingest and read tokens MUST be independent: `NETMON_INGEST_TOKEN` for the Mac and ingestion function, `NETMON_READ_TOKEN` for Render and status function. Generate each separately with `openssl rand -hex 32`, redirecting into private files, not printing the results. `NETMON_STATUS_URL` defaults to https://twrihhyfvomqiqbxkitc.supabase.co/functions/v1/netmon-status. The uploader uses `NETMON_INGEST_URL=https://twrihhyfvomqiqbxkitc.supabase.co/functions/v1/netmon-ingest`.

Only label, hashed random installation ID, sample timestamp, collector health, latency/loss, device COUNTS, latest aggregate speed with its original timestamp, and agent version are uploaded. No IPs, MACs, router data, device names, hostnames, or per-device bandwidth. A computer's human label is public to your admin wall; override NETMON_LABEL if your ComputerName is sensitive.

Tables have ENABLE + FORCE RLS, no policies, and revoked table/sequence privileges for PUBLIC/anon/authenticated. RPCs are SECURITY INVOKER and revoked for those roles too. Only the built-in BYPASSRLS service_role has access. Source/sample insertion is transactional and same-source/same-time requests are idempotent. Status queries in PostgreSQL avoid the REST 1,000-row limit: one actual point per 5-minute bucket, up to 289 real samples over the last 24 hours; no synthetic points. Latest speed can outlive the latest sample's failed speed attempt. Render computes ages from its own clock: STALE at 120s, OFFLINE at 300s, stale speed at 7200s; collector failure/feed failure is at least STALE. A 15s cache applies to successes and failures. Fetch timeout 3s, redirects refused, sanitized last-good fallback.

## Future deploy order — requires explicit approval

1. Back up the database. Inspect `migrations/20261013120000_netmon_telemetry.sql`. Apply that file ONLY to the confirmed project with your approved SQL workflow (e.g. `psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f supabase/migrations/20261013120000_netmon_telemetry.sql`). This is additive; it creates only netmon tables/functions/index/identity sequence, no policies or extension. Do not apply other pending migrations blindly.
2. Deploy the two functions. This repo has no Supabase config.toml; custom bearer tokens require disabling gateway JWT checks explicitly:

       supabase functions deploy netmon-ingest --project-ref twrihhyfvomqiqbxkitc --no-verify-jwt
       supabase functions deploy netmon-status --project-ref twrihhyfvomqiqbxkitc --no-verify-jwt

   Without secrets they intentionally return 503. The pure modules need no npm dependency.
3. Set independent Supabase secrets `NETMON_INGEST_TOKEN` and `NETMON_READ_TOKEN` via the dashboard or `supabase secrets set --project-ref twrihhyfvomqiqbxkitc --env-file /private/path/netmon.env`. That mode-600 env file contains exactly the two names/values; never commit it or run with shell tracing. Built-in service role/URL are provided by Supabase, not newly created secrets.
4. Set Render's server-only `NETMON_READ_TOKEN` and optionally `NETMON_STATUS_URL` in houstontruckwreck's environment. Leave STORE_STATS_TOKEN/URL and existing behavior alone. Cache/age defaults are code constants in config.py, not additional secrets.
5. Review and merge the local integration branch only when authorized. Main auto-deploys; startup remains `python3 start_app.py`, requirements unchanged. This task does NOT push, merge or deploy.
6. Last, configure the approved Mac uploader with the ingestion URL and ingestion token only. See `~/webteam/netmon-integration/UPLOADER.md`. Do not start the copy beside the current agent: only one collector may own the data directory/port. A later approved cutover must preserve data/snapshot.json and source_uuid. This task does not modify or restart the current agent.

## Verification after an authorized rollout

Use protected environment variables and disable shell tracing. These commands are examples, not executed here. Avoid exposing headers in process listings: pipe curl's config on stdin rather than passing the token as a command-line argument.

    printf 'header = "Authorization: Bearer %s"\n' "$NETMON_READ_TOKEN" | curl --silent --show-error --fail --config - "$NETMON_STATUS_URL"
    curl --silent --output /dev/null --write-out '%{http_code}\n' "$NETMON_STATUS_URL"

Authorized status should be 200, `{ok:true,server_time,sources}`; unauthenticated should be 401 (503 means unset secret). Ingest wrong/no token must be 401, wrong method 405, unknown fields 400, >4096 bytes 413. Do not re-upload old test fixtures: samples older than 24h or >5m future are rejected. Observe the real uploader's next sample instead of forcing a speed test. Verify admin `/api/live` includes netmon and ages, anonymous `/api/live` still redirects to login, viewer `/api/tow` excludes it, and the browser has no token/Supabase calls. If checking `/api/live` with curl, use an existing authorized mode-600 admin cookie jar via `curl --cookie /private/path/admin.cookies https://houstontruckwreck.onrender.com/api/live`.

Retention is deliberately NOT scheduled automatically. An operator may arrange a daily `SELECT public.netmon_prune()` as service_role/admin (removes only samples older than 7 days); document any pg_cron job ID so rollback can unschedule it. No pg_cron extension/job is created by this migration. Until scheduled, storage is unbounded; approve and monitor retention before enabling a long-running uploader.

## Rollback order

Disable the uploader URL first, preserving private source_uuid and local snapshot. Remove Render NETMON_READ_TOKEN (panel shows Not configured); roll back the application commit only through an approved deployment. Disable/delete the two edge functions or remove their dedicated secrets. Unschedule any manually added retention job. Back up telemetry then apply `supabase/rollback/20261013120000_netmon_telemetry_down.sql`. It drops only netmon functions/tables and their owned index/sequence; it is re-runnable, does not CASCADE into unrelated objects. Never drop or rotate the project's service role as a rollback.

## Local checks (no production contact)

    node --test supabase/tests/logic.test.ts
    PGLITE_MODULE="$HOME/webteam/netmon-integration/scratch-rls/node_modules/@electric-sql/pglite/dist/index.js" node --test supabase/tests/rls.test.mjs
    ../netmon-integration/.venv/bin/python -m unittest -v test_netmon

PGlite was installed with `npm install --prefix ../netmon-integration/scratch-rls --ignore-scripts @electric-sql/pglite`; no dependencies or node_modules are committed. Its migration/RLS/rollback test is entirely in-memory, not the hosted project. Native Supabase gateway/Deno deployment and production RLS are not verified until an approved rollout.
