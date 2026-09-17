#!/usr/bin/env python3
"""Rebuild local data from the preserved archives; never download or execute sources."""
import ast, collections, hashlib, json, re, shutil, struct, tarfile, unicodedata, zlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; DIST=ROOT/'dist'
def write(path,obj):
 p=DIST/path;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(obj,ensure_ascii=False,separators=(',',':')))
def norm(s):
 return ''.join(c for c in unicodedata.normalize('NFD',s.lower().replace('æ','ae').replace('œ','oe')) if not unicodedata.combining(c)).replace('j','i').replace('v','u')
CLASSICAL=set('andronicus apicius apuleius asconius caesar calpurniusflaccus calpurniussiculus carmenarvale carmensaliare cato catullus censorinus cicero cinna claud columella curtius enn frontinus fronto gaius gellius germanicus grattius horace hyginus inscriptions juvenal livy lucan lucretius manilius martial minucius naevius nepos ovid persius petronius petroniusfrag phaedr phaedrapp plautus pliny pomponius priapea prop propertius quintilian resgestae rhetores rutiliuslupus sall scbaccanalibus sen seneca silius statius suetonius sulpicia syrus tacitus ter tibullus valeriusflaccus valmax varro vell vergil vitruvius 12tables'.split())
HUMANIST=set('addison albertofaix bacon balde bebel biggs boskovic buchanan bultelius campion celtis columbus corvinus cotta declaratio descartes erasmus ferraria ficino fletcher forsett galileo garcilaso gauss gwinne halley holberg iabervocius janus jfkhonor kepler landor lhomond lotichius luther marullo marx may melanchthon milton mirandola montanus more navagero newton owen paris pascoli passerat petrarch petrarchmedicus piccolomini poggio pontano poree rimbaud ruaeus sabinus sannazaro scaliger scottus smarius tunger vegius vico vida waardenburg walton withof xylander zonaras'.split())
VERSE=set('vergil horace ovid catullus lucretius martial juvenal silius statius lucan tibullus prop propertius phaedr phaedrapp persius valeriusflaccus manilius grattius germanicus plautus ter'.split())
NAMES={'caesar':'Julius Caesar','cicero':'Cicero','vergil':'Vergil','horace':'Horace','ovid':'Ovid','livy':'Livy','sen':'Seneca the Younger','seneca':'Seneca the Elder','sall':'Sallust','ter':'Terence','prop':'Propertius','phaedr':'Phaedrus','phaedrapp':'Phaedrus','valmax':'Valerius Maximus','vell':'Velleius Paterculus','enn':'Ennius','mirandola':'Pico della Mirandola','more':'Thomas More','erasmus':'Erasmus','petrarchmedicus':'Petrarch','petrarch':'Petrarch','piccolomini':'Aeneas Silvius Piccolomini','ficino':'Marsilio Ficino','poggio':'Poggio Bracciolini','bacon':'Francis Bacon','descartes':'René Descartes','spinoza':'Baruch Spinoza','newton':'Isaac Newton','pliny':'Pliny','12tables':'Twelve Tables'}
HUMANIST.add('spinoza')
FOOTERS={'the latin library','the classics page','classics page','christian latin','medieval latin','neo-latin','the latin library.'}
def split_long(p,verse):
 if len(p)<=6000:return [p]
 units=p.splitlines(keepends=True) if verse else re.split(r'(?<=[.!?;])\s+',p)
 out=[];buf=''
 for u in units:
  if len(buf)+len(u)>5500 and buf:out.append(buf.strip());buf=''
  # Bound a paragraph without sentence punctuation, preserving every word.
  while len(u)>6000:
   cut=u.rfind(' ',0,5500);cut=cut if cut>0 else 5500
   if buf:out.append(buf.strip());buf=''
   out.append(u[:cut].strip());u=u[cut:]
  buf+=u+('' if verse else ' ')
 if buf.strip():out.append(buf.strip())
 return out
