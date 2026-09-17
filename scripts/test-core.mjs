import fs from 'node:fs';import assert from 'node:assert/strict';import crypto from 'node:crypto';
import {normalize,candidates,flatten,shardFor,entryLabel} from '../dist/engine.mjs';
const root=new URL('../dist/',import.meta.url),read=p=>JSON.parse(fs.readFileSync(new URL(p,root)));
const catalog=read('catalog.json');assert.equal(catalog.length,2328);assert.equal(catalog.filter(b=>b.collection==='Perseus Digital Library').length,345);assert.equal(new Set(catalog.map(b=>b.id)).size,catalog.length);
for(const b of catalog){const d=read(b.file);assert.equal(d.id,b.id);assert.equal(d.pages.length,b.pages);assert(d.pages.every(p=>p.length&&p.every(t=>typeof t==='string'&&t.length)));}
const caesar=read('texts/caesar--gall1.json');assert(caesar.pages[0].join(' ').includes('Gallia est omnis divisa'));
const erasmus=catalog.find(b=>b.id==='erasmus--coll');assert.equal(erasmus.title,'In primo congressu (selection)');assert(read(erasmus.file).pages.flat().join(' ').includes('Salve pater, salve matercula'));
assert(read('texts/vergil--aen1.json').pages.flat().some(p=>p.includes('Arma virumque')&&p.includes('\nItaliam')));
const index=read('dictionary/index.json');
for(const [form,lemma] of Object.entries({omnis:'omnis',partes:'pars',quarum:'qui',incolunt:'incolo',civitati:'civitas','amābāmus':'amo',hostibus:'hostis',fuisset:'sum',armaque:'arma'})){
 const m=read('morphology/'+shardFor(normalize(form))+'.json');const found=candidates(form,index,m);assert(found.some(([s,id])=>normalize(read('dictionary/'+s+'.json')[id].key).replace(/\d+$/,'')===normalize(lemma)),form+' → '+lemma);
}
let count=0;for(const f of fs.readdirSync(new URL('dictionary/',root)).filter(f=>f!== 'index.json')){const rows=read('dictionary/'+f);count+=Object.keys(rows).length;for(const row of Object.values(rows)){const values=flatten(row.senses);assert(values.every(x=>typeof x==='string'));}}assert.equal(count,51596);
assert.deepEqual(flatten(['a',['b',['c']]]),['a','b','c']);assert.equal(normalize('JŪLĬVS Æ Œ'),'iulius ae oe');
const conor=read('dictionary/c.json')['c-4461'];assert.equal(entryLabel(conor),'Deponent verb');assert.equal(conor.part_of_speech,'noun');
let conflicts=0;for(const file of fs.readdirSync(new URL('dictionary/',root)).filter(f=>f!=='index.json'))for(const row of Object.values(read('dictionary/'+file))){if(entryLabel(row)&&row.part_of_speech==='noun'){assert(!entryLabel(row).toLowerCase().includes('noun'));conflicts++;}}assert.equal(conflicts,14);console.log('PASS: all 14 detected noun/verb metadata conflicts handled.');
const manifest=read('offline-manifest.json');for(const f of manifest.files){const b=fs.readFileSync(new URL(f.path,root));assert.equal(b.length,f.bytes,f.path);assert.equal(crypto.createHash('sha256').update(b).digest('hex'),f.sha256,f.path);}
console.log('PASS: 2,328 texts/editions including 345 Perseus editions, Caesar, Erasmus, verse breaks, 51,596 entries, nine morphology cases, corrected conor presentation, and '+manifest.files.length+' offline file hashes.');
