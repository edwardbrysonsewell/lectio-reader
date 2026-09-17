#!/usr/bin/env python3
"""Rebuild the Perseus Latin editions from the preserved canonical-latinLit archive.

Reading text only: editors' notes, apparatus readings, expansions and bibliographic
notes are left out; verse keeps its lines; the TEI book/poem/chapter structure sets
passage breaks and passage labels. Editorial brackets follow printed convention:
<del> -> [ ], <add>/<supplied> -> ⟨ ⟩, <gap> -> …. Catalogue ids are unchanged so
reading positions and bookmarks survive a rebuild.
"""
from pathlib import Path
from lxml import etree
import io, json, re, sys, tarfile

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"
ARCHIVE = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "sources/perseus-canonical.tar.gz"
COLLECTION = "Perseus Digital Library"
LB = " "  # internal line-break marker, turned into "\n" at the end
DIVS = {"div", "div1", "div2", "div3", "div4", "div5"}
SKIP = {"note", "rdg", "witDetail", "figure", "expan", "teiHeader", "interpGrp", "desc"}
BREAK_MILESTONES = {"card", "para", "paragraph", "section", "chapter"}
PAGE_CHARS = 8000
MINOR_LEVELS = {"section", "subsection", "line", "textpart"}
NAMED = {"pr": "Prologue", "prol": "Prologue", "arg": "Argument", "praef": "Preface", "pref": "Preface", "pra": "Preface"}

def local(node):
    return node.tag.rsplit("}", 1)[-1] if isinstance(node.tag, str) else ""

def ws(s):
    return re.sub(r"\s+", " ", s or "")

def inline(e):
    """Text of an element as a reader sees it (LB marks forced line breaks)."""
    t = local(e)
    if not t or t in SKIP:
        return ""
    if t == "choice":
        kids = {local(c): c for c in e if local(c)}
        for pref in ("corr", "abbr", "orig", "reg", "sic"):
            if pref in kids:
                return inline(kids[pref])
        return ""
    if t == "app":
        lem = next((c for c in e if local(c) == "lem"), None)
        return inline(lem) if lem is not None else ""
    if t == "gap":
        return " … "
    if t in ("lb", "space"):
        return " "
    if t in ("pb", "milestone"):
        return ""
    inner = ws(e.text) + "".join(inline(c) + ws(c.tail) for c in e)
    if t == "del":
        return "[" + inner.strip() + "]"
    if t in ("add", "supplied"):
        return "⟨" + inner.strip() + "⟩"
    if t == "bibl":
        return " (" + inner.strip() + ") "
    if t in ("l", "p", "ab", "speaker", "head", "stage", "lg", "sp", "argument", "label", "opener", "closer", "item"):
        return LB + inner.strip() + LB
    return inner

def finish(s):
    lines = [re.sub(r" +", " ", x).strip() for x in s.split(LB)]
    s = "\n".join(x for x in lines if x)
    s = re.sub(r" +([,.;:!?])", r"\1", s)
    s = re.sub(r"([(\[⟨]) +", r"\1", s)
    s = re.sub(r" +([)\]⟩])", r"\1", s)
    return s.strip()

def level_label(div):
    kind = div.get("subtype") or div.get("type") or ""
    if kind in ("edition", "translation", "commentary") or div.get("n") is None:
        return None
    kind = "" if kind == "textpart" else kind
    n = div.get("n").strip()
    if not re.fullmatch(r"\d+[a-z]?|[ivxlcdmIVXLCDM]+", n):
        if kind.lower() in MINOR_LEVELS or not kind:
            return NAMED.get(n.lower())
        return NAMED.get(n.lower(), n.capitalize())
    return (kind.capitalize() + " " + n).strip()

def collect(container, path, out):
    verse, numbers = [], []
    def flush():
        if verse:
            out.append((tuple(path), "\n".join(verse), (numbers[0], numbers[-1]) if numbers else None))
            verse.clear(); numbers.clear()
    for c in container:
        t = local(c)
        if not t or t in SKIP or t in ("pb", "lb", "bibl"):
            continue
        if t in DIVS:
            flush()
            head = next((h for h in c if local(h) == "head"), None)
            if (c.get("n") or "").lower() == "sigla" or (head is not None and finish(inline(head)).upper() == "SIGLA"):
                continue
            label = level_label(c)
            collect(c, path + [label] if label else path, out)
        elif t == "l":
            line = finish(inline(c)).replace("\n", " ")
            if line:
                verse.append(line)
                if re.fullmatch(r"\d+", c.get("n") or ""):
                    numbers.append(int(c.get("n")))
        elif t == "milestone":
            if c.get("unit") in BREAK_MILESTONES:
                flush()
        else:
            flush()
            text = finish(inline(c))
            if text:
                ns = [int(l.get("n")) for l in c.iter() if local(l) == "l" and re.fullmatch(r"\d+", l.get("n") or "")]
                out.append((tuple(path), text, (ns[0], ns[-1]) if ns else None))
    flush()