catalog=[];excluded=[]
with tarfile.open(ROOT/'sources/corpus.tar.gz') as t:
 for m in sorted(t.getmembers(),key=lambda m:m.name):
  rel=m.name.split('/',1)[-1]
  if rel=='LICENSE.md':
   (DIST/'licenses').mkdir(exist_ok=True);(DIST/'licenses/CORPUS.txt').write_bytes(t.extractfile(m).read())
  if not m.isfile() or not rel.endswith('.txt'):continue
  raw=t.extractfile(m).read();txt=raw.decode('utf-8-sig')
  if Path(rel).name in ('index.txt','indices.txt') or len(raw)<1200 or len(re.findall(r'\b\w+\b',txt))<100:
   excluded.append(rel);continue
  prefix=re.split(r'[/\.\d]',rel)[0] or Path(rel).stem
  verse=prefix in VERSE or (prefix=='sen' and re.search(r'hercules|medea|phaedra|thyestes|troades|oedipus|agamemnon|phoenissae|octavia',rel) is not None)
  chunks=[x.strip() for x in re.split(r'\n\s*\n',txt.replace('\r','')) if x.strip()]
  title=' '.join(chunks[0].split());paras=[]
  for p in chunks[1:]:
   p='\n'.join(line.strip() for line in p.splitlines()).strip() if verse else ' '.join(p.split())
   low=p.lower()
   if not p or low in FOOTERS or (len(p)<180 and 'the latin library' in low and 'the classics page' in low) or re.fullmatch(r'[\d\s.,|\[\]()–—-]+',p):continue
   if paras and p==paras[-1]:continue
   if norm(p)==norm(title):continue
   paras.extend(split_long(p,verse))
  if not paras:excluded.append(rel);continue
  pages=[];page=[];size=0
  for p in paras:
   if page and size+len(p)>8000:pages.append(page);page=[];size=0
   page.append(p);size+=len(p)
  if page:pages.append(page)
  id=rel[:-4].replace('/','--');author=NAMES.get(prefix,prefix.replace('_',' ').capitalize())
  if rel.startswith('caesar/gall'):title='De bello Gallico · Book '+re.search(r'gall(\d+)',rel)[1]
  if rel.startswith('vergil/aen'):title='Aeneid · Book '+re.search(r'aen(\d+)',rel)[1]
  if rel.startswith('pliny.ep'):author='Pliny the Younger';title='Letters · Book '+re.search(r'ep(\d+)',rel)[1]
  if rel.startswith('pliny.nh'):author='Pliny the Elder'
  if rel=='erasmus/coll.txt':title='In primo congressu (selection)'
  if rel=='erasmus/ep.txt':title='Scripta selecta'
  file=f'texts/{id}.json';write(Path(file),{'id':id,'pages':pages})
  catalog.append(dict(id=id,author=author,title=title,era='Classical' if prefix in CLASSICAL else 'Humanist' if prefix in HUMANIST else 'Later',file=file,pages=len(pages),verse=bool(verse),words=len(re.findall(r'\b\w+\b',' '.join(paras))),source='https://www.thelatinlibrary.com/'+rel[:-4]+'.html'))
write(Path('catalog.json'),catalog)
index=collections.defaultdict(list);entries=0
with tarfile.open(ROOT/'sources/dictionary.tar.gz') as t:
 for m in sorted(t.getmembers(),key=lambda m:m.name):
  if not re.search(r'/ls_\w+\.json$',m.name):continue
  shard=Path(m.name).stem[3:].lower();rows=json.load(t.extractfile(m));data={}
  for i,row in enumerate(rows):
   id=f'{shard}-{i}';data[id]=row;entries+=1
   key=re.sub(r'\d+$','',norm(row['key']));index[key].append([shard,id,row.get('title_orthography') or row['key']])
  write(Path(f'dictionary/{shard}.json'),data)
write(Path('dictionary/index.json'),index)
tree=ast.parse((ROOT/'sources/latin_lemmata_cltk.py').read_text());mapping=ast.literal_eval(next(n.value for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(x,ast.Name) and x.id=='LEMMATA' for x in n.targets)))
morph=collections.defaultdict(lambda:collections.defaultdict(set))
for form,lemmas in mapping.items():
 form=norm(form)
 for lemma in ([lemmas] if isinstance(lemmas,str) else lemmas):morph[form[0] if form and form[0] in 'abcdefghijklmnopqrstuvwxyz' else '_'][form].add(re.sub(r'\d+$','',norm(lemma)))
