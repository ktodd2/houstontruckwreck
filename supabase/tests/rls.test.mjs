import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {pathToFileURL} from 'node:url';
const {PGlite}=await import(pathToFileURL(process.env.PGLITE_MODULE).href);
const db=new PGlite();
const up=readFileSync(new URL('../migrations/20261013120000_netmon_telemetry.sql',import.meta.url),'utf8');
const down=readFileSync(new URL('../rollback/20261013120000_netmon_telemetry_down.sql',import.meta.url),'utf8');
await db.exec('CREATE ROLE anon; CREATE ROLE authenticated; CREATE ROLE service_role BYPASSRLS; GRANT USAGE ON SCHEMA public TO anon,authenticated,service_role;');
await db.exec(up);
test('RLS enabled and forced, zero policies',async()=>{const r=await db.query("SELECT relrowsecurity,relforcerowsecurity FROM pg_class WHERE relname IN ('netmon_sources','netmon_samples')");assert.equal(r.rows.length,2);for(const x of r.rows)assert.ok(x.relrowsecurity&&x.relforcerowsecurity);assert.equal((await db.query("SELECT * FROM pg_policies WHERE tablename LIKE 'netmon_%'")).rows.length,0);});
for(const role of ['anon','authenticated'])test(role+' denied all table verbs, sequence and RPC',async()=>{
 await db.exec('SET ROLE '+role);
 try{for(const table of ['netmon_sources','netmon_samples'])for(const query of ['SELECT * FROM '+table,'INSERT INTO '+table+' DEFAULT VALUES','UPDATE '+table+' SET '+(table==='netmon_sources'?'label=label':'collector_ok=collector_ok'),'DELETE FROM '+table])await assert.rejects(db.exec(query),/permission denied/);
 await assert.rejects(db.exec("SELECT nextval('netmon_samples_id_seq')"),/permission denied/);await assert.rejects(db.exec('SELECT netmon_status()'),/permission denied/);
 }finally{await db.exec('RESET ROLE');}
});
test('service role ingest/status/dedup/downsample/delete; rollback repeat',async()=>{
 const p=JSON.parse(readFileSync(new URL('./valid-sample.json',import.meta.url),'utf8'));p.sampled_at=new Date().toISOString();
 await db.exec('SET ROLE service_role');
 await db.query('SELECT netmon_ingest($1::jsonb)',[JSON.stringify(p)]);await db.query('SELECT netmon_ingest($1::jsonb)',[JSON.stringify(p)]);
 assert.equal((await db.query('SELECT * FROM netmon_samples')).rows.length,1);
 await db.exec("UPDATE netmon_sources SET label='Mac test'; UPDATE netmon_samples SET collector_ok=true;");
 const data=(await db.query('SELECT netmon_status() AS data')).rows[0].data;
 assert.equal(data.sources[0].label,'Mac test');assert.equal(data.sources[0].history.length,1);assert.ok(!JSON.stringify(data).includes('source_key'));
 // Real SQL history downsampling (not REST pagination), latest speed timestamp preserved.
 for(let i=1;i<=30;i++){
   const q={...p,sampled_at:new Date(Date.parse(p.sampled_at)-i*30000).toISOString()};
   await db.query('SELECT netmon_ingest($1::jsonb)',[JSON.stringify(q)]);
 }
 const series=(await db.query('SELECT netmon_status() AS data')).rows[0].data.sources[0];
 assert.ok(series.history.length>=3 && series.history.length<=5);
 assert.equal(Date.parse(series.latest_sample.sampled_at),Date.parse(p.sampled_at));
 assert.equal(Date.parse(series.latest_speed.speed_measured_at),Date.parse(p.speed_measured_at));
 await db.exec('SELECT netmon_prune(); DELETE FROM netmon_samples; DELETE FROM netmon_sources; RESET ROLE;');
 await db.exec(down);await db.exec(down);assert.equal((await db.query("SELECT to_regclass('public.netmon_sources') AS t")).rows[0].t,null);await db.exec(up);await db.exec(down);await db.close();
});
