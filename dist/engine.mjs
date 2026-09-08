export const normalize=s=>s.toLowerCase().normalize('NFD').replace(/\p{M}/gu,'').replace(/æ/g,'ae').replace(/œ/g,'oe').replace(/j/g,'i').replace(/v/g,'u');
export const lemmaKey=s=>normalize(s).replace(/\d+$/,'');
export const shardFor=s=>/^[a-z]/.test(s)?s[0]:'_';
export function candidates(word,index,morph={}) {
 const form=normalize(word), forms=[form];
 for(const suffix of ['que','ue','ne'])if(form.endsWith(suffix)&&form.length>suffix.length+1)forms.push(form.slice(0,-suffix.length));
 const result=new Map();
 for(const f of forms)for(const key of [f,...(morph[f]||[])])for(const row of index[lemmaKey(key)]||[])result.set(row[1],row);
 return [...result.values()];
}
export function flatten(value){return Array.isArray(value)?value.flatMap(flatten):value&&typeof value==='object'?Object.entries(value).flatMap(([k,v])=>[k,...flatten(v)]):value==null?[]:[String(value)];}

// Supplied grammatical metadata can describe a later substantivized sense.
// Prefer the entry's explicit opening description; do not print unreliable raw fields.
export function entryLabel(entry){
 const opening=[entry.main_notes||'',...flatten(entry.senses).slice(0,1)].join(' ').trim();
 if(/^V\.\s*dep\./i.test(opening))return 'Deponent verb';
 if(/^V\.\s*a\./i.test(opening))return 'Transitive verb';
 if(/^V\.\s*n\./i.test(opening))return 'Intransitive verb';
 return '';
}
