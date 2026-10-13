BEGIN;
DROP FUNCTION IF EXISTS public.netmon_prune();
DROP FUNCTION IF EXISTS public.netmon_status();
DROP FUNCTION IF EXISTS public.netmon_ingest(jsonb);
DROP TABLE IF EXISTS public.netmon_samples;
DROP TABLE IF EXISTS public.netmon_sources;
COMMIT;
