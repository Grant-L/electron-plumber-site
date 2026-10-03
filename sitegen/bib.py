"""A BibTeX subset, enough for the notes repo's published sources.bib. No dependencies.

The notes repo publishes citation fields only (no note-style fields, no % lines), and the site's copy adds one
header line naming the notes commit it came from. Supported: @type{key, field = {value} | "value" | 1234, ...},
brace-balanced values, TeX accents such as {\\"U} and {\\'e}, a few named letters, escaped specials, -- and ---,
and inline math such as $g-2$. Anything else is an error rather than a silent mis-render, as in md.py.
"""
import re
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path

HEADER = re.compile(r"^% Copied from Grant-L/electron-plumber-notes sources\.bib at commit ([0-9a-f]{40})\.")
UNSUPPORTED_TYPES = {"string", "preamble", "comment"}
RAW_FIELDS = {"doi", "url", "eprint"}  # identifiers: braces and \_ are undone, nothing else is interpreted

ACCENTS = {'"': "\u0308", "'": "\u0301", "`": "\u0300", "^": "\u0302", "~": "\u0303", "=": "\u0304", ".": "\u0307",
           "u": "\u0306", "v": "\u030c", "H": "\u030b", "c": "\u0327", "k": "\u0328", "r": "\u030a", "d": "\u0323",
           "b": "\u0331"}
LETTERS = {"ss": "\u00df", "o": "\u00f8", "O": "\u00d8", "aa": "\u00e5", "AA": "\u00c5", "ae": "\u00e6", "AE": "\u00c6",
           "oe": "\u0153", "OE": "\u0152", "l": "\u0142", "L": "\u0141", "i": "\u0131", "j": "\u0237"}
GREEK = {name: chr(code) for name, code in (
    ("alpha", 0x3b1), ("beta", 0x3b2), ("gamma", 0x3b3), ("delta", 0x3b4), ("epsilon", 0x3b5), ("mu", 0x3bc),
    ("nu", 0x3bd), ("pi", 0x3c0), ("sigma", 0x3c3), ("tau", 0x3c4), ("phi", 0x3c6), ("omega", 0x3c9),
    ("Gamma", 0x393), ("Delta", 0x394), ("Omega", 0x3a9))}
SPECIALS = set("&%$#_{}")


class BibError(ValueError):
    pass


@dataclass(frozen=True)
class Entry:
    kind: str
    key: str
    fields: dict = field(default_factory=dict)   # field name -> text (TeX decoded; identifiers kept as written)
    authors: tuple = ()                          # display names, "First Last"


@dataclass(frozen=True)
class Bib:
    sha: str
    entries: dict  # key -> Entry

    def __contains__(self, key):
        return key in self.entries

    def __getitem__(self, key):
        return self.entries[key]


# ---------------------------------------------------------------- TeX text
def _group(text, i):
    """text[i] is "{": return (content, index after the matching "}")."""
    depth, start = 0, i
    while i < len(text):
        ch = text[i]
        if ch == "\\":
            i += 2
            continue
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return text[start + 1:i], i + 1
        i += 1
    raise BibError(f"unbalanced braces in {text[:60]!r}")


def _accent(mark, base):
    if not base:
        raise BibError(f"accent \\{mark} with nothing to put it on")
    base = {"\u0131": "i", "\u0237": "j"}.get(base[0], base[0]) + base[1:]
    return unicodedata.normalize("NFC", base[0] + ACCENTS[mark]) + base[1:]


def decode(text, math=False):
    """TeX-ish field text to plain Unicode. Unknown macros and unsupported constructs raise BibError."""
    out, i = [], 0
    while i < len(text):
        ch = text[i]
        if ch == "{":
            inner, i = _group(text, i)
            out.append(decode(inner, math))
            continue
        if ch == "}":
            raise BibError(f"unbalanced braces in {text[:60]!r}")
        if ch == "$":
            if math:
                raise BibError(f"nested math in {text[:60]!r}")
            end = text.find("$", i + 1)
            if end < 0:
                raise BibError(f"unclosed math in {text[:60]!r}")
            out.append(decode(text[i + 1:end], math=True))
            i = end + 1
            continue
        if math and ch in "^_":
            raise BibError(f"unsupported math {text[:60]!r}: superscripts and subscripts are not rendered")
        if ch == "\\":
            m = re.match(r"[A-Za-z]+", text[i + 1:])
            name = m.group(0) if m else text[i + 1:i + 2]
            if not name:
                raise BibError(f"dangling backslash in {text[:60]!r}")
            i += 1 + len(name)
            if name in SPECIALS:
                out.append(name)
                continue
            if name == " ":
                out.append(" ")
                continue
            if name in ACCENTS and not math:
                while m and i < len(text) and text[i] == " ":
                    i += 1
                if i < len(text) and text[i] == "{":
                    inner, i = _group(text, i)
                    out.append(_accent(name, decode(inner)))
                elif i < len(text) and text[i] == "\\":
                    m2 = re.match(r"\\([A-Za-z]+)", text[i:])
                    if not m2 or m2.group(1) not in LETTERS:
                        raise BibError(f"unknown TeX macro in {text[:60]!r}")
                    out.append(_accent(name, LETTERS[m2.group(1)]))
                    i += len(m2.group(0))
                else:
                    out.append(_accent(name, text[i:i + 1]))
                    i += 1
                continue
            if name in LETTERS and not math:
                out.append(LETTERS[name])
            elif name in GREEK and math:
                out.append(GREEK[name])
            else:
                raise BibError(f"unknown TeX macro \\{name} in {text[:60]!r}")
            if m and i < len(text) and text[i] == " ":
                i += 1  # the space that ends a control word is not text
            continue
        if not math and text.startswith("---", i):
            out.append("\u2014")
            i += 3
        elif not math and text.startswith("--", i):
            out.append("\u2013")
            i += 2
        elif not math and text.startswith("``", i):
            out.append("\u201c")
            i += 2
        elif not math and text.startswith("''", i):
            out.append("\u201d")
            i += 2
        elif ch == "~":
            out.append("\u00a0")
            i += 1
        else:
            out.append(ch)
            i += 1
    return re.sub(r"\s+", " ", "".join(out)).strip() if not math else "".join(out)


