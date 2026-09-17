#!/usr/bin/env python3
"""Build Whitaker's Words short definitions for every word form in the library.

Sources: sources/whitaker/DICTLINE.json + INFLECTS.json (William Whitaker's
Words dictionary and inflection tables, as JSON). The parse is done here, once,
for each distinct word in dist/texts/, so the phone only loads small shards:

  dist/whitaker/forms/<letter>.json   normalized form -> [[entry, parse, parse…], …]
  dist/whitaker/entries-<n>.json      entry id -> [dictionary form, part of speech, age, senses]
  dist/whitaker/parses.json           parse id -> readable parse ("perfect active indicative, 3rd singular")
"""
from pathlib import Path
import json, re, unicodedata, collections

ROOT = Path(__file__).resolve().parents[1]
SRC, DIST = ROOT/'sources/whitaker', ROOT/'dist'
OUT = DIST/'whitaker'
SHARD = 4000

def norm(s):
    s = unicodedata.normalize('NFD', s.lower())
    s = ''.join(c for c in s if unicodedata.category(c) != 'Mn')
    return s.replace('æ', 'ae').replace('œ', 'oe').replace('j', 'i').replace('v', 'u')

# ---- dictionary: fold "|" continuation lines into the entry they continue
entries = []
for d in json.load(open(SRC/'DICTLINE.json')):
    senses = d['senses'].strip()
    if senses.startswith('|') and entries:
        entries[-1]['senses'] += ' ' + senses.lstrip('|').strip()
        continue
    entries.append({**d, 'senses': senses})
# Whitaker's Words builds "sum, esse, fui, futurus" into its program instead of DICTLINE;
# its endings (conjugation 5) are in INFLECTS. Sense wording here is Lectio's.
entries.append({'stems': ['s', '', 'fu', 'fut'], 'pos': 'V', 'conjugation': 5, 'conjugation_variant': 1, 'verb_kind': 'TO_BE',
                'age': 'X', 'area': 'X', 'geography': 'X', 'frequency': 'A', 'source': 'X',
                'senses': 'be, exist; (with a perfect participle) forms the perfect passive tenses'})

stem_index = collections.defaultdict(list)          # normalized stem -> [(entry id, stem number)]
for i, e in enumerate(entries):
    for n, s in enumerate(e['stems'], 1):
        if s not in ('NO_STEM', 'zzz'):
            stem_index[norm(s)].append((i, n))

inflects = json.load(open(SRC/'INFLECTS.json'))
ending_index = collections.defaultdict(list)
for f in inflects:
    ending_index['' if f['ending'] == 'NO_ENDING' else norm(f['ending'])].append(f)

WHICH = {'V': 'conjugation', 'N': 'declension', 'ADJ': 'declension', 'PRON': 'declension', 'NUM': 'declension', 'PACK': 'declension'}
INFL_POS = {'V': ('V', 'VPAR', 'SUPINE'), 'PACK': ('PRON',)}

def fits(e, f):
    pos = e['pos']
    if f['pos'] not in INFL_POS.get(pos, (pos,)):
        return False
    key = WHICH.get(pos)
    if key:
        fw, fv = f.get('conjugation', f.get('declension', 0)), f.get('conjugation_variant', f.get('declension_variant', 0))
        if fw not in (0, e[key]) or fv not in (0, e[key + '_variant']):
            return False
    if pos == 'N':
        fg, eg = f.get('gender', 'X'), e.get('gender', 'X')
        if not (fg == 'X' or eg == 'X' or fg == eg or (fg == 'C' and eg in 'MFC') or (eg == 'C' and fg in 'MF')):
            return False
    if pos == 'V' and f['pos'] == 'V':
        kind = e.get('verb_kind')
        if kind == 'DEP' and f.get('voice') == 'ACTIVE':
            return False
        if kind == 'SEMIDEP' and f.get('voice') == 'PASSIVE' and f.get('tense') in ('PERF', 'PLUP', 'FUTP'):
            pass
        if kind == 'IMPERS' and f.get('person') not in ('0', '3'):
            return False
    if pos == 'ADJ' and f['pos'] == 'ADJ' and e.get('comparison') not in ('X', 'POS', None):
        # comparative/superlative-only entries have one stem, used with any ending set
        return f.get('comparison') == e['comparison']
    return True

def tack_only(e):
    return (e['pos'] == 'PACK' and re.match(r'\(w/-\w+', e['senses'])) or re.match(r'\(w/-\w+ ONLY', e['senses'])

