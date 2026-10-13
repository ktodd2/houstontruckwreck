import {handler} from '../_shared/handler.ts';
import {rpc} from '../_shared/rpc.ts';
Deno.serve(handler({secret:Deno.env.get('NETMON_READ_TOKEN'),ingest:false,rpc}));
