#!/usr/bin/env python3
"""Find transcription errors in the Latin Library texts. Writes work/typo-candidates.tsv; changes nothing.

Evidence tiers
  edition  — the Latin Library form is not a known Latin form and occurs at most twice in the
             22-million-word corpus, and the aligned Perseus edition of the same work reads a known
             form within two letters (or the same letters with a different word division).
  neighbor — no edition evidence, but the form occurs once in the whole corpus, is unknown to the
             dictionary and morphology, and exactly one frequent known form lies one letter away.
Legitimate variant spellings (michi, nichil, quom…) are common in the corpus and are never proposed.
"""
from pathlib import Path
from difflib import SequenceMatcher
import collections, json, re, sqlite3, statistics, sys, unicodedata

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"
CORPUS = Path.home() / "latin_corpus_index.db"
WORD = re.compile(r"[^\W\d_]+")
LETTERS = "abcdefghiklmnopqrstuxyz"

def norm(s):
    s = unicodedata.normalize("NFD", s.lower().replace("æ", "ae").replace("œ", "oe"))
    return "".join(c for c in s if not unicodedata.combining(c)).replace("j", "i").replace("v", "u")

def tokens(text):
    return [(m.start(), m.end(), norm(m.group())) for m in WORD.finditer(text)]

def distance(a, b):
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]

ASSIMILATION = [("adf", "aff"), ("adl", "all"), ("adp", "app"), ("adc", "acc"), ("ads", "ass"), ("adt", "att"), ("adg", "agg"), ("adr", "arr"),
    ("conl", "coll"), ("conm", "comm"), ("conp", "comp"), ("conr", "corr"), ("inm", "imm"), ("inl", "ill"), ("inp", "imp"), ("inr", "irr"), ("inb", "imb"),
    ("subf", "suff"), ("subp", "supp"), ("subc", "succ"), ("obp", "opp"), ("obf", "off"), ("exs", "ex"), ("ii", "i"), ("ae", "e"), ("oe", "e"), ("y", "i"),
    ("ph", "f"), ("th", "t"), ("ch", "c"), ("mn", "m"), ("mpn", "mn"), ("michi", "mihi"), ("nichil", "nihil"), ("quom", "cum"), ("uo", "ue"), ("uu", "u"), ("k", "c")]

OCR = [("rn", "m"), ("nn", "m"), ("cl", "d"), ("li", "h"), ("ii", "n"), ("in", "m"), ("ni", "m"), ("tl", "d")]

def ocr_fold(w):
    """Undo one classic scanning confusion (rn read for m, cl for d …) if the word contains it."""
    for a, b in OCR:
        if a in w:
            return w.replace(a, b, 1)
    return w

def spelling_key(w):
    for a, b in ASSIMILATION:
        w = w.replace(a, b)
    return re.sub(r"(.)\1", r"\1", w)

def load_known():
    known = set(json.loads((DIST / "dictionary/index.json").read_text()))
    for f in (DIST / "morphology").glob("*.json"):
        known.update(json.loads(f.read_text()))
    return known

