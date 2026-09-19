"""A small Markdown subset, enough for episode handouts. No dependencies.

Supported: ATX headings, paragraphs, unordered and ordered lists (with indented
continuation lines), fenced code, blockquotes, HTML comments (dropped), and
inline code, links, autolinks, bold and italic. Anything else is a build error
rather than a silent mis-render: tables and nested lists are not supported.
"""
import html
import re

_COMMENT = re.compile(r"<!--.*?-->", re.S)
_ITEM = re.compile(r"^(\s*)([-*]|\d+\.)\s+(.*)$")
_HEADING = re.compile(r"^(#{1,4})\s+(.*?)\s*#*$")
_SLOT = "\x00{}\x00"


class MarkdownError(ValueError):
    pass


def _smart_quotes(text):
    """Typographic quotes for prose. Code spans and autolinks are already out of the way."""
    text = re.sub(r'(^|[\s(\[{\u2014-])([*_]{0,3})"', "\\1\\2\u201c", text)
    text = text.replace('"', "\u201d")
    text = re.sub(r"(^|[\s(\[{\u2014-])([*_]{0,3})'", "\\1\\2\u2018", text)
    return text.replace("'", "\u2019")


def inline(text, link_base=""):
    """Inline Markdown to HTML. Raw HTML in the source is escaped, never passed through."""
    slots = []

    def keep(markup):
        slots.append(markup)
        return _SLOT.format(len(slots) - 1)

    def resolve(url):
        if link_base and not re.match(r"^(?:[a-z][a-z0-9+.-]*:|/|#)", url, re.I):
            while url.startswith("./"):
                url = url[2:]
            return link_base.rstrip("/") + "/" + url
        return url

    text = re.sub(r"`([^`]+)`", lambda m: keep(f"<code>{html.escape(m.group(1), quote=False)}</code>"), text)
    text = re.sub(r"<(https?://[^>\s]+)>",
                  lambda m: keep(f'<a href="{html.escape(m.group(1))}">{html.escape(m.group(1), quote=False)}</a>'), text)
    # Link targets go into slots before any text pass, so quotes, emphasis and ")" inside a URL survive.
    text = re.sub(r"(?<=\])\(((?:[^()\s]|\([^()\s]*\))+)\)", lambda m: "(" + keep(html.escape(resolve(m.group(1)))) + ")", text)
    text = html.escape(text, quote=False)
    text = _smart_quotes(text)
    text = re.sub(r"\[([^\]]+)\]\(\x00(\d+)\x00\)", '<a href="\x00\\2\x00">\\1</a>', text)
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"(?<![*\w])\*(?!\s)(.+?)(?<!\s)\*(?![*\w])", r"<em>\1</em>", text)
    text = re.sub(r"(?<![\w])_(?!\s)(.+?)(?<!\s)_(?![\w])", r"<em>\1</em>", text)
    return re.sub(r"\x00(\d+)\x00", lambda m: slots[int(m.group(1))], text)


def render(source, link_base="", heading_shift=0):
    """Block-level Markdown to HTML."""
    lines = _COMMENT.sub("", source).replace("\t", "    ").splitlines()
    out, para, i = [], [], 0

    def flush():
        if para:
            out.append("<p>" + inline(" ".join(para), link_base) + "</p>")
            para.clear()

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        if not stripped:
            flush()
            i += 1
            continue
        if stripped.startswith("```"):
            flush()
            code = []
            i += 1
            while i < len(lines) and not lines[i].strip().startswith("```"):
                code.append(lines[i])
                i += 1
            if i == len(lines):
                raise MarkdownError("unclosed code fence")
            out.append("<pre><code>" + html.escape("\n".join(code), quote=False) + "</code></pre>")
            i += 1
            continue
        m = _HEADING.match(stripped)
        if m:
            flush()
            level = min(6, len(m.group(1)) + heading_shift)
            out.append(f"<h{level}>{inline(m.group(2), link_base)}</h{level}>")
            i += 1
            continue
        if stripped.startswith(">"):
            flush()
            quote = []
            while i < len(lines) and lines[i].strip().startswith(">"):
                quote.append(lines[i].strip()[1:].strip())
                i += 1
            out.append("<blockquote><p>" + inline(" ".join(quote), link_base) + "</p></blockquote>")
            continue
        if stripped.startswith("|") or re.fullmatch(r"[\s:|-]*-\|-[\s:|-]*", stripped):
            raise MarkdownError(f"tables are not supported: {stripped[:40]!r}")
        if (re.fullmatch(r"-{3,}|\*{3,}|_{3,}|=+", stripped) or stripped.startswith(("~~~", "#####", "!["))
                or re.match(r"(?:\+|\d+\))\s", stripped)):
            raise MarkdownError(f"unsupported Markdown: {stripped[:40]!r}")
        m = _ITEM.match(line)
        if m and para:
            flush()  # as on GitHub, a list may interrupt a paragraph
        if m:
            ordered = m.group(2)[0].isdigit()
            first = int(m.group(2)[:-1]) if ordered else 1
            indent = len(m.group(1))
            items = []
            def same_list(text, indent=indent, ordered=ordered):
                found = _ITEM.match(text)
                return bool(found) and len(found.group(1)) == indent and found.group(2)[0].isdigit() == ordered

            while i < len(lines):
                m = _ITEM.match(lines[i])
                if same_list(lines[i]):
                    items.append([m.group(3).strip()])
                elif m and len(m.group(1)) > indent:
                    raise MarkdownError(f"nested lists are not supported: {lines[i].strip()[:40]!r}")
                elif m:
                    break  # a different list starts here
                elif lines[i].strip() and lines[i].startswith(" ") and items:
                    items[-1].append(lines[i].strip())
                elif not lines[i].strip() and i + 1 < len(lines) and same_list(lines[i + 1]):
                    pass  # a blank line between two items of the same list
                else:
                    break
                i += 1
            tag = "ol" if ordered else "ul"
            start = f' start="{first}"' if ordered and first != 1 else ""
            out.append(f"<{tag}{start}>" + "".join(f"<li>{inline(' '.join(it), link_base)}</li>" for it in items) + f"</{tag}>")
            continue
        para.append(stripped)
        i += 1
    flush()
    return "\n".join(out)


def sections(source):
    """Split a handout at its `## ` headings: [(title, body_markdown), ...]. Text above the first one is dropped."""
    found, title, body = [], None, []
    in_fence = False
    for line in _COMMENT.sub("", source).splitlines():
        if line.strip().startswith("```"):
            in_fence = not in_fence
        if not in_fence and line.startswith("## "):
            if title is not None:
                found.append((title, "\n".join(body).strip()))
            title, body = line[3:].strip(), []
        elif title is not None:
            body.append(line)
    if title is not None:
        found.append((title, "\n".join(body).strip()))
    return found