def split_long(text):
    if len(text) <= 6000:
        return [text]
    units = text.split("\n") if "\n" in text else re.split(r"(?<=[.!?;])\s+", text)
    joiner = "\n" if "\n" in text else " "
    out, buf = [], ""
    for u in units:
        while len(u) > 6000:
            cut = u.rfind(" ", 0, 5500)
            cut = cut if cut > 3500 else 5500
            if buf:
                out.append(buf); buf = ""
            out.append(u[:cut].strip()); u = u[cut:].strip()
        if buf and len(buf) + len(u) > 5500:
            out.append(buf); buf = ""
        buf = (buf + joiner + u) if buf else u
    if buf:
        out.append(buf)
    return out

def major_levels(path):
    return [p for p in path if p.split(" ")[0].lower() not in MINOR_LEVELS and not re.fullmatch(r"\d+[a-z]?", p)]

def label_for(path):
    major = [p for i, p in enumerate(major_levels(path)) if i == 0 or p != major_levels(path)[i - 1]]
    if major:
        minor = [x for x in path if x.split(" ")[0].lower() == "section" and re.fullmatch(r"\d+[a-z]?", x.split(" ")[-1])]
        if len(major) == 1 and minor and not major[0].lower().startswith("chapter"):
            return major[0] + " · § " + minor[-1].split(" ")[-1]
        return " · ".join(major[:2])
    return "§ " + path[-1].split(" ")[-1] if path else ""

def range_label(first, last):
    a, b = label_for(first), label_for(last)
    if not a or a == b:
        return a
    ha, hb = a.rsplit(" ", 1), b.rsplit(" ", 1)
    if len(ha) == 2 and len(hb) == 2 and ha[0] == hb[0]:
        return ha[0] + " " + ha[1] + "–" + hb[1]
    return a + " – " + b

def paginate(blocks):
    pages, labels, page, size, first = [], [], [], 0, None
    last, lines = None, []
    def close():
        label = range_label(first, last)
        if lines and lines[0] <= lines[-1]:
            label = (label + " · " if label else "") + (f"lines {lines[0]}–{lines[-1]}" if lines[0] != lines[-1] else f"line {lines[0]}")
        pages.append(page[:]); labels.append(label)
    for path, text, numbers in blocks:
        for part in split_long(text):
            top = major_levels(path)[:1]
            if page and (size + len(part) > PAGE_CHARS or major_levels(first)[:1] != top):
                close(); page.clear(); size = 0; first = None; lines.clear()
            if first is None or not first or (len(path) > len(first) and path[:len(first)] == first):
                first = path
            if numbers:
                if not lines: lines.append(numbers[0])
                lines[1:] = [numbers[1]]
            page.append(part); size += len(part); last = path
    if page:
        close()
    return pages, labels

def parse(data):
    return etree.parse(io.BytesIO(data), etree.XMLParser(load_dtd=False, no_network=True, recover=True, huge_tree=True)).getroot()

def main():
    catalogue = json.loads((DIST / "catalog.json").read_text())
    existing = {b["id"]: b for b in catalogue if b.get("collection") == COLLECTION}
    keep = [b for b in catalogue if b.get("collection") != COLLECTION]
    rebuilt, report = [], []
    with tarfile.open(ARCHIVE) as tf:
        files = {m.name: m for m in tf.getmembers() if m.isfile()}
        by_id = {"perseus--" + Path(n).stem: n for n in files if re.search(r"-lat\d+\.xml$", n) and not Path(n).name.startswith("._")}
        for ident, entry in existing.items():
            name = by_id.get(ident)
            if not name:
                raise SystemExit("Source TEI missing for " + ident)
            root = parse(tf.extractfile(files[name]).read())
            body = root.xpath('//*[local-name()="body"]')[0]
            blocks = []
            collect(body, [], blocks)
            pages, labels = paginate(blocks)
            words = len(re.findall(r"\b\w+\b", " ".join(p for page in pages for p in page)))
            (DIST / "texts" / (ident + ".json")).write_text(json.dumps({"id": ident, "pages": pages, "labels": labels}, ensure_ascii=False, separators=(",", ":")))
            rebuilt.append({**entry, "pages": len(pages), "words": words, "verse": any("\n" in p for page in pages for p in page)})
            report.append((ident, entry["words"], words, entry["pages"], len(pages)))
    (DIST / "catalog.json").write_text(json.dumps(keep + rebuilt, ensure_ascii=False, separators=(",", ":")))
    out = ROOT / "work"; out.mkdir(exist_ok=True)
    (out / "perseus-rebuild-report.tsv").write_text("id\told_words\tnew_words\told_pages\tnew_pages\n" + "\n".join("\t".join(map(str, r)) for r in report) + "\n")
    print(f"Rebuilt {len(rebuilt)} Perseus editions; words {sum(r[1] for r in report):,} -> {sum(r[2] for r in report):,}")

if __name__ == "__main__":
    main()