def raw_parses(form, entry_filter=None):
    found = []
    for k in range(len(form) + 1):
        stem, end = form[:k], form[k:]
        if not stem and not end:
            continue
        for f in ending_index.get(end, ()):
            for i, n in stem_index.get(stem, ()):
                if n != f['stem'] and not (entries[i]['pos'] == 'ADJ' and entries[i].get('comparison') not in ('X', 'POS') and n == 1):
                    continue
                e = entries[i]
                if entry_filter and not entry_filter(e):
                    continue
                if tack_only(e) and not entry_filter:
                    continue
                if fits(e, f):
                    found.append((i, f))
    return found

# ---- readable parses
LABEL = {'NOM': 'nominative', 'GEN': 'genitive', 'DAT': 'dative', 'ACC': 'accusative', 'ABL': 'ablative', 'VOC': 'vocative', 'LOC': 'locative',
         'S': 'singular', 'P': 'plural', 'M': 'masculine', 'F': 'feminine', 'N': 'neuter', 'C': 'common',
         'PRES': 'present', 'IMPF': 'imperfect', 'FUT': 'future', 'PERF': 'perfect', 'PLUP': 'pluperfect', 'FUTP': 'future perfect',
         'ACTIVE': 'active', 'PASSIVE': 'passive', 'IND': 'indicative', 'SUB': 'subjunctive', 'IMP': 'imperative', 'INF': 'infinitive',
         'COMP': 'comparative', 'SUPER': 'superlative', '1': '1st', '2': '2nd', '3': '3rd'}
POS_NAME = {'N': 'noun', 'ADJ': 'adjective', 'V': 'verb', 'ADV': 'adverb', 'PREP': 'preposition', 'CONJ': 'conjunction',
            'INTERJ': 'interjection', 'PRON': 'pronoun', 'PACK': 'pronoun', 'NUM': 'numeral'}

def parse_text(e, f, tackon=''):
    L = lambda *keys: ' '.join('masculine/feminine' if k == 'gender' and f[k] == 'C' else LABEL[f[k]]
                               for k in keys if f.get(k) not in (None, 'X', '0', 0))
    p = f['pos']
    if p == 'V':
        voice = 'deponent' if e.get('verb_kind') == 'DEP' else L('voice')
        s = ' '.join(x for x in (L('tense'), voice, L('mood')) if x)
        if f.get('person') not in (None, '0'):
            s += ', ' + L('person') + ' ' + L('number')
    elif p == 'VPAR':
        voice = 'deponent' if e.get('verb_kind') == 'DEP' else L('voice')
        s = ' '.join(x for x in (L('tense'), voice, 'participle') if x) + ', ' + L('case', 'number', 'gender')
    elif p == 'SUPINE':
        s = 'supine, ' + L('case')
    elif p == 'N':
        s = L('case', 'number')
    elif p in ('PRON', 'ADJ', 'NUM'):
        s = L('case', 'number', 'gender')
        if p == 'ADJ' and f.get('comparison') in ('COMP', 'SUPER'):
            s = L('comparison') + ', ' + s
    elif p == 'ADV' and f.get('comparison') in ('COMP', 'SUPER') and f['stem'] > 1:
        s = L('comparison')
    else:
        s = ''
    if tackon:
        s = (s + ' + ' if s else '') + '-' + tackon
    return s

# ---- dictionary forms (e.g. "amo, amare, amavi, amatus") generated from the same tables
def same(k, have, v):
    if k == 'gender':
        return have in ('X', v) or (have == 'C' and v in 'MF')
    return have == v

COMMON = [f for f in inflects if f['frequency'] in ('A', 'B') and f['age'] in ('X', 'C')]
COMMON.sort(key=lambda f: f.get('conjugation_variant', f.get('declension_variant', 0)) == 0)
ALL = sorted(inflects, key=lambda f: f.get('conjugation_variant', f.get('declension_variant', 0)) == 0)

def make(e, want):
    return make_from(e, want, COMMON) or make_from(e, want, ALL)

def make_from(e, want, rows):
    single = e['pos'] == 'ADJ' and e.get('comparison') not in ('X', 'POS', None)
    for f in rows:
        if all(same(k, f.get(k), v) for k, v in want.items()) and fits(e, f):
            n = 1 if single else f['stem']
            stem = e['stems'][n - 1] if n - 1 < len(e['stems']) else 'NO_STEM'
            if stem in ('NO_STEM', 'zzz'):
                return None
            return stem + ('' if f['ending'] == 'NO_ENDING' else f['ending'])
    return None

