import {setupReaderControls} from './reader-controls.js';
import {json,asset,manifest,inventory} from './assets.js';
import {normalize,candidates,flatten,shardFor,entryLabel} from './engine.mjs';
const $=id=>document.getElementById(id),el=(tag,text,cls)=>{const n=document.createElement(tag);if(text!==undefined)n.textContent=text;if(cls)n.className=cls;return n;};
const safeRead=(k,f)=>{try{return JSON.parse(localStorage.getItem(k))??f;}catch{return f;}};
const save=(k,v)=>{try{localStorage.setItem(k,JSON.stringify(v));}catch{toast('Reading place could not be saved. Storage is unavailable.');}};
let prefs={size:null,leading:'1.85',font:'serif',theme:'paper',width:'comfortable',paragraphGap:'1.2em',lookup:true,...safeRead('lectio.preferences',{})};
let catalogue=[],personal=[],book,data,page=0,openToken=0,lookupToken=0,downloadRunning=false,pause=false,observer,positionTimer,dbPromise,indexPromise;
const positions=safeRead('lectio.positions',{});let controls;
const navigate=async(id,target,anchor=0)=>{if(book?.id!==id)await openBook(id);if(book?.id!==id)throw Error('That saved text is unavailable.');page=Math.max(0,Math.min(target,data.pages.length-1));renderPage(anchor);};
function toast(s){$('toast').textContent=s;$('toast').style.display='block';clearTimeout(toast.timer);toast.timer=setTimeout(()=>$('toast').style.display='none',6500);}
function halt(){}
function show(id){if(!$(id).open){if(id==='wordDialog'&&innerWidth>=1000)$(id).show();else $(id).showModal();}}
function applyPrefs(){const r=document.documentElement;r.dataset.mode=prefs.theme;r.dataset.font=prefs.font;r.style.setProperty('--size',prefs.size?prefs.size+'px':'clamp(21px,5.5vw,25px)');r.style.setProperty('--leading',prefs.leading);$('fontOutput').textContent=prefs.size?prefs.size+' px':'Auto';$('fontSize').value=prefs.size||23;$('lineHeight').value=prefs.leading;$('fontFamily').value=prefs.font;document.querySelectorAll('[data-theme]').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.theme===prefs.theme)));save('lectio.preferences',prefs);controls?.preferences();}
function db(){return dbPromise??=new Promise((resolve,reject)=>{const r=indexedDB.open('lectio-personal',1);r.onupgradeneeded=()=>r.result.createObjectStore('texts',{keyPath:'id'});r.onsuccess=()=>resolve(r.result);r.onerror=()=>reject(r.error);});}
async function personalOp(mode,action){const d=await db();return new Promise((resolve,reject)=>{const t=d.transaction('texts',mode),r=action(t.objectStore('texts'));t.oncomplete=()=>resolve(r.result);t.onerror=()=>reject(t.error);t.onabort=()=>reject(t.error||Error('Import was not saved.'));});}
const allBooks=()=>[...catalogue,...personal];
function renderLibrary(){const q=normalize($('bookSearch').value),era=$('eraFilter').value;const books=allBooks().filter(b=>(era==='all'||b.era===era)&&($('authorFilter').value==='all'||b.author===$('authorFilter').value)&&($('shelfFilter').value==='all'||$('shelfFilter').value==='recent'&&!!positions[b.id]||$('shelfFilter').value==='favorites'&&controls.isFavorite(b.id))&&normalize(b.author+' '+b.title).includes(q)).sort((a,b)=>{const kind=$('librarySort').value;if(kind==='recent'){const recent=(positions[b.id]?.updated||0)-(positions[a.id]?.updated||0);if(recent)return recent;}if(kind==='length')return a.words-b.words;if(kind==='title')return a.title.localeCompare(b.title,undefined,{numeric:true});return a.author.localeCompare(b.author)||a.title.localeCompare(b.title,undefined,{numeric:true});});$('libraryCount').textContent=books.length.toLocaleString()+' texts and editions';$('bookList').replaceChildren();const batch=document.createDocumentFragment();for(const b of books){const button=el('button',undefined,'book-card');if(positions[b.id])button.append(el('small','Continue · passage '+(positions[b.id].page+1),'resume-label'));const provenance=b.collection?` · ${b.collection}`:'';button.append(el('span',b.author,'book-author'),el('strong',b.title),el('small',`${b.pages} passages · ${b.words.toLocaleString()} words${provenance}`));button.onclick=()=>{$('libraryDialog').close();openBook(b.id).catch(fail);};batch.append(button);}$('bookList').append(batch);if(!books.length)$('bookList').append(el('p','No texts match these filters. Try All authors and All texts.','muted'));}
function visibleParagraph(){return [...$('passage').children].findIndex(p=>p.getBoundingClientRect().bottom>Math.min(100,innerHeight/4));}
function remember(anchor=visibleParagraph()){if(book){positions[book.id]={page,anchor:Math.max(0,anchor),updated:Date.now()};save('lectio.positions',positions);save('lectio.last',book.id);const before=data.pages.slice(0,page).reduce((n,p)=>n+p.length,0),total=data.pages.reduce((n,p)=>n+p.length,0);const atEnd=page===data.pages.length-1&&scrollY+innerHeight>=document.documentElement.scrollHeight-12;const pct=atEnd?100:Math.round((before+Math.max(0,anchor))/total*100);$('progressText').textContent=pct+'%';$('bookProgress').value=pct;}}
function renderPage(anchor=0){
 observer?.disconnect();$('author').textContent=book.author;$('bookTitle').textContent=book.title;$('sectionTitle').textContent=`Passage ${page+1} of ${data.pages.length}`;$('chapterLabel').textContent=`${page+1} / ${data.pages.length}`;
 const pct=Math.round((page+1)/data.pages.length*100);$('progressText').textContent=pct+'%';$('bookProgress').value=pct;$('previous').disabled=page===0;$('next').disabled=page===data.pages.length-1;
 const frag=document.createDocumentFragment();data.pages[page].forEach((text,i)=>{const p=el('p');p.dataset.paragraph=i;
 for(const part of text.split(/([\p{L}\p{M}]+)/u)){if(/\p{L}/u.test(part)){const w=el('span',part,'word');w.tabIndex=frag.childNodes.length===0&&p.childNodes.length===0?0:-1;w.setAttribute('role','button');w.setAttribute('aria-label','Look up '+part);p.append(w);}else p.append(document.createTextNode(part));}frag.append(p);});$('passage').replaceChildren(frag);
 $('sourceNote').replaceChildren();if(book.source){$('sourceNote').append('Source: ');const a=el('a',book.collection||'The Latin Library');a.href=book.source;a.target='_blank';a.rel='noopener';$('sourceNote').append(a);if(book.editionDescription)$('sourceNote').append(' · '+book.editionDescription);}else $('sourceNote').textContent='Personal text · stored on this device';
 requestAnimationFrame(()=>{if(anchor>0)$('passage').children[Math.min(anchor,$('passage').children.length-1)]?.scrollIntoView({block:'start'});else window.scrollTo(0,0);});
 $('passage').querySelector('.word')?.setAttribute('tabindex','0');$('barPrevious').disabled=page===0;$('barNext').disabled=page===data.pages.length-1;remember(anchor);document.dispatchEvent(new CustomEvent('lectio:page'));
}
async function openBook(id){
 const turn=++openToken;halt();remember();const next=allBooks().find(b=>b.id===id)||catalogue.find(b=>b.id==='caesar--gall1');if(!next)throw Error('No books available.');
 const loaded=next.era==='Personal'?{pages:next.content}:await json(next.file);if(turn!==openToken)return;
 if(!loaded.pages?.length)throw Error('This source has no passages.');book=next;data=loaded;page=Math.min(positions[book.id]?.page||0,data.pages.length-1);renderPage(positions[book.id]?.anchor||0);
}
const dictionaryCache=new Map();
function dictionaryJSON(path){if(!dictionaryCache.has(path))dictionaryCache.set(path,json(path).catch(e=>{dictionaryCache.delete(path);throw e;}));return dictionaryCache.get(path);}
async function lookup(word){
 const turn=++lookupToken;$('selectedWord').textContent=word;$('lookupInput').value=word;$('definitions').replaceChildren();$('lookupStatus').textContent='Looking up…';show('wordDialog');$('wordDialog').scrollTop=0;document.dispatchEvent(new CustomEvent('lectio:lookup',{detail:{word}}));if(!word){$('lookupStatus').textContent='Enter a Latin word or headword. Macrons and u/v variants are accepted.';return;}
 try{indexPromise??=json('dictionary/index.json').catch(e=>{indexPromise=null;throw e;});const form=normalize(word);const [idx,morph]=await Promise.all([indexPromise,dictionaryJSON('morphology/'+shardFor(form)+'.json')]);const rows=candidates(word,idx,morph);
  const results=await Promise.all(rows.map(async([shard,id,head])=>({head,entry:(await dictionaryJSON('dictionary/'+shard+'.json'))[id]})));if(turn!==lookupToken)return;
  $('lookupStatus').textContent=results.length?`${results.length} possible headword${results.length===1?'':'s'}. These are candidates, not contextual parses.`:'No match in the supplied dictionary and word-form data. Try an edited headword.';
  for(const {head,entry} of results){
   if(!entry)continue;const d=el('section',undefined,'definition');
   const title=el('h3',entry.title_orthography||head);d.append(title);
   const direct=(idx[normalize(word)]||[]).some(row=>row[2]===head);d.append(el('p',direct?'Headword match':'Possible inflected-form or enclitic match','match-label'));const label=entryLabel(entry);if(label)d.append(el('p',label,'entry-label'));
   const forms=[entry.title_genitive,entry.title_infinitive].filter(Boolean);if(forms.length)d.append(el('p',forms.join(' · '),'entry-forms'));
   if(entry.main_notes)d.append(el('p',entry.main_notes,'entry-notes'));
   for(const sense of flatten(entry.senses))d.append(el('p',sense));
   const note=el('p','Lewis & Short · supplied Perseus digitization','entry-source');d.append(note);
   $('definitions').append(d);
  }
 }catch(e){if(turn===lookupToken)$('lookupStatus').textContent=e.message;}
}
function fail(e){console.error(e);toast(e.message||String(e));}
async function stats(){const s=await inventory();$('offlineStats').textContent=`${s.count.toLocaleString()} / ${s.total.toLocaleString()} files saved · ${(s.bytes/1e6).toFixed(1)} / ${(s.totalBytes/1e6).toFixed(1)} MB`;$('downloadProgress').value=s.bytes/s.totalBytes*100;return s;}
async function download(core=false,verify=false){
 if(downloadRunning)return;downloadRunning=true;pause=false;$('cancelDownload').hidden=false;for(const id of ['downloadAll','downloadCore','verifyOffline'])$(id).disabled=true;
 let done=0,failed=0,firstError='';
 try{await navigator.storage?.persist?.();const m=await manifest();const files=m.files.filter(f=>!core||!f.path.startsWith('texts/')||f.path==='texts/caesar--gall1.json');let cursor=0;
 const runner=async()=>{while(!pause&&cursor<files.length){const f=files[cursor++];try{await asset(f.path,{verify});done++;}catch(e){failed++;firstError||=e.message;}$('downloadStatus').textContent=`${verify?'Verifying':'Saving'}: ${done} / ${files.length} · ${failed} errors`;$('connection').textContent='Saving library · '+Math.round((done+failed)/files.length*100)+'%';}};
 await Promise.all([runner(),runner(),runner()]);const saved=await stats();$('connection').textContent=saved.count===saved.total?'Full library saved offline':'Library partially saved';$('downloadStatus').textContent=pause?'Paused. Start again to resume.':failed?`${failed} files could not be saved. ${firstError} Retry when available.`:`${verify?'Verified':'Saved and SHA-256 checked'} ${done} files. ${core?'Other books save when opened.':'The collection is available offline.'}`;
 }catch(e){$('downloadStatus').textContent=e.message;}finally{downloadRunning=false;$('cancelDownload').hidden=true;for(const id of ['downloadAll','downloadCore','verifyOffline'])$(id).disabled=false;}
}
document.querySelectorAll('dialog').forEach(d=>{d.addEventListener('click',e=>{if(e.target===d){const r=d.getBoundingClientRect();if(e.clientX<r.left||e.clientX>r.right||e.clientY<r.top||e.clientY>r.bottom)d.close();}});d.querySelector('.close')?.addEventListener('click',()=>d.close());const h=d.querySelector('h2');if(h){h.id||=d.id+'Title';d.setAttribute('aria-labelledby',h.id);}});
for(const id of ['libraryButton','backLibrary'])$(id).onclick=()=>{renderLibrary();show('libraryDialog');};$('settingsButton').onclick=()=>show('settingsDialog');$('offlineButton').onclick=()=>{show('offlineDialog');stats().then(()=>{if(!downloadRunning)$('downloadStatus').textContent='Choose what to save. Every saved file is checked against its SHA-256 hash.';}).catch(fail);};
$('bookSearch').oninput=renderLibrary;$('eraFilter').onchange=renderLibrary;for(const id of ['authorFilter','shelfFilter','librarySort'])$(id).onchange=renderLibrary;
$('previous').onclick=()=>{if(page>0){halt();page--;renderPage();}};$('next').onclick=()=>{if(page<data.pages.length-1){halt();page++;renderPage();}};
$('barPrevious').onclick=()=>$('previous').click();$('barNext').onclick=()=>$('next').click();
$('tocButton').onclick=()=>{if(!data)return;$('tocList').replaceChildren();for(let i=0;i<data.pages.length;i++){const b=el('button',String(i+1));b.setAttribute('aria-current',String(i===page));b.onclick=()=>{halt();page=i;renderPage();$('tocDialog').close();};const excerpt=data.pages[i].join(' ').replace(/\s+/g,' ').slice(0,95);b.textContent='Passage '+(i+1);b.append(el('small',excerpt+'…'));$('tocList').append(b);}show('tocDialog');};
function selectWord(w){document.querySelectorAll('.word.selected').forEach(n=>n.classList.remove('selected'));w.classList.add('selected');lookup(w.textContent);}
$('passage').onclick=e=>{const w=e.target.closest('.word');if(prefs.lookup!==false&&w&&getSelection().toString().trim().length===0)selectWord(w);};
$('passage').onkeydown=e=>{const w=e.target.closest('.word');if(!w||prefs.lookup===false)return;if(['Enter',' '].includes(e.key)){e.preventDefault();selectWord(w);}else if(['ArrowLeft','ArrowRight'].includes(e.key)){const words=[...$('passage').querySelectorAll('.word')],i=words.indexOf(w),next=words[i+(e.key==='ArrowRight'?1:-1)];if(next){e.preventDefault();w.tabIndex=-1;next.tabIndex=0;next.focus();}}};
$('lookupForm').onsubmit=e=>{e.preventDefault();lookup($('lookupInput').value.trim());};$('wordDialog').addEventListener('close',()=>{lookupToken++;document.querySelectorAll('.word.selected').forEach(n=>n.classList.remove('selected'));});
$('fontSize').oninput=()=>{prefs.size=Number($('fontSize').value);applyPrefs();};$('autoSize').onclick=()=>{prefs.size=null;applyPrefs();};
for(const [id,key] of [['lineHeight','leading'],['fontFamily','font']])$(id).onchange=()=>{halt();prefs[key]=$(id).value;applyPrefs();};
document.querySelectorAll('[data-theme]').forEach(b=>b.onclick=()=>{prefs.theme=b.dataset.theme;applyPrefs();});
$('downloadAll').onclick=()=>download();$('downloadCore').onclick=()=>download(true);$('verifyOffline').onclick=()=>download(false,true);$('cancelDownload').onclick=()=>{pause=true;$('downloadStatus').textContent='Pausing after current files finish…';};
$('importButton').onclick=()=>show('importDialog');$('importForm').onsubmit=async e=>{e.preventDefault();try{const file=$('importFile').files[0];if(file&&file.size>5_000_000)throw Error('Import text files up to 5 MB.');const text=file?new TextDecoder('utf-8',{fatal:true}).decode(await file.arrayBuffer()):$('importText').value;if(!text.trim())throw Error('Add some Latin text first.');if(text.length>5_000_000)throw Error('Import text files up to 5 MB.');const paragraphs=text.trim().replace(/\r/g,'').split(/\n\s*\n/),pages=[];let group=[],size=0;for(let p of paragraphs){while(p.length>6000){const cut=Math.max(p.lastIndexOf(' ',5500),4000);const part=p.slice(0,cut);p=p.slice(cut);if(group.length){pages.push(group);group=[];size=0;}pages.push([part]);}if(group.length&&size+p.length>8000){pages.push(group);group=[];size=0;}group.push(p);size+=p.length;}if(group.length)pages.push(group);const b={id:'personal-'+crypto.randomUUID(),title:$('importTitle').value.trim(),author:$('importAuthor').value.trim()||'Personal text',era:'Personal',pages:pages.length,words:text.split(/\s+/).length,content:pages};if(!b.title)throw Error('Enter a title.');await personalOp('readwrite',s=>s.put(b));personal.push(b);$('importDialog').close();$('libraryDialog').close();$('importForm').reset();await openBook(b.id);toast('Text saved on this device.');}catch(e){fail(e);}};
window.addEventListener('scroll',()=>{clearTimeout(positionTimer);positionTimer=setTimeout(()=>remember(),350);},{passive:true});window.addEventListener('pagehide',()=>{remember();halt();});
for(const event of ['online','offline'])window.addEventListener(event,()=>$('connection').textContent=navigator.onLine?'Your personal library':'Offline · saved files');
let installEvent;window.addEventListener('beforeinstallprompt',e=>{e.preventDefault();installEvent=e;$('installApp').hidden=false;});$('installApp').onclick=async()=>{await installEvent?.prompt();$('installApp').hidden=true;};
controls=setupReaderControls({state:()=>({book,data,page,prefs,positions}),anchor:visibleParagraph,navigate,lookup,show,toast,applyPrefs,personalTexts:()=>personalOp('readonly',s=>s.getAll())});
applyPrefs();
(async()=>{if(!isSecureContext)throw Error('Open Lectio through its local launcher or HTTPS; file:// and phone HTTP do not support offline installation.');
 if('serviceWorker'in navigator){let refreshing=false;const hadController=!!navigator.serviceWorker.controller;navigator.serviceWorker.addEventListener('controllerchange',()=>{if(hadController&&!refreshing){refreshing=true;remember();location.reload();}});}
 if('serviceWorker'in navigator)navigator.serviceWorker.register('./sw.js',{updateViaCache:'none'}).catch(e=>toast('Offline installation unavailable: '+e.message));
 [catalogue,personal]=await Promise.all([json('catalog.json'),personalOp('readonly',s=>s.getAll()).catch(e=>{toast('Personal storage unavailable: '+e.message);return [];})]);
 for(const author of [...new Set(catalogue.map(b=>b.author))].sort((a,b)=>a.localeCompare(b))){const o=el('option',author);o.value=author;$('authorFilter').append(o);}$('collectionSummary').textContent=`${catalogue.length.toLocaleString()} texts and editions · ${catalogue.filter(b=>b.era==='Humanist').length} Humanist & Neo-Latin · 51,596 dictionary entries`;
 await openBook(safeRead('lectio.last','caesar--gall1'));$('credits').textContent=await(await asset('licenses/ATTRIBUTIONS.txt')).text();
 if(['localhost','127.0.0.1'].includes(location.hostname)){const saved=await stats();if(saved.count<saved.total)download();else $('connection').textContent='Full library saved offline';}
})().catch(e=>{$('sectionTitle').textContent=e.message;fail(e);});
