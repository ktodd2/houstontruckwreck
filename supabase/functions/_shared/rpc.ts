// Built-in service role stays inside the edge function, never in clients.
export async function rpc(name:string,args:unknown={}) {
 const url=Deno.env.get('SUPABASE_URL'); const key=Deno.env.get('SUPABASE_SERVICE_ROLE_KEY');
 if(!url || !key) throw Error('not configured');
 const response=await fetch(url+'/rest/v1/rpc/'+name,{method:'POST',headers:{apikey:key,Authorization:'Bearer '+key,'Content-Type':'application/json'},body:JSON.stringify(args),signal:AbortSignal.timeout(8000)});
 if(!response.ok) throw Error('database unavailable');
 const text=await response.text();
 return text ? JSON.parse(text) : null;
}