QUI = {'REL': 'qui, quae, quod', 'ADJECT': 'qui, quae, quod', 'INTERR': 'quis, quid', 'INDEF': 'quis, quid'}

def dictionary_form(e):
    p, st = e['pos'], e['stems']
    if p == 'V':
        kind = e.get('verb_kind')
        pers = '3' if kind == 'IMPERS' else '1'
        if kind == 'TO_BE':
            return 'sum, esse, fui, futurus'
        if kind == 'DEP':
            parts = [make(e, dict(pos='V', tense='PRES', voice='PASSIVE', mood='IND', person=pers, number='S')),
                     make(e, dict(pos='V', tense='PRES', voice='PASSIVE', mood='INF')),
                     make(e, dict(pos='VPAR', tense='PERF', case='NOM', number='S', gender='M'))]
            if parts[2]:
                parts[2] += ' sum'
        else:
            parts = [make(e, dict(pos='V', tense='PRES', voice='ACTIVE', mood='IND', person=pers, number='S')),
                     make(e, dict(pos='V', tense='PRES', voice='ACTIVE', mood='INF')),
                     make(e, dict(pos='V', tense='PERF', voice='ACTIVE', mood='IND', person=pers, number='S')),
                     make(e, dict(pos='VPAR', tense='PERF', voice='PASSIVE', case='NOM', number='S', gender='M'))
                     or make(e, dict(pos='VPAR', tense='FUT', voice='ACTIVE', case='NOM', number='S', gender='M'))]
        if not parts[0] and e['conjugation'] == 7 and e['conjugation_variant'] == 3:
            parts[0] = st[0] + 'o'                      # edo, esse (irregular "eat")
        parts = [x or '—' for x in parts]
        while parts and parts[-1] == '—':
            parts.pop()
    elif p == 'N':
        parts = [make(e, dict(pos='N', case='NOM', number='S')) or make(e, dict(pos='N', case='NOM', number='P')),
                 make(e, dict(pos='N', case='GEN', number='S')) or make(e, dict(pos='N', case='GEN', number='P'))]
    elif p == 'ADJ':
        comp = {'comparison': 'POS' if e.get('comparison') in ('X', 'POS') else e['comparison']}
        parts = [make(e, dict(pos='ADJ', case='NOM', number='S', gender=g, **comp)) for g in 'MFN']
    elif p in ('PRON', 'PACK') and e['declension'] == 1:
        # qui/quis family: Whitaker keeps only the stem "qu" and spreads the forms over variants
        kind = e.get('pronoun_kind') or e.get('packon_kind')
        prefix = st[0][:-2]
        base = QUI.get(kind, 'qui, quae, quod')
        tack = re.match(r'\(w/-(\w+)', e['senses']) if p == 'PACK' else None
        if tack and tack.group(1) == 'quam':
            base = 'quis, quid'
        parts = [prefix + x + (tack.group(1) if tack else '') for x in base.split(', ')]
    elif p == 'PRON' and e['stems'] == ['NO_STEM', 's']:
        parts = ['sui, sibi, se']
    elif p == 'PRON' and e['senses'].startswith('(w/-dem ONLY'):
        parts = ['idem, eadem, idem']
    elif p in ('PRON', 'PACK'):
        parts = [make(e, dict(pos='PRON', case='NOM', number='S', gender=g)) for g in 'MFN']
        if not any(parts):
            parts = [make(e, dict(pos='PRON', case='NOM', number='P', gender=g)) for g in 'MFN']
        if not any(parts):
            parts = [make(e, dict(pos='PRON', case='GEN', number='S', gender=g)) for g in 'MFN']
    elif p == 'NUM':
        sort = {'numeral_sort': 'CARD'}
        parts = [make(e, dict(pos='NUM', case='NOM', number='S', gender=g, **sort)) for g in 'MFN']
        if not any(parts):
            parts = [make(e, dict(pos='NUM', case='NOM', number='P', gender=g, **sort)) for g in 'MFN']
    else:
        parts = [st[0]]
    out = []
    for x in parts:
        if x and x not in out:
            out.append(x)
    head = ', '.join(out) or next((x for x in st if x not in ('NO_STEM', 'zzz', '')), '?')
    if p == 'N' and e.get('gender') in 'MFN':
        head += ' ' + e['gender'].lower() + '.'
    return head

# ---- words in the library
tokens = set()
for path in (DIST/'texts').glob('*.json'):
    for page in json.load(open(path))['pages']:
        for para in page:
            tokens.update(norm(w) for w in re.findall(r'[^\W\d_]+', para))
tokens.discard('')

