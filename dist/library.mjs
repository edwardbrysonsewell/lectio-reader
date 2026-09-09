import {normalize} from './engine.mjs';
const cmp=(a,b)=>a.localeCompare(b,undefined,{numeric:true,sensitivity:'base'});
const roman=s=>{let n=0,last=0;for(const c of [...s.toUpperCase()].reverse()){const v={I:1,V:5,X:10,L:50,C:100,D:500,M:1000}[c]||0;n+=v<last?-v:v;last=Math.max(last,v);}return n;};
const authors={'Cicero, Marcus Tullius':'Cicero','P. Vergilius Maro (Virgil)':'Vergil','Virgil':'Vergil','Titus Livius (Livy)':'Livy','Tacitus, Cornelius':'Tacitus','Cornelius Tacitus':'Tacitus','Seneca, Lucius Annaeus':'Seneca the Younger','Gellius, Aulus':'Gellius','Propertius, Sextus':'Propertius','Pliny, the Elder':'Pliny the Elder'};
const rules=[
 [/^caesar--gall(\d+)$/, 'De bello Gallico','Book'],[/^caesar--bc(\d+)$/, 'De bello civili','Book'],
 [/^vergil--aen(\d+)$/, 'Aeneid','Book'],[/^vergil--geo(\d+)$/, 'Georgics','Book'],[/^vergil--ec(\d+)$/, 'Eclogues','Eclogue'],
 [/^livy--liv\.(\d+)$/, 'Ab urbe condita','Book'],[/^livy--liv\.per(\d+)$/, 'Periochae','Summary'],
 [/^pliny\.ep(\d+)$/, 'Letters','Book'],[/^pliny\.nh(\d+)$/, 'Natural History','Book'],
 [/^sen--seneca\.ep(\d+(?:-\d+)?)$/, 'Epistulae morales','Book'],
 [/^horace--carm(\d+)$/, 'Odes','Book'],[/^horace--epist(\d+)$/, 'Epistulae','Book'],[/^horace--serm(\d+)$/, 'Satires','Book'],
 [/^lucan--lucan(\d+)$/, 'Bellum civile','Book'],[/^lucretius--lucretius(\d+)$/, 'De rerum natura','Book'],
 [/^martial--mart(\d+)$/, 'Epigrams','Book'],[/^silius--silius(\d+)$/, 'Punica','Book'],[/^gellius--gellius(\d+)$/, 'Noctes Atticae','Book'],
 [/^(?:prop|propertius)(\d+)$/, 'Elegies','Book'],[/^tibullus(\d+)$/, 'Elegies','Book'],
 [/^descartes--des\.med(\d+)$/, 'Meditationes de prima philosophia','Meditation'],[/^spinoza\.ethica(\d+)$/, 'Ethica','Part'],
 [/^cicero--tusc(\d+)$/, 'Tusculan Disputations','Book'],[/^cicero--divinatione(\d+)$/, 'De divinatione','Book'],
 [/^cicero--verres\.2\.(\d+)$/, 'In Verrem','Second action · Book'],
 [/^statius--theb(\d+)$/, 'Thebaid','Book'],[/^statius--silvae(\d+)$/, 'Silvae','Book'],[/^statius--achilleid(\d+)$/, 'Achilleid','Book'],
 [/^quintilian--quintilian\.decl\.mai(\d+)$/, 'Declamationes maiores','Declamation'],
];
const aliases=Object.fromEntries(Object.entries({'the civil wars':'De bello civili','aeneis':'Aeneid','bucolica':'Eclogues','georgica':'Georgics','georgicon':'Georgics','ab urbe condita libri':'Ab urbe condita','ab urbe condita libri, erklärt von M. Weissenborn':'Ab urbe condita','philippic':'Philippicae','in l. catilinam':'In Catilinam','in c. verrem':'In Verrem','historiae':'Histories','de finibus bonorum et malorum':'De finibus','epistulae ad atticum':'Ad Atticum','epistulae ad familiares':'Ad Familiares','epistulae ad quintum fratrem':'Ad Quintum Fratrem','epistulae ad brutum':'Ad Brutum'}).map(([k,v])=>[normalize(k),v]));
export function describe(b){
 if(b.era==='Personal')return {author:b.author,title:b.title,part:'',order:0,key:'personal:'+b.id};
 let author=authors[b.author]||b.author,title=b.title.replace(/\s*· Perseus edition$/i,'').trim(),part='',order=0;
 // Explicit source identities resolve inconsistent or missing headings.
 for(const [pattern,work,unit] of rules){const m=b.id.match(pattern);if(m){title=work;part=unit+' '+m[1];order=parseInt(m[1]);break;}}
 if(!part){
  title=title.replace(/^(?:(?:Cicero|Ovid|Seneca|Livy|Tacitus|Horace|Lucretius|Statius|Erasmus|Eramus|Pliny the Elder|Pliny the Younger):\s*)+/i,'');
  const m=title.match(/^(.*?)\s+(?:(Book|Liber|Libri|Part|Volume)\s+)?([IVXLCDM]+|\d+)(?:\s*[-–&]\s*([IVXLCDM]+|\d+))?\s*$/);
  const idNumber=b.id.match(/(\d+)(?:-\d+)?$/);
  if(m&&m[1].trim()&&!b.collection&&(m[2]||idNumber&&Number(idNumber[1])===(/^\d+$/.test(m[3])?Number(m[3]):roman(m[3])))){title=m[1].replace(/[,·:]\s*$/,'').trim();part=(m[2]||'Part')+' '+m[3]+(m[4]?'–'+m[4]:'');order=/^\d+$/.test(m[3])?Number(m[3]):roman(m[3]);}
 }
 if(b.id==='livy--liv.pr'){title='Ab urbe condita';part='Preface';order=-1;}
 if(b.id==='pliny.nhpr'){title='Natural History';part='Preface';order=-1;}
 if(b.id==='livy--liv.per'){title='Periochae';part='Collected summaries';order=-1;}
 if(b.id==='cicero--ver1'){title='In Verrem';part='First action';order=-1;}
 title=aliases[normalize(title)]||title;
 return {author,title,part,order,key:b.era==='Personal'?'personal:'+b.id:normalize(author)+'|'+normalize(title)};
}
export function groupWorks(books){
 const groups=new Map();for(const b of books){const d=describe(b);if(!groups.has(d.key))groups.set(d.key,{...d,books:[]});groups.get(d.key).books.push({...b,libraryPart:d.part,libraryOrder:d.order});}
 // Identical uninformative headings in one source do not establish a shared work.
 const result=[];for(const g of groups.values()){
  if(g.books.length>1&&g.books.every(b=>!b.libraryPart)&&new Set(g.books.map(b=>b.collection||'Latin Library')).size===1){for(const b of g.books)result.push({...g,key:g.key+'|'+b.id,books:[b]});}
  else{g.books.sort((a,b)=>a.libraryOrder-b.libraryOrder||cmp(a.title,b.title));result.push(g);}
 }return result;
}
let view='works',selected=null,lastQuery='';
export function renderLibrary(api){
 const {$,el,allBooks,positions,isFavorite,openBook}=api;
 if(!$('libraryBrowse')){
  const nav=el('div',undefined,'library-browse');nav.id='libraryBrowse';
  for(const [mode,label] of [['works','Works'],['authors','Authors']]){const b=el('button',label,'quiet');b.dataset.browse=mode;b.onclick=()=>{view=mode;selected=null;renderLibrary(api);};nav.append(b);}
  const reset=el('button','Clear filters','quiet');reset.onclick=()=>{$('bookSearch').value='';for(const id of ['eraFilter','authorFilter','shelfFilter'])$(id).value='all';selected=null;renderLibrary(api);};nav.append(reset);
  $('bookList').before(nav);
 }
 const q=normalize($('bookSearch').value),era=$('eraFilter').value,author=$('authorFilter').value,shelf=$('shelfFilter').value;
 const signature=[q,era,author,shelf].join('|');if(signature!==lastQuery){selected=null;lastQuery=signature;}
 const eligible=allBooks().filter(b=>(era==='all'||b.era===era)&&(author==='all'||describe(b).author===author)&&(shelf==='all'||shelf==='recent'&&positions[b.id]||shelf==='favorites'&&isFavorite(b.id)));
 let groups=groupWorks(eligible).filter(g=>normalize(g.author+' '+g.title+' '+g.books.map(b=>b.title+' '+b.libraryPart).join(' ')).includes(q));
 const recent=g=>Math.max(0,...g.books.map(b=>positions[b.id]?.updated||0));
 groups.sort((a,b)=>{const sort=$('librarySort').value;if(sort==='recent'&&recent(a)!==recent(b))return recent(b)-recent(a);if(sort==='length')return a.books.reduce((n,b)=>n+b.words,0)-b.books.reduce((n,b)=>n+b.words,0);if(sort==='title')return cmp(a.title,b.title);return cmp(a.author,b.author)||cmp(a.title,b.title);});
 $('libraryBrowse').querySelectorAll('[data-browse]').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.browse===view)));
 const list=$('bookList');list.replaceChildren();
 const open=b=>{$('libraryDialog').close();openBook(b.id).catch(api.fail);};
 const card=b=>{const button=el('button',undefined,'book-card');button.dataset.bookId=b.id;button.append(el('strong',b.libraryPart||b.title.replace(/\s*· Perseus edition$/,'')),el('small',`${b.pages} passages · ${b.words.toLocaleString()} words`));if(positions[b.id])button.append(el('small','Continue · passage '+(positions[b.id].page+1),'resume-label'));button.onclick=()=>open(b);return button;};
 const current=groups.find(g=>g.key===selected);
 $('libraryDialog').classList.toggle('library-detail',!!current);
 if(current){
  const back=el('button','‹ Back to works','quiet');back.onclick=()=>{selected=null;renderLibrary(api);$('bookList').querySelector('button')?.focus();};list.append(back,el('p',current.author,'book-author'),el('h3',current.title));
  const latest=[...current.books].filter(b=>positions[b.id]).sort((a,b)=>positions[b.id].updated-positions[a.id].updated)[0];
  if(latest){const resume=el('button','Continue reading · '+(latest.libraryPart||latest.title),'primary');resume.onclick=()=>open(latest);list.append(resume);}
  const sources=new Map();for(const b of current.books){const source=b.collection||'The Latin Library';if(!sources.has(source))sources.set(source,[]);sources.get(source).push(b);}
  for(const [source,books]of [...sources].sort((a,b)=>(a[0]==='The Latin Library'?-1:b[0]==='The Latin Library'?1:cmp(a[0],b[0])))){list.append(el('h4',source));const parts=el('div',undefined,'work-parts');for(const b of books)parts.append(card(b));list.append(parts);}
  list.classList.add('work-detail');$('libraryCount').textContent=current.books.length+' available books / editions';
 }else{
  list.classList.remove('work-detail');
  if(view==='authors'){
   const byAuthor=new Map();for(const g of groups){if(!byAuthor.has(g.author))byAuthor.set(g.author,[]);byAuthor.get(g.author).push(g);}
   for(const [name,works] of [...byAuthor].sort((a,b)=>cmp(a[0],b[0]))){const b=el('button',undefined,'book-card');b.append(el('strong',name),el('small',works.length+' works / collections'));b.onclick=()=>{$('authorFilter').value=name;view='works';selected=null;renderLibrary(api);};list.append(b);}
   $('libraryCount').textContent=byAuthor.size+' authors';
  }else{
   for(const g of groups){const b=el('button',undefined,'book-card');b.dataset.workKey=g.key;b.append(el('span',g.author,'book-author'),el('strong',g.title),el('small',g.books.length>1?g.books.length+' books / editions · Browse ›':'Open text ›'));if(recent(g))b.append(el('small','Reading in progress','resume-label'));b.onclick=()=>{if(g.books.length===1)open(g.books[0]);else{selected=g.key;renderLibrary(api);$('libraryDialog').scrollTop=0;list.querySelector('button')?.focus();}};list.append(b);}
   $('libraryCount').textContent=groups.length.toLocaleString()+' works / collections · '+groups.reduce((n,g)=>n+g.books.length,0).toLocaleString()+' texts';
  }
  if(!groups.length)list.append(el('p','No matches. Try clearing the filters.','muted'));
 }
}