def _raw(text):
    return re.sub(r"\\([_%&#])", r"\1", text.replace("{", "").replace("}", "")).strip()


def _split_authors(text):
    """Split at top-level " and ", so a braced corporate name keeps its own "and"."""
    parts, depth, start, i = [], 0, 0, 0
    while i < len(text):
        ch = text[i]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
        elif depth == 0 and ch.isspace():
            m = re.match(r"\s+and\s+", text[i:])
            if m:
                parts.append(text[start:i])
                i += len(m.group(0))
                start = i
                continue
        i += 1
    parts.append(text[start:])
    return [p.strip() for p in parts if p.strip()]


def _display_name(raw):
    """"Last, First" or "Last, Jr, First" to "First Last"; anything else as written."""
    pieces, depth, cur = [], 0, ""
    for ch in raw:
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
        if ch == "," and depth == 0:
            pieces.append(cur)
            cur = ""
        else:
            cur += ch
    pieces.append(cur)
    pieces = [decode(p) for p in pieces]
    if len(pieces) == 2:
        return f"{pieces[1]} {pieces[0]}".strip()
    if len(pieces) == 3:
        return f"{pieces[2]} {pieces[0]} {pieces[1]}".strip()
    return pieces[0]


# ---------------------------------------------------------------- entries
def _value(text, i, where):
    if text[i] == "{":
        return _group(text, i)
    if text[i] == '"':
        depth, j = 0, i + 1
        while j < len(text):
            if text[j] == "\\":
                j += 2
                continue
            if text[j] == "{":
                depth += 1
            elif text[j] == "}":
                depth -= 1
            elif text[j] == '"' and depth == 0:
                return text[i + 1:j], j + 1
            j += 1
        raise BibError(f"{where}: unclosed quoted value")
    m = re.match(r"\d+", text[i:])
    if m:
        return m.group(0), i + len(m.group(0))
    raise BibError(f"{where}: a value must be {{braced}}, \"quoted\" or a number (macros and # are not supported)")


def _skip(text, i):
    while i < len(text) and text[i].isspace():
        i += 1
    return i


def parse(text):
    """Parse a site copy of sources.bib: the SHA header line, then entries."""
    first = text.split("\n", 1)[0]
    m = HEADER.match(first)
    if not m:
        raise BibError("the first line must be '% Copied from Grant-L/electron-plumber-notes sources.bib at commit <40-char SHA>. "
                       "Do not edit here.'")
    sha, entries, i = m.group(1), {}, 0
    seen = {}
    while True:
        i = _skip(text, i)
        if i >= len(text):
            break
        if text[i] == "%":
            nl = text.find("\n", i)
            i = len(text) if nl < 0 else nl + 1
            continue
        if text[i] != "@":
            raise BibError(f"stray text outside an entry: {text[i:i + 40]!r}")
        special = re.match(r"@([A-Za-z]+)", text[i:])
        if special and special.group(1).lower() in UNSUPPORTED_TYPES:
            raise BibError(f"@{special.group(1).lower()} is not supported")
        m = re.match(r"@([A-Za-z]+)\s*\{\s*([^,\s{}]+)\s*,", text[i:])
        if not m:
            raise BibError(f"malformed entry start: {text[i:i + 40]!r}")
        kind, key = m.group(1).lower(), m.group(2)
        where = f"entry {key}"
        if key.lower() in seen:
            raise BibError(f"duplicate key {key!r}")
        i += len(m.group(0))
        raw = {}
        while True:
            i = _skip(text, i)
            if i >= len(text):
                raise BibError(f"{where}: unbalanced braces (no closing '}}')")
            if text[i] == "}":
                i += 1
                break
            fm = re.match(r"([A-Za-z][A-Za-z0-9_-]*)\s*=\s*", text[i:])
            if not fm:
                raise BibError(f"{where}: malformed field near {text[i:i + 40]!r}")
            name = fm.group(1).lower()
            if name in raw:
                raise BibError(f"{where}: duplicate field {name!r}")
            i += len(fm.group(0))
            if i >= len(text):
                raise BibError(f"{where}: field {name!r} has no value")
            raw[name], i = _value(text, i, where)
            i = _skip(text, i)
            if i < len(text) and text[i] == ",":
                i += 1
            elif i < len(text) and text[i] != "}":
                raise BibError(f"{where}: expected ',' or '}}' after field {name!r}")
        try:
            fields = {k: (_raw(v) if k in RAW_FIELDS else decode(v)) for k, v in raw.items()}
            authors = tuple(_display_name(a) for a in _split_authors(raw.get("author", "")))
        except BibError as exc:
            raise BibError(f"{where}: {exc}") from None
        for required in ("title", "year"):
            if not fields.get(required):
                raise BibError(f"{where}: no {required}")
        seen[key.lower()] = key
        entries[key] = Entry(kind, key, fields, authors)
    return Bib(sha, entries)


def load(path: Path):
    if not path.is_file():
        raise BibError(f"{path.name} does not exist")
    return parse(path.read_text(encoding="utf-8"))
