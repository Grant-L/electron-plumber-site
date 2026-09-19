#!/usr/bin/env python3
"""Gate for the built site. Prints every problem it finds and exits 1 if there are any.

    python3 check.py [_site] [--drafts]

Every HTML page: balanced tags, a title, a description, exactly one h1, internal links, assets and
anchors that resolve, no leftover [PLACEHOLDER] text, and the framework's name spelled out.
Every built file and every tracked source file: none of the owner's private forbidden terms.
Every image: no embedded metadata.
"""
import os
import re
import subprocess
import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlparse

ROOT = Path(__file__).resolve().parent
VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr"}

# The framework's name is spelled out. The three letters are fine only inside the repo's name.
ACRONYM = re.compile(r"\bAVE\b(?!-Core)")
PLACEHOLDER = re.compile(r"\[[A-Z][A-Z0-9_ ,.'-]{2,}(?::[^\]\n]*)?\]")
STYLE_URL = re.compile(r"url\(\s*['\"]?([^'\")]+)['\"]?\s*\)")
TEXT_ATTRS = ("alt", "aria-label", "title", "content")


def forbidden_terms():
    """Terms that must never ship. The list itself is private: it comes from the FORBIDDEN_TERMS
    environment variable (a repository secret in CI) or from _private/forbidden.txt. One term or phrase per line;
    lines starting with # are comments. Matching is a case-insensitive substring search."""
    raw = os.environ.get("FORBIDDEN_TERMS", "")
    local = ROOT / "_private" / "forbidden.txt"
    if not raw and local.is_file():
        raw = local.read_text(encoding="utf-8")
    return sorted({line.strip().lower() for line in raw.splitlines() if line.strip() and not line.strip().startswith("#")})


class Page(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack, self.errors, self.links, self.ids = [], [], [], set()
        self.title, self.description, self.h1, self.text, self.attr_text = "", "", 0, [], []
        self._in_title = self._skip = False

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if a.get("id"):
            self.ids.add(a["id"])
        for key in ("href", "src"):
            if a.get(key):
                self.links.append(a[key])
        self.links.extend(STYLE_URL.findall(a.get("style") or ""))
        self.attr_text.extend(a[k] for k in TEXT_ATTRS if a.get(k))
        if tag == "meta" and a.get("name") == "description":
            self.description = a.get("content", "")
        if tag == "h1":
            self.h1 += 1
        self._in_title = tag == "title"
        self._skip = tag in ("script", "style")
        if tag not in VOID:
            self.stack.append(tag)

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in VOID and self.stack and self.stack[-1] == tag:
            self.stack.pop()

    def handle_endtag(self, tag):
        self._in_title = self._skip = False
        if tag in VOID:
            return
        if self.stack and self.stack[-1] == tag:
            self.stack.pop()
        else:
            self.errors.append(f"unexpected </{tag}> (open: {'>'.join(self.stack[-3:])})")

    def handle_data(self, data):
        if self._in_title:
            self.title += data
        elif not self._skip:
            self.text.append(data)


METADATA_MARKERS = {
    ".jpg": (b"Exif\x00\x00", b"http://ns.adobe.com/xap/1.0/"),
    ".jpeg": (b"Exif\x00\x00", b"http://ns.adobe.com/xap/1.0/"),
    ".png": (b"eXIf", b"XML:com.adobe.xmp"),
    ".webp": (b"EXIF", b"XMP "),
}


def _has_metadata(suffix: str, data: bytes) -> bool:
    """EXIF/XMP in an image: location, device and timestamps do not belong on the site."""
    return any(marker in data for marker in METADATA_MARKERS.get(suffix.lower(), ()))


def check(site: Path, drafts: bool = False):
    site = site.resolve()
    problems, parsed = [], {}
    terms = forbidden_terms()
    if not terms:
        print("WARN no private forbidden-term list found (FORBIDDEN_TERMS or _private/forbidden.txt): that rule is skipped",
              file=sys.stderr)

    for path in sorted(p for p in site.rglob("*") if p.is_file()):
        rel = path.relative_to(site).as_posix()
        data = path.read_bytes()
        if any(t.encode() in data.lower() for t in terms):
            problems.append(f"{rel}: a term that must never appear on a channel surface is in this file")
        if _has_metadata(path.suffix, data):
            problems.append(f"{rel}: image carries embedded metadata (strip it: magick in.jpg -strip out.jpg)")
        if path.suffix == ".html":
            page = Page()
            page.feed(data.decode("utf-8"))
            parsed[path] = page

    for path, page in parsed.items():
        rel = path.relative_to(site).as_posix()
        say = lambda msg, rel=rel: problems.append(f"{rel}: {msg}")  # noqa: E731
        is_redirect = 'http-equiv="refresh"' in path.read_text(encoding="utf-8")
        if page.stack:
            say(f"unclosed tags: {page.stack}")
        for error in page.errors:
            say(error)
        if not page.title.strip():
            say("no <title>")
        if is_redirect:
            continue
        if not page.description.strip():
            say("no meta description")
        if page.h1 != 1:
            say(f"expected exactly one <h1>, found {page.h1}")

        text = " ".join(page.text)
        if not drafts and PLACEHOLDER.search(text):
            say(f"leftover placeholder {PLACEHOLDER.search(text).group(0)!r}")
        if ACRONYM.search(" ".join([text, page.title, *page.attr_text])):
            say("the framework's name must be spelled out (three-letter acronym found)")

        for link in page.links:
            url = urlparse(link)
            if url.scheme or link.startswith("//"):
                continue
            if url.path == "":
                target = path
            elif url.path.startswith("/"):
                target = site / unquote(url.path).lstrip("/")
            else:
                target = (path.parent / unquote(url.path)).resolve()
            if target.is_dir():
                target = target / "index.html"
            if not target.exists():
                say(f"broken link {link!r}")
            elif url.fragment and target.suffix == ".html":
                other = parsed.get(target.resolve())
                if other and url.fragment not in other.ids:
                    say(f"missing anchor {link!r}")
    return problems


def check_sources(root: Path = ROOT):
    """The repository is as public as the site: scan every tracked file for the private terms too."""
    terms = forbidden_terms()
    if not terms:
        return []
    try:
        tracked = subprocess.run(["git", "-C", str(root), "ls-files", "-z"], capture_output=True, check=True).stdout.split(b"\0")
    except (OSError, subprocess.CalledProcessError):
        return []
    problems = []
    for name in filter(None, tracked):
        path = root / name.decode()
        if path.is_file() and any(t.encode() in path.read_bytes().lower() for t in terms):
            problems.append(f"{name.decode()}: a term that must never appear in this public repository")
    return problems


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    target = Path(args[0] if args else "_site").resolve()
    if not target.is_dir():
        sys.exit(f"{target} does not exist: run build.py first")
    found = check(target, drafts="--drafts" in sys.argv) + check_sources()
    for line in found:
        print("FAIL", line)
    print(f"checked {len(list(target.rglob('*.html')))} pages: {'%d problems' % len(found) if found else 'ok'}")
    sys.exit(1 if found else 0)
