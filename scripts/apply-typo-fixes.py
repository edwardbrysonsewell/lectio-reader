#!/usr/bin/env python3
"""Apply the edition-backed corrections from work/typo-candidates.tsv to the Latin Library texts.

Only the `edition` tier is applied. Each replacement keeps the source text's own letter
conventions (capitals, u/v, i/j) wherever the corrected word shares a letter with the old one.
Every change is recorded in corrections/latin-library-edition-fixes.tsv, which is enough to
reverse it.
"""
from pathlib import Path
from difflib import SequenceMatcher
import collections, csv, json, sys, unicodedata

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"
VOWELS = set("aeiouy")

def fold(c):
    c = unicodedata.normalize("NFD", c.lower())
    c = "".join(x for x in c if not unicodedata.combining(x))
    return {"j": "i", "v": "u", "æ": "ae", "œ": "oe"}.get(c, c)

def adapt(original, target):
    """Spell `target` (normalized letters, spaces allowed) using `original`'s characters where they agree."""
    chars, index = [], []
    for i, c in enumerate(original):
        for f in fold(c) if c.strip() else " ":
            chars.append(f); index.append(i)
    source = "".join(chars)
    out = []
    for tag, i1, i2, j1, j2 in SequenceMatcher(None, source, target, autojunk=False).get_opcodes():
        if tag == "equal":
            used = set()
            for k in range(i1, i2):
                c = original[index[k]]
                if len(fold(c)) > 1 or not c.strip():  # ligatures and spaces: take the corrected letters
                    out.append(target[j1 + k - i1])
                elif index[k] not in used:
                    out.append(c); used.add(index[k])
        elif tag in ("replace", "insert"):
            out.extend(target[j1:j2])
    fixed = list("".join(out))
    # A kept consonantal-style 'v' that now stands before a consonant or at the end is a vowel.
    for n, c in enumerate(fixed):
        if c in "vV" and (n + 1 == len(fixed) or fixed[n + 1].lower() not in VOWELS):
            fixed[n] = "u" if c == "v" else "U"
    if original[:1].isupper() and fixed and fixed[0].isalpha():
        fixed[0] = fixed[0].upper()
    return "".join(fixed)

def main():
    rows = [r for r in csv.DictReader(open(ROOT / "work/typo-candidates.tsv"), delimiter="\t") if r["evidence"].startswith("edition")]
    by_text = collections.defaultdict(list)
    for r in rows:
        by_text[r["text"]].append(r)
    log = []
    for text_id, fixes in sorted(by_text.items()):
        path = DIST / "texts" / (text_id + ".json")
        data = json.loads(path.read_text())
        # Apply right-to-left inside each paragraph so earlier offsets stay valid.
        for r in sorted(fixes, key=lambda r: (int(r["page"]), int(r["paragraph"]), -int(r["start"]))):
            pg, pa, s, e = int(r["page"]), int(r["paragraph"]), int(r["start"]), int(r["end"])
            para = data["pages"][pg][pa]
            old = para[s:e]
            new = adapt(old, r["proposed"])
            if not new or new == old:
                continue
            data["pages"][pg][pa] = para[:s] + new + para[e:]
            log.append((text_id, pg + 1, pa + 1, s, old, new, r["evidence"].split(":", 1)[1], r["kind"]))
        path.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")))
    out = ROOT / "corrections"; out.mkdir(exist_ok=True)
    log_path = out / "latin-library-edition-fixes.tsv"
    new_log = not log_path.exists()
    with log_path.open("a") as fh:
        w = csv.writer(fh, delimiter="\t", lineterminator="\n")
        if new_log:
            w.writerow(["text", "passage", "paragraph", "offset", "before", "after", "evidence_edition", "kind"])
        w.writerows(log)
    print(f"Applied {len(log)} corrections across {len(by_text)} texts.")

if __name__ == "__main__":
    sys.exit(main())