def main():
    known = load_known()
    db = sqlite3.connect(CORPUS)
    freq = dict(db.execute("select word,total_freq from corpus_freq"))
    bigram = lambda a, b: (db.execute("select coalesce(sum(frequency),0) from ngrams where n=2 and ngram=?", (a + " " + b,)).fetchone()[0])
    catalog = json.loads((DIST / "catalog.json").read_text())
    ll = [b for b in catalog if not b.get("collection")]
    ps = [b for b in catalog if b.get("collection")]

    # Sampled 4-word shingles locate each Latin Library text inside a Perseus edition.
    ptoks, index = [], collections.defaultdict(list)
    for pi, b in enumerate(ps):
        words = [t[2] for page in json.loads((DIST / b["file"]).read_text())["pages"] for p in page for t in tokens(p)]
        ptoks.append(words)
        for k in range(len(words) - 3):
            h = hash(tuple(words[k:k + 4]))
            if h % 4 == 0:
                index[h].append((pi, k))

    rows, matched = [], 0
    def is_known(w):
        if w in known:
            return True
        for tail in ("que", "ue", "ne", "ce", "st"):  # enclitics and prodelided est
            if w.endswith(tail) and len(w) > len(tail) + 1 and w[:-len(tail)] in known:
                return True
        return w.endswith("s") and w[:-1] in known and w[-2:-1] in "aeiou"  # prodelided es (factus's)
    def good(w):
        return is_known(w)
    def suspect(w, limit=2):
        return len(w) > 2 and not is_known(w) and freq.get(w, 0) <= limit
    def unword(w):
        return w not in ("a", "e", "o") and not is_known(w)

    for n, b in enumerate(ll):
        data = json.loads((DIST / b["file"]).read_text())
        flat = []  # (page, para, start, end, normalized)
        for pg, page in enumerate(data["pages"]):
            for pa, text in enumerate(page):
                flat.extend((pg, pa, s, e, w) for s, e, w in tokens(text))
        words = [x[4] for x in flat]
        hits = collections.defaultdict(list)
        sampled = 0
        for k in range(len(words) - 3):
            h = hash(tuple(words[k:k + 4]))
            if h % 4 == 0:
                sampled += 1
                for pi, pos in index.get(h, ()):
                    hits[pi].append(pos)
        edition_positions = set()
        if hits and sampled:
            pi, pos = max(hits.items(), key=lambda kv: len(kv[1]))
            if len(pos) / sampled >= 0.3:
                matched += 1
                pos.sort()
                lo = max(0, pos[int(len(pos) * 0.02)] - 400)
                hi = pos[min(len(pos) - 1, int(len(pos) * 0.98))] + 400
                other = ptoks[pi][lo:hi]
                sm = SequenceMatcher(None, words, other, autojunk=False)
                for tag, i1, i2, j1, j2 in sm.get_opcodes():
                    if tag != "replace":
                        continue
                    a, e = words[i1:i2], other[j1:j2]
                    fix = None
                    first, last = flat[i1], flat[i2 - 1]
                    para = data["pages"][first[0]][first[1]]
                    span = para[max(0, first[2] - 2):last[3] + 2]
                    after = para[last[3]:last[3] + 1]
                    if re.search(r"[\[\]<>⟨⟩{}]", span) or after in ("'", "’") or (i2 - i1 == 2 and para[flat[i1][3]:flat[i1 + 1][2]].strip()):
                        continue
                    capital = para[first[2]].isupper()
                    if len(a) == 1 and len(e) == 1 and suspect(a[0]) and good(e[0]) and spelling_key(a[0]) != spelling_key(e[0]):
                        d = distance(a[0], e[0])
                        if ocr_fold(a[0]) != a[0]:
                            d = min(d, max(1, distance(ocr_fold(a[0]), e[0])))
                        if (d == 1 or (d == 2 and len(a[0]) >= 7)) and (not capital or (d == 1 and freq.get(e[0], 0) >= 20)):
                            fix = ("replace", e[0])
                    elif len(a) == 2 and len(e) == 1 and a[0] + a[1] == e[0] and good(e[0]) and any(unword(x) and freq.get(x, 0) <= 2 for x in a):
                        fix = ("join", e[0])
                    elif len(a) == 1 and len(e) == 2 and a[0] == e[0] + e[1] and suspect(a[0]) and good(e[0]) and good(e[1]):
                        fix = ("split", e[0] + " " + e[1])
                    if fix:
                        rows.append((b["id"], first[0], first[1], first[2], last[3], "edition:" + ps[pi]["id"], fix[0], " ".join(a), fix[1]))
                        edition_positions.update(range(i1, i2))

        # Neighbor tier for every text, skipping forms already handled and capitalised names.
        for i, (pg, pa, s, e, w) in enumerate(flat):
            if i in edition_positions or not suspect(w, 1) or len(w) < 4:
                continue
            original = data["pages"][pg][pa][s:e]
            if original[0].isupper():
                continue
            cands = set()
            for k in range(len(w) + 1):
                for c in LETTERS:
                    cands.add(w[:k] + c + w[k:])
                    if k < len(w):
                        cands.add(w[:k] + c + w[k + 1:])
                if k < len(w):
                    cands.add(w[:k] + w[k + 1:])
                if k < len(w) - 1:
                    cands.add(w[:k] + w[k + 1] + w[k] + w[k + 2:])
            cands.discard(w)
            strong = [c for c in cands if c in known and freq.get(c, 0) >= 50]
            if len(strong) == 1:
                rows.append((b["id"], pg, pa, s, e, "neighbor", "replace", w, strong[0]))
        if n % 200 == 0:
            print(f"{n}/{len(ll)} texts · {matched} aligned · {len(rows)} candidates", file=sys.stderr, flush=True)

    out = ROOT / "work"; out.mkdir(exist_ok=True)
    with (out / "typo-candidates.tsv").open("w") as fh:
        fh.write("text\tpage\tparagraph\tstart\tend\tevidence\tkind\tfound\tproposed\n")
        for r in rows:
            fh.write("\t".join(map(str, r)) + "\n")
    tiers = collections.Counter(r[5].split(":")[0] for r in rows)
    print(f"Aligned {matched}/{len(ll)} Latin Library texts to a Perseus edition. Candidates: {dict(tiers)}")

if __name__ == "__main__":
    main()
