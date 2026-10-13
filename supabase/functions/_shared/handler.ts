import {authorized, MAX_BODY, validate, shapeStatus} from './logic.ts';
type Options = {secret?:string, ingest:boolean, rpc:(name:string,args?:any)=>Promise<any>};
const json=(body:unknown,status=200)=>new Response(JSON.stringify(body),{status,headers:{'Content-Type':'application/json','Cache-Control':'no-store'}});
export function handler(options:Options) {
 return async (req:Request):Promise<Response> => {
  if(req.method !== (options.ingest?'POST':'GET')) return json({ok:false,error:'method not allowed'},405);
  if(!options.secret) return json({ok:false,error:'not configured'},503);
  if(!await authorized(req.headers.get('Authorization'),options.secret)) return json({ok:false,error:'unauthorized'},401);
  try {
   if(!options.ingest) return json(shapeStatus(await options.rpc('netmon_status')));
   if(!req.headers.get('content-type')?.toLowerCase().startsWith('application/json')) return json({ok:false,error:'JSON required'},415);
   if(Number(req.headers.get('content-length'))>MAX_BODY) return json({ok:false,error:'too large'},413);
   const reader=req.body?.getReader();
   if(!reader) return json({ok:false,error:'invalid payload'},400);
   const chunks:Uint8Array[]=[]; let length=0;
   while(true){const {done,value}=await reader.read();if(done)break;length+=value.length;if(length>MAX_BODY){await reader.cancel();return json({ok:false,error:'too large'},413);}chunks.push(value);}
   const bytes=new Uint8Array(length);let offset=0;for(const c of chunks){bytes.set(c,offset);offset+=c.length;}
   let payload;
   try{payload=validate(JSON.parse(new TextDecoder('utf-8',{fatal:true}).decode(bytes)));}
   catch{return json({ok:false,error:'invalid payload'},400);}
   await options.rpc('netmon_ingest',{p:payload});
   return json({ok:true},201);
  }catch{return json({ok:false,error:'feed unavailable'},503);}
 };
}