for shard,rows in morph.items():write(Path(f'morphology/{shard}.json'),{k:sorted(v) for k,v in rows.items()})
shutil.copy2(ROOT/'sources/cltk-license',DIST/'licenses/MORPHOLOGY.txt')
(DIST/'licenses/ATTRIBUTIONS.txt').write_text('''Lectio reconstruction, 6 September 2026. All processing is local.
Corpus: The Latin Library via CLTK lat_text_latin_library source snapshot.
https://github.com/cltk/lat_text_latin_library
Source license: Public Domain Mark 1.0 (see CORPUS.txt).
Modified: whitespace cleanup, paragraph segmentation, broad navigation labels and catalogue titles. Source spellings retained. These are source files/books, not a count of complete works; fragments, selections and editorial material occur. The Later filter includes unclassified material. No complete-corpus claim.
Dictionary: Charlton T. Lewis and Charles Short, A Latin Dictionary (1879).
Perseus Digital Library digitization, with funding from the National Endowment for the Humanities; JSON conversion by IohannesArnold.
https://github.com/IohannesArnold/lewis-short-json
https://www.perseus.tufts.edu/
Dictionary and transformed dictionary data: Creative Commons Attribution-ShareAlike 3.0.
https://creativecommons.org/licenses/by-sa/3.0/
Modified: alphabetical shards, stable IDs and normalized lookup index; all supplied entry fields and nested senses retained. Digitization errors may remain.
Morphology: CLTK lat_models_cltk, MIT (see MORPHOLOGY.txt).
https://github.com/cltk/lat_models_cltk
Modified: lookup normalization and lemma suffix removal. Candidates are not contextual parses.
Reading-only release: speech removed. Original model assets preserved in source recovery and Git. Dictionary presentation omits unreliable converter grammatical fields. All supplied senses retained.
''')
# Self-contained PNG icons, drawn as a simple book mark without external dependencies.
def icon(n):
 rows=[]
 for y in range(n):
  row=bytearray()
  for x in range(n):
   ink=(n*.28<x<n*.39 and n*.23<y<n*.75) or (n*.28<x<n*.74 and n*.64<y<n*.75)
   row.extend((248,249,247) if ink else (21,60,56))
  rows.append(b'\0'+row)
 def chunk(k,v):return struct.pack('!I',len(v))+k+v+struct.pack('!I',zlib.crc32(k+v)&0xffffffff)
 return b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('!2I5B',n,n,8,2,0,0,0))+chunk(b'IDAT',zlib.compress(b''.join(rows)))+chunk(b'IEND',b'')
for n in (192,512):(DIST/f'icon-{n}.png').write_bytes(icon(n))
(DIST/'icon.svg').write_text('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 192 192"><rect width="192" height="192" rx="24" fill="#153c38"/><path d="M55 44h20v80h65v21H55z" fill="#f8f9f7"/></svg>')
write(Path('manifest.webmanifest'),{'name':'Lectio · Bibliotheca Latina','short_name':'Lectio','id':'./','start_url':'./','scope':'./','display':'standalone','background_color':'#f8f9f7','theme_color':'#153c38','icons':[{'src':f'icon-{n}.png','sizes':f'{n}x{n}','type':'image/png','purpose':'any maskable'} for n in (192,512)]})
summary={'sourceFiles':len(catalog),'words':sum(b['words'] for b in catalog),'eras':{e:{'files':sum(b['era']==e for b in catalog),'words':sum(b['words'] for b in catalog if b['era']==e)} for e in ('Classical','Humanist','Later')},'dictionaryEntries':entries,'sourceMorphologyMappings':len(mapping),'excludedFiles':excluded}
write(Path('build-report.json'),summary)
print(json.dumps({k:v for k,v in summary.items() if k!='excludedFiles'},indent=2))
