-- Additive, private telemetry. Apply only after operator approval.
BEGIN;
CREATE TABLE public.netmon_sources (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
 source_key text NOT NULL UNIQUE CHECK (source_key ~ '^[0-9a-f]{64}$'),
 label text NOT NULL CHECK (length(label) BETWEEN 1 AND 80),
 first_seen timestamptz NOT NULL DEFAULT now(),
 last_seen timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE public.netmon_samples (
 id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
 source_id uuid NOT NULL REFERENCES public.netmon_sources(id) ON DELETE CASCADE,
 sampled_at timestamptz NOT NULL,
 collector_ok boolean NOT NULL,
 internet_latency_ms double precision CHECK (internet_latency_ms BETWEEN 0 AND 60000),
 internet_loss_pct double precision CHECK (internet_loss_pct BETWEEN 0 AND 100),
 gateway_latency_ms double precision CHECK (gateway_latency_ms BETWEEN 0 AND 60000),
 gateway_loss_pct double precision CHECK (gateway_loss_pct BETWEEN 0 AND 100),
 devices_online integer NOT NULL CHECK (devices_online BETWEEN 0 AND 65535),
 devices_seen integer NOT NULL CHECK (devices_seen BETWEEN devices_online AND 65535),
 download_mbps double precision CHECK (download_mbps BETWEEN 0 AND 1000000),
 upload_mbps double precision CHECK (upload_mbps BETWEEN 0 AND 1000000),
 speed_measured_at timestamptz,
 agent_version text NOT NULL CHECK (length(agent_version) BETWEEN 1 AND 40),
 CHECK ((speed_measured_at IS NULL AND download_mbps IS NULL AND upload_mbps IS NULL)
 OR (speed_measured_at IS NOT NULL AND download_mbps IS NOT NULL AND upload_mbps IS NOT NULL)),
 CHECK (speed_measured_at IS NULL OR speed_measured_at <= sampled_at),
 UNIQUE (source_id, sampled_at)
);
CREATE INDEX netmon_samples_source_time ON public.netmon_samples(source_id, sampled_at DESC);
ALTER TABLE public.netmon_sources ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.netmon_sources FORCE ROW LEVEL SECURITY;
ALTER TABLE public.netmon_samples ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.netmon_samples FORCE ROW LEVEL SECURITY;
REVOKE ALL ON public.netmon_sources, public.netmon_samples FROM anon, authenticated, PUBLIC;
REVOKE ALL ON SEQUENCE public.netmon_samples_id_seq FROM anon, authenticated, PUBLIC;
GRANT SELECT, INSERT, UPDATE, DELETE ON public.netmon_sources, public.netmon_samples TO service_role;
GRANT USAGE, SELECT ON SEQUENCE public.netmon_samples_id_seq TO service_role;

-- Invoker rights: only the built-in BYPASSRLS service_role can execute/use these.
CREATE FUNCTION public.netmon_ingest(p jsonb) RETURNS void
LANGUAGE plpgsql SECURITY INVOKER SET search_path = public, pg_temp AS $$
DECLARE source uuid;
BEGIN
 INSERT INTO netmon_sources(source_key,label) VALUES(p->>'source_key',p->>'label')
 ON CONFLICT(source_key) DO UPDATE SET label=EXCLUDED.label,last_seen=now()
 RETURNING id INTO source;
 INSERT INTO netmon_samples(source_id,sampled_at,collector_ok,internet_latency_ms,internet_loss_pct,
 gateway_latency_ms,gateway_loss_pct,devices_online,devices_seen,download_mbps,upload_mbps,speed_measured_at,agent_version)
 VALUES(source,(p->>'sampled_at')::timestamptz,(p->>'collector_ok')::boolean,
 (p->>'internet_latency_ms')::float8,(p->>'internet_loss_pct')::float8,
 (p->>'gateway_latency_ms')::float8,(p->>'gateway_loss_pct')::float8,
 (p->>'devices_online')::integer,(p->>'devices_seen')::integer,
 (p->>'download_mbps')::float8,(p->>'upload_mbps')::float8,
 (p->>'speed_measured_at')::timestamptz,p->>'agent_version')
 ON CONFLICT(source_id,sampled_at) DO NOTHING;
END $$;

CREATE FUNCTION public.netmon_status() RETURNS jsonb
LANGUAGE sql STABLE SECURITY INVOKER SET search_path = public, pg_temp AS $$
SELECT jsonb_build_object('ok',true,'server_time',now(),'sources',COALESCE(jsonb_agg(item ORDER BY label),'[]'::jsonb))
FROM (
 SELECT s.label,jsonb_build_object('label',s.label,'last_seen',s.last_seen,
 'latest_sample',(SELECT to_jsonb(n)-'id'-'source_id' FROM netmon_samples n WHERE n.source_id=s.id ORDER BY sampled_at DESC LIMIT 1),
 'latest_speed',(SELECT jsonb_build_object('download_mbps',download_mbps,'upload_mbps',upload_mbps,'speed_measured_at',speed_measured_at)
 FROM netmon_samples n WHERE n.source_id=s.id AND speed_measured_at IS NOT NULL ORDER BY speed_measured_at DESC,sampled_at DESC LIMIT 1),
 'history',(SELECT COALESCE(jsonb_agg(to_jsonb(h) ORDER BY sampled_at),'[]'::jsonb) FROM (
 SELECT DISTINCT ON (floor(extract(epoch FROM sampled_at)/300)) sampled_at,internet_latency_ms,gateway_latency_ms
 FROM netmon_samples n WHERE n.source_id=s.id AND sampled_at >= now()-interval '24 hours'
 ORDER BY floor(extract(epoch FROM sampled_at)/300),sampled_at DESC
 ) h)) AS item FROM netmon_sources s
) sources;
$$;
CREATE FUNCTION public.netmon_prune() RETURNS bigint
LANGUAGE plpgsql SECURITY INVOKER SET search_path = public, pg_temp AS $$
DECLARE removed bigint;
BEGIN
 DELETE FROM netmon_samples WHERE sampled_at < now()-interval '7 days';
 GET DIAGNOSTICS removed = ROW_COUNT;
 RETURN removed;
END $$;
REVOKE ALL ON FUNCTION public.netmon_ingest(jsonb), public.netmon_status(), public.netmon_prune() FROM anon, authenticated, PUBLIC;
GRANT EXECUTE ON FUNCTION public.netmon_ingest(jsonb), public.netmon_status(), public.netmon_prune() TO service_role;
-- Optional operator-managed pg_cron: SELECT public.netmon_prune() daily.
-- No extension, cron job, policy, or changes to existing objects are installed here.
COMMIT;