ENCLITICS = ('que', 'ne', 'ue', 'cum')
PACKS = [(i, re.match(r'\(w/-(\w+)', e['senses']).group(1)) for i, e in enumerate(entries) if tack_only(e)]
SYNCOPE = [('asti', 'auisti'), ('astis', 'auistis'), ('arunt', 'auerunt'), ('ass', 'auiss'), ('aram', 'aueram'), ('arat', 'auerat'),
           ('arant', 'auerant'), ('arim', 'auerim'), ('arit', 'auerit'), ('arint', 'auerint'), ('aro', 'auero'),
           ('esti', 'euisti'), ('erunt', 'euerunt'), ('ess', 'euiss'), ('isti', 'iuisti'), ('iss', 'iuiss'), ('ier', 'iuer'),
           ('osti', 'ouisti'), ('oss', 'ouiss'), ('orunt', 'ouerunt')]

parse_ids, forms, canonical, head_cache = {}, {}, {}, {}
def heads(i):
    if i not in head_cache:
        head_cache[i] = dictionary_form(entries[i])
    return head_cache[i]
def pid(text):
    return parse_ids.setdefault(text, len(parse_ids))

def analyse(tok):
    hits = [(i, f, '') for i, f in raw_parses(tok)]
    if not hits:
        for suffix, full in SYNCOPE:
            at = tok.rfind(suffix)
            if at > 0:
                hits += [(i, f, '') for i, f in raw_parses(tok[:at] + full + tok[at + len(suffix):])
                         if f.get('tense') in ('PERF', 'PLUP', 'FUTP')]
    for i, tack in PACKS:
        if tok.endswith(tack) and len(tok) > len(tack):
            hits += [(j, f, '') for j, f in raw_parses(tok[:-len(tack)], lambda e, i=i: e is entries[i])]
    FREQ_RANK = 'ABCDEFI'
    if not hits or min(FREQ_RANK.find(entries[i]['frequency']) % 9 for i, _, _ in hits) >= 3:   # only rare whole-word readings
        for tack in ENCLITICS:
            if tok.endswith(tack) and len(tok) > len(tack) + 1:
                hits += [(i, f, tack if tack != 'ue' else 've') for i, f in raw_parses(tok[:-len(tack)])
                         if tack != 'cum' or f.get('case') == 'ABL']
    return hits

for tok in sorted(tokens):
    hits = analyse(tok)
    if not hits:
        continue
    grouped = collections.OrderedDict()
    for i, f, tack in hits:
        text = parse_text(entries[i], f, tack)
        e = entries[i]
        i = canonical.setdefault((heads(i), e['pos'], e['senses']), i)
        row = grouped.setdefault(i, [])
        p = pid(text)
        if p not in row:
            row.append(p)
    forms[tok] = [[i, *ps] for i, ps in grouped.items()]

used = sorted({i for rows in forms.values() for i, *_ in rows})
AGE = {'A': 'archaic', 'B': 'early', 'D': 'late', 'E': 'later', 'F': 'medieval', 'G': 'scholarly', 'H': 'modern'}

# ---- write
import shutil
shutil.rmtree(OUT, ignore_errors=True)
(OUT/'forms').mkdir(parents=True)
def write(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, separators=(',', ':')))
shards = collections.defaultdict(dict)
for tok, rows in forms.items():
    shards[tok[0] if 'a' <= tok[0] <= 'z' else '_'][tok] = rows
for letter, rows in shards.items():
    write(OUT/'forms'/f'{letter}.json', rows)
ebuckets = collections.defaultdict(dict)
FREQ = 'ABCDEFI'
for i in used:
    e = entries[i]
    ebuckets[i // SHARD][i] = [heads(i), POS_NAME.get(e['pos'], e['pos'].lower()), AGE.get(e['age'], ''),
                               re.sub(r'^\(w/-\w+( ONLY[^)]*)?\)\s*', '', re.sub(r'\s+', ' ', e['senses']).strip()).rstrip(';'), FREQ.find(e['frequency']) if e['frequency'] in FREQ else 9]
for b, rows in ebuckets.items():
    write(OUT/f'entries-{b}.json', rows)
write(OUT/'parses.json', [t for t, _ in sorted(parse_ids.items(), key=lambda kv: kv[1])])
size = sum(p.stat().st_size for p in OUT.rglob('*.json'))
print(f'{len(tokens):,} distinct words · {len(forms):,} parsed ({len(forms)/len(tokens):.0%}) · {len(used):,} entries · {len(parse_ids):,} parse labels · {size/1e6:.1f} MB')
