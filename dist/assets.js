export const CACHE='lectio-assets-v1';
let manifestPromise;
export const assetURL=path=>new URL(path,import.meta.url).href;
export async function manifest(){
 if(!manifestPromise)manifestPromise=(async()=>{
  let r;try{r=await fetch(assetURL('offline-manifest.json'),{cache:'no-cache'});}catch{}
  if(!r?.ok)r=await caches.match(assetURL('offline-manifest.json'));
  if(!r?.ok)throw Error('The offline catalogue is unavailable. Start Lectio using Open Lectio.command.');
  return r.json();
 })().catch(e=>{manifestPromise=null;throw e;});return manifestPromise;
}
export async function sha(buffer){return [...new Uint8Array(await crypto.subtle.digest('SHA-256',buffer))].map(x=>x.toString(16).padStart(2,'0')).join('');}
export async function checked(response,item){
 if(!response?.ok||response.redirected)throw Error('Unavailable or redirected: '+item.path);
 const type=response.headers.get('content-type')||'';
 if(item.path.endsWith('.json')&&!type.includes('json'))throw Error('Invalid data response: '+item.path);
 if(!/\.html$/.test(item.path)&&type.includes('text/html'))throw Error('Unexpected sign-in or error page: '+item.path);
 const buffer=await response.arrayBuffer();
 if(buffer.byteLength!==item.bytes||await sha(buffer)!==item.sha256)throw Error('Integrity check failed: '+item.path);
 const headers=new Headers(response.headers);headers.set('x-lectio-sha',item.sha256);headers.delete('content-encoding');headers.set('content-length',String(buffer.byteLength));
 return new Response(buffer,{status:200,headers});
}
export async function asset(path,{verify=false}={}){
 const m=await manifest(),item=m.files.find(x=>x.path===path);if(!item)throw Error('Unknown asset: '+path);
 const cache=await caches.open(CACHE),url=assetURL(path);let r=await cache.match(url);
 if(r){try{if(verify||r.headers.get('x-lectio-sha')!==item.sha256){r=await checked(r,item);await cache.put(url,r.clone());}return r;}catch{await cache.delete(url);}}
 try{r=await checked(await fetch(url),item);}catch(e){throw Error('File not saved or unavailable: '+path+'. '+e.message);}
 try{await cache.put(url,r.clone());}catch(e){throw Error('Could not save '+path+'. Device storage may be full. '+e.message);}
 return r;
}
export const json=async path=>(await asset(path)).json();
export async function inventory(){const m=await manifest(),c=await caches.open(CACHE);let count=0,bytes=0;for(const f of m.files){const r=await c.match(assetURL(f.path));if(r?.headers.get('x-lectio-sha')===f.sha256){count++;bytes+=f.bytes;}}return {count,bytes,total:m.files.length,totalBytes:m.files.reduce((n,x)=>n+x.bytes,0)};}
