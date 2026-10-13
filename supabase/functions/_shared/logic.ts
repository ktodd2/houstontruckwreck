// Pure, built-ins only; Node 26 and Deno both erase these types.
import {timingSafeEqual} from "node:crypto";
export const MAX_BODY = 4096;
export const fields = ['source_key','label','sampled_at','collector_ok','internet_latency_ms','internet_loss_pct','gateway_latency_ms','gateway_loss_pct','devices_online','devices_seen','download_mbps','upload_mbps','speed_measured_at','agent_version'];
export async function authorized(header: string | null, secret: string | undefined): Promise<boolean> {
  if (!secret || !header || header.length > 1024 || !header.startsWith('Bearer ')) return false;
  // Hash to fixed-length byte arrays; compare all bytes without early exit.
  const hash = async (s: string) => new Uint8Array(await crypto.subtle.digest('SHA-256',new TextEncoder().encode(s)));
  const [a,b] = await Promise.all([hash(header.slice(7)),hash(secret)]);
  return timingSafeEqual(a,b);
}
export function timestamp(value: unknown): number {
  if (typeof value !== 'string' || value.length > 35 || !/^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(?:\.\d{1,6})?(?:Z|[+-]\d\d:\d\d)$/.test(value)) throw Error('invalid timestamp');
  const t = Date.parse(value);
  if (!Number.isFinite(t) || new Date(value.slice(0,10)+'T00:00:00Z').toISOString().slice(0,10) !== value.slice(0,10)) throw Error('invalid timestamp');
  return t;
}
export function validate(input: unknown, now = Date.now()): Record<string, any> {
  if (!input || typeof input !== 'object' || Array.isArray(input)) throw Error('invalid object');
  const p = input as Record<string, any>;
  if (Object.keys(p).length !== fields.length || Object.keys(p).some(k=>!fields.includes(k)) || fields.some(k=>!Object.hasOwn(p,k))) throw Error('invalid fields');
  if (typeof p.source_key !== 'string' || !/^[0-9a-f]{64}$/.test(p.source_key)) throw Error('invalid source');
  for (const [key,limit] of [['label',80],['agent_version',40]] as const) {
    if (typeof p[key] !== 'string' || !p[key].trim() || p[key].length > limit || /[\x00-\x1f\x7f]/.test(p[key])) throw Error('invalid text');
  }
  const sampled = timestamp(p.sampled_at);
  if (sampled > now+300000 || sampled < now-86400000) throw Error('sample outside window');
  if (typeof p.collector_ok !== 'boolean') throw Error('invalid collector');
  for (const key of ['internet_latency_ms','gateway_latency_ms','internet_loss_pct','gateway_loss_pct','download_mbps','upload_mbps']) {
    const v=p[key], max=key.endsWith('_pct')?100:key.endsWith('_ms')?60000:1000000;
    if (v !== null && (typeof v !== 'number' || !Number.isFinite(v) || v < 0 || v > max)) throw Error('invalid measurement');
  }
  for (const key of ['devices_online','devices_seen']) if (!Number.isInteger(p[key]) || p[key]<0 || p[key]>65535) throw Error('invalid count');
  if (p.devices_online>p.devices_seen) throw Error('invalid counts');
  if (p.speed_measured_at === null) {
    if(p.download_mbps!==null || p.upload_mbps!==null) throw Error('speed requires timestamp');
  } else if (timestamp(p.speed_measured_at)>sampled || p.download_mbps===null || p.upload_mbps===null) throw Error('invalid speed');
  return Object.fromEntries(fields.map(k=>[k,p[k]]));
}
// Shape RPC output defensively. Private source identifiers never leave the edge.
export function shapeStatus(data: any) {
  if (!data || !Array.isArray(data.sources)) throw Error('invalid database response');
  const sampleFields = fields.filter(k=>!['source_key','label'].includes(k));
  const pick=(x:any,keys:string[])=>x ? Object.fromEntries(keys.map(k=>[k,x[k] ?? null])):null;
  return {ok:true,server_time:new Date().toISOString(),sources:data.sources.map((s:any)=>({
    label:s.label,last_seen:s.last_seen,latest_sample:pick(s.latest_sample,sampleFields),
    latest_speed:pick(s.latest_speed,['download_mbps','upload_mbps','speed_measured_at']),
    history:(s.history||[]).slice(-289).map((h:any)=>pick(h,['sampled_at','internet_latency_ms','gateway_latency_ms']))
  }))};
}
