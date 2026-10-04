"""Load and validate the site's content: content/site.toml, content/episodes.toml, content/episodes/*.md,
the History timeline, content/timeline.toml, against its sources in content/sources.bib, and the corrections in
content/errata.md, and the Research page's counts in content/research.toml.
link_episodes() then gives each live episode the events, claims and corrections that name it."""
import datetime
import re
import struct
import tomllib
import urllib.parse
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path

from check import ACRONYM, PLACEHOLDER, forbidden_terms

from . import bib, md

ARCS = {"historical": "Historical", "speculative": "Speculative", "practical": "Practical"}
STATUSES = {"in-production", "published"}

# The History filters. Each changes only by a spec change; the order is the chip order.
# An era's bounds are inclusive years of an event's sort key; None is an open end.
ERAS = {
    "ether": ("Fields and ether", 1840, 1904),
    "relativity": ("Relativity", 1905, 1924),
    "quantum-electron": ("Quantum electron", 1925, 1949),
    "precision": ("Precision", 1950, None),
}
CLASSES = {"experiment": "Experiment", "measurement": "Measurement", "theory": "Theory", "instrument": "Instrument"}
THREADS = {
    "ether": "The ether",
    "vortex-atoms": "Vortex atoms",
    "electromagnetism": "Electromagnetism",
    "vectors-quaternions": "Vectors and quaternions",
    "relativity": "Relativity",
    "quantum": "Quantum theory",
    "spin-and-moment": "Spin and magnetic moment",
    "g-factor": "The g-factor",
    "electron-mass": "Electron mass",
    "charge": "Charge",
    "topology-knots": "Topology and knots",
    "cosmology": "Cosmology",
}
DATE_BASES = ("event", "read", "received", "published")
VERIFIED = {"primary": "Checked against the original", "secondary-only": "Secondary sources only"}
SOURCE_KINDS = ("primary", "secondary")
EVENT_ID = re.compile(r"\d{4}-[a-z0-9]+(?:-[a-z0-9]+)*")
PARTIAL_DATE = re.compile(r"(\d{4})(?:-(\d{2})(?:-(\d{2}))?)?")
# A public-safe display name: no digits, so bot ids and numbered handles cannot pass.
CHECKED_BY = re.compile(r"[A-Z][A-Za-z .'-]{1,39}")
CLAIM = re.compile(r"ep(\d{3})-c\d{2,}")
IMAGE_DIR = "static/img/history"
IMAGE_FILE = re.compile(r"static/img/history/[a-z0-9-]+\.(webp|jpg|svg)")
IMAGE_LICENSES = ("public-domain", "cc0", "cc-by-4.0", "own-work")
IMAGE_SOURCE = re.compile(r"https://commons\.wikimedia\.org/wiki/File:\S+")
IMAGE_MAX_BYTES = 40_960
HISTORY_IMAGES_MAX_BYTES = 200 * 1024
ALT_OPENERS = ("image of", "picture of", "photo of")
DOI = re.compile(r"10\.\d{4,9}/\S+")
MD_LINK = re.compile(r"\]\(|<https?://")
# Reading links on a timeline entry (a source's url and fulltext_url, and [[event.further]]): only these hosts.
FURTHER_HOSTS = frozenset({
    "www.maths.tcd.ie", "archive.org", "mathshistory.st-andrews.ac.uk", "ajsonline.org", "www.aps.org",
    "history.aip.org", "www.nobelprize.org", "journals.aps.org", "arxiv.org", "physics.aps.org", "royalsocietypublishing.org",
})
LINK_QUERY_KEYS = ("id", "page")
TRACKING_QUERY = re.compile(r"utm_.*|fbclid|gclid|ref", re.I)
# (host, path prefix), lowercase: the owner's own repositories, which may hold unpublished material.
PRIVATE_LINKS = (("github.com", "/grant-l/"), ("raw.githubusercontent.com", "/grant-l/"), ("gist.github.com", "/grant-l/"),
                 ("codeload.github.com", "/grant-l/"))
MAX_FURTHER = 2
FURTHER_TITLE_MAX, FURTHER_PUBLISHER_MAX = 100, 60
# Timeline titles and summaries render as plain text, so a character that reads as Markdown emphasis or code is refused.
MARKUP = re.compile(r"[*_`]")


class ContentError(SystemExit):
    pass


@dataclass
class Episode:
    number: int
    slug: str
    title: str
    status: str
    arc: str = ""
    excerpt: str = ""
    orientation: str = ""
    youtube_id: str = ""
    date: str = ""
    runtime: str = ""
    announce: bool = True
    sources: list = field(default_factory=list)  # TOML [[episode.source]]
    draft: bool = False
    sections: list = field(default_factory=list)  # [(title, html)]
    # Filled by link_episodes, for live episodes only: what the public records say about this episode.
    events: list = field(default_factory=list, init=False)
    claims: list = field(default_factory=list, init=False)
    corrections: list = field(default_factory=list, init=False)

    @property
    def serial(self):
        return f"Episode {self.number:03d}"

    @property
    def live(self):
        return self.status == "published" or self.draft

    @property
    def url(self):
        return f"episodes/{self.slug}/"


def load(root: Path, drafts: bool = False):
    site = tomllib.loads((root / "content" / "site.toml").read_text(encoding="utf-8"))
    raw = tomllib.loads((root / "content" / "episodes.toml").read_text(encoding="utf-8")).get("episode", [])
    episodes, seen, slugs = [], set(), set()
    for item in raw:
        for internal in ("draft", "sections", "sources", "events", "claims", "corrections"):
            if internal in item:
                raise ContentError(f"episodes.toml: {internal!r} is not a content field")
        item = dict(item)
        if "source" in item:
            item["sources"] = item.pop("source")
        if isinstance(item.get("date"), datetime.date):
            item["date"] = item["date"].isoformat()
        try:
            ep = Episode(**item)
        except TypeError as exc:
            raise ContentError(f"episodes.toml: {exc}") from None
        where = f"episodes.toml, episode {ep.number}"
        if not isinstance(ep.number, int) or isinstance(ep.number, bool):
            raise ContentError(f"{where}: number must be an integer")
        for key in ("slug", "title", "arc", "status", "excerpt", "orientation", "youtube_id", "date", "runtime"):
            if not isinstance(getattr(ep, key), str):
                raise ContentError(f"{where}: {key} must be a string")
        if not isinstance(ep.announce, bool):
            raise ContentError(f"{where}: announce must be true or false")
        if not isinstance(ep.sources, list):
            raise ContentError(f"{where}: source must be a list of [[episode.source]] tables")
        if ep.sources and ep.status != "published":
            raise ContentError(f"{where}: sources go with a published episode")
        if ep.arc and ep.arc not in ARCS:
            raise ContentError(f"{where}: unknown arc {ep.arc!r} (one of {', '.join(ARCS)})")
        if ep.status == "published" and not ep.arc:
            raise ContentError(f"{where}: a published episode needs an arc (one of {', '.join(ARCS)})")
        if ep.status not in STATUSES:
            raise ContentError(f"{where}: unknown status {ep.status!r} (one of {', '.join(sorted(STATUSES))})")
        if not re.fullmatch(r"\d{3}-[a-z0-9-]+", ep.slug):
            raise ContentError(f"{where}: slug must look like 001-short-title, got {ep.slug!r}")
        if not ep.slug.startswith(f"{ep.number:03d}-"):
            raise ContentError(f"{where}: slug must start with {ep.number:03d}-")
        if ep.number in seen or ep.slug in slugs:
            raise ContentError(f"{where}: duplicate episode number or slug")
        seen.add(ep.number)
        slugs.add(ep.slug)

        handout = root / "content" / "episodes" / f"{ep.slug}.md"
        if ep.status == "published":
            # Same rule as the notes pipeline: a published episode with no handout is refused.
            missing = [k for k in ("youtube_id", "date", "excerpt") if not getattr(ep, k)]
            if missing:
                raise ContentError(f"{where}: published, but missing {', '.join(missing)}")
            try:
                datetime.date.fromisoformat(ep.date)
            except ValueError:
                raise ContentError(f"{where}: date must be a real date, YYYY-MM-DD") from None
            if not re.fullmatch(r"[A-Za-z0-9_-]{6,20}", ep.youtube_id):
                raise ContentError(f"{where}: youtube_id does not look like a video id")
            if not handout.is_file():
                raise ContentError(f"{where}: published, but content/episodes/{ep.slug}.md does not exist")
        elif handout.is_file():
            raise ContentError(f"{where}: content/episodes/{ep.slug}.md exists but the episode is not published. "
                               "Unpublished handouts do not belong in this public repo.")
        elif drafts and (root / "_private" / "drafts" / f"{ep.slug}.md").is_file():
            handout = root / "_private" / "drafts" / f"{ep.slug}.md"
            ep.draft = True

        if ep.live:
            base = site["notes_repo"].rstrip("/") + "/blob/main/" + site.get("notes_path", "").strip("/")
            try:
                ep.sections = [(t, md.render(body, link_base=base))
                               for t, body in md.sections(handout.read_text(encoding="utf-8"))]
            except md.MarkdownError as exc:
                raise ContentError(f"{handout.name}: {exc}") from None
            if not ep.sections:
                raise ContentError(f"{handout.name}: no '## ' sections found")
        episodes.append(ep)

    handouts = root / "content" / "episodes"
    if handouts.is_dir():
        for path in sorted(handouts.glob("*.md")):
            if path.stem not in slugs:
                raise ContentError(f"content/episodes/{path.name}: no episode in episodes.toml has this slug")

    episodes.sort(key=lambda e: e.number)
    return site, episodes


# ---------------------------------------------------------------- the Start here page
START_TARGETS = {"episodes/", "history/", "research/", "corrections/", "about/"}
MAX_START_STEPS = 5
START_EPISODE = re.compile(r"episode:(\d+)")


@dataclass
class Step:
    target: str
    kind: str  # "episode" or "route"
    episode: object = None
    route: str = ""
    anchor: str = ""


def load_start(root: Path, episodes):
    """content/start.toml as a list of Step. Each step names a target and nothing else: its words come from
    the target page or the episode's data, so this file cannot add a claim."""
    path = root / "content" / "start.toml"
    if not path.is_file():
        raise ContentError("content/start.toml does not exist")
    raw = tomllib.loads(path.read_text(encoding="utf-8"))
    if set(raw) - {"step"}:
        raise ContentError(f"start.toml: unknown key {sorted(set(raw) - {'step'})[0]!r} (only [[step]] tables)")
    items = raw.get("step", [])
    if not isinstance(items, list) or not all(isinstance(i, dict) for i in items):
        raise ContentError("start.toml: steps must be [[step]] tables")
    if not items:
        raise ContentError("start.toml: no [[step]] entries")
    if len(items) > MAX_START_STEPS:
        raise ContentError(f"start.toml: {len(items)} steps, at most {MAX_START_STEPS}")
    by_number = {e.number: e for e in episodes}
    steps, seen = [], set()
    for n, item in enumerate(items, 1):
        where = f"start.toml, step {n}"
        if set(item) - {"target"}:
            raise ContentError(f"{where}: unknown key {sorted(set(item) - {'target'})[0]!r} (the only field is target)")
        target = item.get("target")
        if not isinstance(target, str):
            raise ContentError(f"{where}: target must be a string")
        if target in seen:
            raise ContentError(f"{where}: duplicate target {target!r}")
        seen.add(target)
        m = START_EPISODE.fullmatch(target)
        if m:
            ep = by_number.get(int(m.group(1)))
            if ep is None:
                raise ContentError(f"{where}: no episode {m.group(1)} in episodes.toml")
            if not ep.live and not ep.announce:
                raise ContentError(f"{where}: episode {ep.number} is not announced")
            steps.append(Step(target, "episode", episode=ep))
            continue
        route, hash_, anchor = target.partition("#")
        if route not in START_TARGETS or (hash_ and not anchor):
            raise ContentError(f"{where}: target {target!r} must be episode:N or one of "
                               f"{', '.join(sorted(START_TARGETS))}, with an optional #anchor")
        steps.append(Step(target, "route", route=route, anchor=anchor))
    return steps


# ---------------------------------------------------------------- the History timeline
@dataclass
class Source:
    key: str
    kind: str
    locator: str = ""
    doi: str = ""
    url: str = ""
    note: str = ""
    fulltext_url: str = ""
    entry: object = field(default=None, init=False, repr=False)  # the bib.Entry, set by load_timeline


@dataclass
class Further:
    title: str
    publisher: str
    url: str


@dataclass
class Event:
    id: str
    title: str
    summary: str
    era: str
    cls: str  # TOML key "class"
    thread: list
    verified: str
    checked_by: str
    checked_date: str
    date: str = ""
    oneliner: str = ""  # the preview card's line; site.js reads it from data-oneliner
    date_basis: str = "event"
    end: str = ""
    circa: bool = False
    not_before: str = ""
    not_after: str = ""
    people: list = field(default_factory=list)
    claims: list = field(default_factory=list)
    episodes: list = field(default_factory=list)
    related: list = field(default_factory=list)
    sources: list = field(default_factory=list)  # TOML [[event.source]]
    further: list = field(default_factory=list)  # TOML [[event.further]], Further once loaded
    image: object = None  # TOML [event.image], an Image once loaded

    @property
    def precision(self):
        return {1: "year", 2: "month", 3: "day"}[len(self.date.split("-"))] if self.date else ""

    @property
    def sort_key(self):
        return date_key(self.date or self.not_before or self.not_after)


@dataclass
class Image:
    file: str
    alt: str
    author: str
    title: str
    license: str
    width: int
    height: int
    source_url: str = ""
    caption: str = ""


def image_size(path: Path):
    """(width, height) in pixels of a WebP or JPEG file, or the viewBox size of an SVG; None if unreadable."""
    data = path.read_bytes()
    if path.suffix == ".webp":
        if data[:4] != b"RIFF" or data[8:12] != b"WEBP" or len(data) < 25:
            return None
        chunk = data[12:16]
        if chunk == b"VP8 " and data[23:26] == b"\x9d\x01\x2a" and len(data) >= 30:
            w, h = struct.unpack("<HH", data[26:30])
            return w & 0x3FFF, h & 0x3FFF
        if chunk == b"VP8L" and data[20] == 0x2F:
            bits = int.from_bytes(data[21:25], "little")
            return (bits & 0x3FFF) + 1, ((bits >> 14) & 0x3FFF) + 1
        if chunk == b"VP8X" and len(data) >= 30:
            return int.from_bytes(data[24:27], "little") + 1, int.from_bytes(data[27:30], "little") + 1
        return None
    if path.suffix == ".jpg":
        if data[:2] != b"\xff\xd8":
            return None
        i = 2
        while i + 9 <= len(data):
            if data[i] != 0xFF:
                return None
            marker = data[i + 1]
            if marker in (0xC0, 0xC2):
                h, w = struct.unpack(">HH", data[i + 5:i + 9])
                return w, h
            if marker == 0x01 or 0xD0 <= marker <= 0xD7:
                i += 2
                continue
            i += 2 + struct.unpack(">H", data[i + 2:i + 4])[0]
        return None
    if path.suffix == ".svg":
        try:
            box = ET.fromstring(data).get("viewBox", "").replace(",", " ").split()
            w, h = float(box[2]), float(box[3])
        except (ET.ParseError, IndexError, ValueError):
            return None
        return (int(w), int(h)) if w.is_integer() and h.is_integer() else None
    return None


def _image_text(value, where, name, terms):
    if ACRONYM.search(value):
        raise ContentError(f"{where}: image {name} must spell out the framework's name (three-letter acronym found)")
    if PLACEHOLDER.search(value):
        raise ContentError(f"{where}: image {name} has a capitalised bracket placeholder (write [sic] in lowercase)")
    if any(t in value.lower() for t in terms):
        raise ContentError(f"{where}: image {name} has a term that must never appear on a channel surface")


def _image(raw, ev, where, root, terms, files):
    """[event.image] as an Image. With files, the file itself is checked too: it exists, its size and pixel size."""
    if not isinstance(raw, dict):
        raise ContentError(f"{where}: image must be an [event.image] table")
    try:
        img = Image(**raw)
    except TypeError as exc:
        raise ContentError(f"{where}, image: {exc}") from None
    for key in ("file", "alt", "author", "title", "license", "source_url", "caption"):
        if not isinstance(getattr(img, key), str):
            raise ContentError(f"{where}: image {key} must be a string")
    for key in ("width", "height"):
        value = getattr(img, key)
        if not isinstance(value, int) or isinstance(value, bool) or value < 1:
            raise ContentError(f"{where}: image {key} must be a positive integer")
    m = IMAGE_FILE.fullmatch(img.file)
    if not m:
        raise ContentError(f"{where}: image file must look like {IMAGE_DIR}/<event-id>.webp (or .jpg, .svg), got {img.file!r}")
    if img.license not in IMAGE_LICENSES:
        raise ContentError(f"{where}: unknown image license {img.license!r} (one of {', '.join(IMAGE_LICENSES)})")
    if m.group(1) == "svg" and img.license != "own-work":
        raise ContentError(f"{where}: an .svg image must be own-work")
    if img.source_url or img.license != "own-work":
        if not IMAGE_SOURCE.fullmatch(img.source_url):
            raise ContentError(f"{where}: image source_url must be an https://commons.wikimedia.org/wiki/File: page")

    alt = img.alt
    if not alt.strip() or len(alt) > 150 or set(alt) & set("\n\r<>"):
        raise ContentError(f"{where}: image alt must be one line of 1 to 150 characters, without < or >")
    if alt.strip().lower() in (img.title.strip().lower(), ev.title.strip().lower()):
        raise ContentError(f"{where}: image alt must describe the picture, not repeat a title")
    if alt.lower().startswith(ALT_OPENERS):
        raise ContentError(f"{where}: image alt must not start with 'Image of', 'Picture of' or 'Photo of'")
    for key in ("author", "title"):
        if not getattr(img, key).strip() or set(getattr(img, key)) & set("\n\r"):
            raise ContentError(f"{where}: image {key} must be one line of text")
    if "caption" in raw and (not img.caption.strip() or len(img.caption) > 140 or set(img.caption) & set("\n\r")):
        raise ContentError(f"{where}: image caption must be one line of at most 140 characters")
    for key in ("alt", "caption", "title", "author"):
        _image_text(getattr(img, key), where, key, terms)

    if files:
        path = root / img.file
        if not path.is_file():
            raise ContentError(f"{where}: image file {img.file} does not exist")
        if path.stat().st_size > IMAGE_MAX_BYTES:
            raise ContentError(f"{where}: image file is {path.stat().st_size} bytes, at most {IMAGE_MAX_BYTES}")
        size = image_size(path)
        if size is None:
            raise ContentError(f"{where}: cannot read the pixel size of {img.file}")
        if size != (img.width, img.height):
            raise ContentError(f"{where}: image width and height say {img.width}x{img.height}, the file is {size[0]}x{size[1]}")
    return img


def _check_history_images(root: Path, events, files):
    """Across the timeline: no shared files and, with files, no unreferenced file in the folder and the page's total
    under its cap."""
    used = {}
    for ev in events:
        if ev.image:
            if ev.image.file in used:
                raise ContentError(f"timeline.toml, event {ev.id}: image file {ev.image.file} is also used by {used[ev.image.file]}")
            used[ev.image.file] = ev.id
    if not files:
        return
    folder = root / IMAGE_DIR
    present = sorted(p for p in folder.iterdir() if p.is_file()) if folder.is_dir() else []
    for path in present:
        if f"{IMAGE_DIR}/{path.name}" not in used:
            raise ContentError(f"{IMAGE_DIR}/{path.name}: no event in timeline.toml uses this file")
    total = sum(p.stat().st_size for p in present)
    if total > HISTORY_IMAGES_MAX_BYTES:
        raise ContentError(f"{IMAGE_DIR}: images total {total} bytes, at most {HISTORY_IMAGES_MAX_BYTES} for the History page")


def date_key(text):
    """(year, month or 0, day or 0) for a YYYY, YYYY-MM or YYYY-MM-DD string."""
    parts = [int(p) for p in text.split("-")]
    return tuple(parts + [0] * (3 - len(parts)))


def _partial_date(value, where, name, today):
    """A YYYY, YYYY-MM or YYYY-MM-DD string naming a real date that is not in the future."""
    if not isinstance(value, str):
        raise ContentError(f"{where}: {name} must be a string")
    m = PARTIAL_DATE.fullmatch(value)
    if not m:
        raise ContentError(f"{where}: {name} must be YYYY, YYYY-MM or YYYY-MM-DD, got {value!r}")
    year, month, day = (int(g) if g else 0 for g in m.groups())
    try:
        datetime.date(year, month or 1, day or 1)
    except ValueError:
        raise ContentError(f"{where}: {name} {value!r} is not a real date") from None
    if (year, month, day)[:len(value.split("-"))] > (today.year, today.month, today.day)[:len(value.split("-"))]:
        raise ContentError(f"{where}: {name} {value!r} is in the future")
    return value


def _iso(value):
    return value.isoformat() if isinstance(value, datetime.date) else value


def _strings(value, where, name):
    if not isinstance(value, list) or not all(isinstance(v, str) and v.strip() for v in value):
        raise ContentError(f"{where}: {name} must be a list of non-empty strings")
    if len(set(value)) != len(value):
        raise ContentError(f"{where}: {name} has a duplicate")
    return value


def load_bib(root: Path):
    try:
        return bib.load(root / "content" / "sources.bib")
    except bib.BibError as exc:
        raise ContentError(f"content/sources.bib: {exc}") from None


def _sources(raw, where, sources_bib):
    """[[event.source]] or [[episode.source]] tables as a list of Source, each checked against sources.bib."""
    sources = []
    for raw_source in raw:
        if not isinstance(raw_source, dict):
            raise ContentError(f"{where}: each source must be a table")
        try:
            src = Source(**raw_source)
        except TypeError as exc:
            raise ContentError(f"{where}, source: {exc}") from None
        for key in ("key", "kind", "locator", "doi", "url", "note", "fulltext_url"):
            if not isinstance(getattr(src, key), str):
                raise ContentError(f"{where}, source {src.key!r}: {key} must be a string")
        if src.key not in sources_bib:
            raise ContentError(f"{where}: source key {src.key!r} is not in content/sources.bib")
        if src.kind not in SOURCE_KINDS:
            raise ContentError(f"{where}, source {src.key!r}: unknown kind {src.kind!r} (one of {', '.join(SOURCE_KINDS)})")
        if any(s.key == src.key for s in sources):
            raise ContentError(f"{where}: source {src.key!r} is listed twice")
        if src.doi:
            if not DOI.fullmatch(src.doi):
                raise ContentError(f"{where}, source {src.key!r}: doi does not look like a DOI (10.NNNN/...)")
            bib_doi = sources_bib[src.key].fields.get("doi", "")
            if bib_doi and bib_doi.lower() != src.doi.lower():
                raise ContentError(f"{where}, source {src.key!r}: doi disagrees with sources.bib")
        for key in ("url", "fulltext_url"):
            if getattr(src, key) and not getattr(src, key).startswith("https://"):
                raise ContentError(f"{where}, source {src.key!r}: {key} must start with https://")
        src.entry = sources_bib[src.key]
        sources.append(src)
    return sources


def _reading_link(url, where, name):
    """A reading link on a timeline entry: https, an allowed host, no tracking, nothing private."""
    if not isinstance(url, str) or not url.startswith("https://"):
        raise ContentError(f"{where}: {name} must start with https://")
    parts = urllib.parse.urlsplit(url)
    host, path = (parts.hostname or "").lower(), parts.path.lower()
    if any(host == h and path.startswith(p) for h, p in PRIVATE_LINKS) or "_private" in f"{host}{path}":
        raise ContentError(f"{where}: {name} points at a private location")
    if host not in FURTHER_HOSTS or parts.port or parts.username or set(url) & set(" \t\n\r<>\"'"):
        raise ContentError(f"{where}: {name} host {host!r} is not in FURTHER_HOSTS")
    for key, _ in urllib.parse.parse_qsl(parts.query, keep_blank_values=True):
        if TRACKING_QUERY.fullmatch(key):
            raise ContentError(f"{where}: {name} carries a tracking parameter {key!r}")
        if key not in LINK_QUERY_KEYS:
            raise ContentError(f"{where}: {name} query parameter {key!r} is not allowed (only {', '.join(LINK_QUERY_KEYS)})")
    return url


def _reading_text(value, where, name, limit, terms):
    if not isinstance(value, str) or not value.strip() or len(value) > limit or set(value) & set("\n\r<>"):
        raise ContentError(f"{where}: further {name} must be one line of 1 to {limit} characters, without < or >")
    if ACRONYM.search(value):
        raise ContentError(f"{where}: further {name} must spell out the framework's name (three-letter acronym found)")
    if PLACEHOLDER.search(value):
        raise ContentError(f"{where}: further {name} has a capitalised bracket placeholder (write [sic] in lowercase)")
    if MARKUP.search(value) or MD_LINK.search(value):
        raise ContentError(f"{where}: further {name} must be plain text (no *, _, ` or links)")
    if any(t in value.lower() for t in terms):
        raise ContentError(f"{where}: further {name} has a term that must never appear on a channel surface")
    return value


def _further(raw, where, terms):
    """[[event.further]] as a list of Further: at most MAX_FURTHER, each a title, a publisher and a reading link."""
    if not isinstance(raw, list) or not all(isinstance(f, dict) for f in raw):
        raise ContentError(f"{where}: further must be [[event.further]] tables")
    if len(raw) > MAX_FURTHER:
        raise ContentError(f"{where}: at most {MAX_FURTHER} [[event.further]] blocks, got {len(raw)}")
    out = []
    for item in raw:
        try:
            further = Further(**item)
        except TypeError as exc:
            raise ContentError(f"{where}, further: {exc}") from None
        _reading_text(further.title, where, "title", FURTHER_TITLE_MAX, terms)
        _reading_text(further.publisher, where, "publisher", FURTHER_PUBLISHER_MAX, terms)
        _reading_link(further.url, where, "further url")
        out.append(further)
    return out


def _check_reading_links(ev, where):
    """Each entry's reading links, DOI targets included, point at different pages."""
    seen = {}
    for src in ev.sources:
        doi = src.doi or src.entry.fields.get("doi", "")
        if doi:
            seen[f"https://doi.org/{doi}".lower()] = f"source {src.key!r} doi"
    links = [(s.url, f"source {s.key!r} url") for s in ev.sources if s.url]
    links += [(s.fulltext_url, f"source {s.key!r} fulltext_url") for s in ev.sources if s.fulltext_url]
    links += [(f.url, "further url") for f in ev.further]
    for url, name in links:
        _reading_link(url, where, name)
        key = url.lower().rstrip("/")
        if key in seen:
            raise ContentError(f"{where}: {name} duplicates the {seen[key]}")
        seen[key] = name


def validate_episode_sources(root: Path, episodes):
    """Check each published episode's [[episode.source]] against sources.bib. A historical episode needs at least one.
    The bib is read only when some episode has sources."""
    for ep in episodes:
        if ep.status == "published" and ep.arc == "historical" and not ep.sources:
            raise ContentError(f"episodes.toml, episode {ep.number}: a published historical episode needs at least one [[episode.source]]")
    if not any(ep.sources for ep in episodes):
        return
    sources_bib = load_bib(root)
    for ep in episodes:
        ep.sources = _sources(ep.sources, f"episodes.toml, episode {ep.number}", sources_bib)


def load_timeline(root: Path, episodes, today=None, files=True):
    """content/timeline.toml as a list of Event, checked against content/sources.bib and the episodes.
    A missing file means no timeline yet: []. files=False skips the checks that read static/img/history/,
    for a caller that has the data but not the site's files."""
    path = root / "content" / "timeline.toml"
    raw = tomllib.loads(path.read_text(encoding="utf-8")).get("event", []) if path.is_file() else []
    if not raw:
        _check_history_images(root, [], files)
        return []
    today = today or datetime.date.today()
    sources_bib = load_bib(root)
    terms = forbidden_terms()
    numbers = {e.number: e for e in episodes}

    events, ids = [], set()
    for n, item in enumerate(raw, 1):
        where = f"timeline.toml, event {item.get('id') or '#' + str(n)}"
        item = dict(item)
        for internal in ("cls", "sources"):
            if internal in item:
                raise ContentError(f"{where}: {internal!r} is not a content field")
        if "class" in item:
            item["cls"] = item.pop("class")
        if "source" in item:
            item["sources"] = item.pop("source")
        for key in ("date", "end", "not_before", "not_after", "checked_date"):
            if key in item:
                item[key] = _iso(item[key])
        try:
            ev = Event(**item)
        except TypeError as exc:
            raise ContentError(f"{where}: {str(exc).replace(repr('cls'), repr('class'))}") from None

        for key in ("id", "title", "summary", "era", "cls", "verified", "checked_by", "date_basis"):
            if not isinstance(getattr(ev, key), str):
                raise ContentError(f"{where}: {'class' if key == 'cls' else key} must be a string")
        if not EVENT_ID.fullmatch(ev.id) or len(ev.id) > 64:
            raise ContentError(f"{where}: id must look like 1843-short-slug (lowercase, at most 64 characters), got {ev.id!r}")
        if ev.id in ids:
            raise ContentError(f"{where}: duplicate id")
        ids.add(ev.id)

        # Dates: either a date (with optional end and circa) or open-ended bounds.
        if not isinstance(ev.circa, bool):
            raise ContentError(f"{where}: circa must be true or false")
        bounds = bool(ev.not_before or ev.not_after)
        if ev.date and bounds:
            raise ContentError(f"{where}: use either date or not_before/not_after, not both")
        if not ev.date and not bounds:
            raise ContentError(f"{where}: needs a date, or not_before/not_after")
        if bounds and (ev.end or ev.circa):
            raise ContentError(f"{where}: end and circa go with date, not with not_before/not_after")
        for key in ("date", "end", "not_before", "not_after"):
            if getattr(ev, key):
                _partial_date(getattr(ev, key), where, key, today)
        if ev.end and date_key(ev.end) <= date_key(ev.date):
            raise ContentError(f"{where}: end must be later than date")
        if ev.circa and ev.precision == "day":
            raise ContentError(f"{where}: circa goes with a YYYY or YYYY-MM date, not a full date")
        if ev.not_before and ev.not_after and date_key(ev.not_before) >= date_key(ev.not_after):
            raise ContentError(f"{where}: not_before must be earlier than not_after")
        if ev.date_basis not in DATE_BASES:
            raise ContentError(f"{where}: unknown date_basis {ev.date_basis!r} (one of {', '.join(DATE_BASES)})")

        # Verification record.
        if ev.verified not in VERIFIED:
            raise ContentError(f"{where}: unknown verified {ev.verified!r} (one of {', '.join(VERIFIED)})")
        if not CHECKED_BY.fullmatch(ev.checked_by):
            raise ContentError(f"{where}: checked_by must be a public display name (letters, spaces, . ' -), got {ev.checked_by!r}")
        if not isinstance(ev.checked_date, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", ev.checked_date):
            raise ContentError(f"{where}: checked_date must be a full date, YYYY-MM-DD")
        _partial_date(ev.checked_date, where, "checked_date", today)

        # Text.
        if not ev.title.strip() or "\n" in ev.title or len(ev.title) > 120:
            raise ContentError(f"{where}: title must be one line of at most 120 characters")
        if not ev.summary.strip() or len(ev.summary) > 600:
            raise ContentError(f"{where}: summary must be 1 to 600 characters")
        if MD_LINK.search(ev.summary):
            raise ContentError(f"{where}: summary must not contain links")
        for key in ("title", "summary"):
            if MARKUP.search(getattr(ev, key)):
                raise ContentError(f"{where}: {key} must be plain text (no *, _ or `)")
        if "oneliner" in item:
            line = ev.oneliner
            if not isinstance(line, str) or not line.strip() or set(line) & set("\n\r<>"):
                raise ContentError(f"{where}: oneliner must be one line of plain text")
            ev.oneliner = line = line.strip()
            if len(line) > 140:
                raise ContentError(f"{where}: oneliner is longer than 140 characters ({len(line)})")
            if not line.endswith((".", "?", "!")):
                raise ContentError(f"{where}: oneliner must end with . ? or !")
            if line == ev.title.strip():
                raise ContentError(f"{where}: oneliner must not repeat the title")
            if ACRONYM.search(line):
                raise ContentError(f"{where}: oneliner must spell out the framework's name (three-letter acronym found)")
            if PLACEHOLDER.search(line):
                raise ContentError(f"{where}: oneliner has a capitalised bracket placeholder (write [sic] in lowercase)")
        _strings(ev.people, where, "people")

        # Vocabularies.
        if ev.era not in ERAS:
            raise ContentError(f"{where}: unknown era {ev.era!r} (one of {', '.join(ERAS)})")
        _, first, last = ERAS[ev.era]
        year = ev.sort_key[0]
        if year < first or (last is not None and year > last):
            raise ContentError(f"{where}: {year} is outside the {ev.era!r} era ({first}\u2013{last or 'present'})")
        if ev.cls not in CLASSES:
            raise ContentError(f"{where}: unknown class {ev.cls!r} (one of {', '.join(CLASSES)})")
        if not isinstance(ev.thread, list) or not 1 <= len(ev.thread) <= 3:
            raise ContentError(f"{where}: thread must be a list of 1 to 3 values")
        _strings(ev.thread, where, "thread")
        unknown = [t for t in ev.thread if t not in THREADS]
        if unknown:
            raise ContentError(f"{where}: unknown thread {unknown[0]!r} (one of {', '.join(THREADS)})")

        # Sources.
        if not isinstance(ev.sources, list) or not ev.sources:
            raise ContentError(f"{where}: needs at least one [[event.source]]")
        ev.sources = sources = _sources(ev.sources, where, sources_bib)
        if ev.verified == "primary" and not any(s.kind == "primary" for s in sources):
            raise ContentError(f"{where}: verified = \"primary\" needs at least one source with kind = \"primary\"")
        ev.further = _further(ev.further, where, terms)
        _check_reading_links(ev, where)

        # Cross-references (related ids are checked once every id is known).
        claimed = set()
        _strings(ev.claims, where, "claims")
        for claim in ev.claims:
            m = CLAIM.fullmatch(claim)
            if not m:
                raise ContentError(f"{where}: claim {claim!r} must look like ep001-c03")
            if int(m.group(1)) not in numbers:
                raise ContentError(f"{where}: claim {claim!r} names an episode that is not in episodes.toml")
            claimed.add(int(m.group(1)))
        if not isinstance(ev.episodes, list) or not all(isinstance(e, int) and not isinstance(e, bool) for e in ev.episodes):
            raise ContentError(f"{where}: episodes must be a list of episode numbers")
        if len(set(ev.episodes)) != len(ev.episodes):
            raise ContentError(f"{where}: episodes has a duplicate")
        for number in ev.episodes:
            if number not in numbers:
                raise ContentError(f"{where}: episode {number} is not in episodes.toml")
            if number in claimed:
                raise ContentError(f"{where}: episode {number} is already linked through a claim")
        _strings(ev.related, where, "related")
        if ev.image is not None:
            ev.image = _image(ev.image, ev, where, root, terms, files)
        events.append(ev)

    for ev in events:
        for other in ev.related:
            if other == ev.id or other not in ids:
                raise ContentError(f"timeline.toml, event {ev.id}: related id {other!r} is not another event in the file")

    left = set()
    for before, ev in zip(events, events[1:], strict=False):
        if ev.sort_key < before.sort_key:
            raise ContentError(f"timeline.toml, event {ev.id}: out of order (it is dated before {before.id}, which comes first)")
        if ev.era != before.era:
            left.add(before.era)
            if ev.era in left:
                raise ContentError(f"timeline.toml, event {ev.id}: the {ev.era!r} era is not contiguous in the file")
    _check_history_images(root, events, files)
    return events


# ---------------------------------------------------------------- the Research page counts: content/research.toml
FALSIFIER_STATUSES = ("excluded", "armed")
FALSIFIER_ID = re.compile(r"[a-z0-9-]+")
RESEARCH_KEYS = {"pin", "checked", "consistency_entries", "falsifier"}


@dataclass
class Research:
    pin: str
    checked: str
    consistency_entries: int
    falsifiers: dict  # id -> status, in file order

    @property
    def armed(self):
        return sum(status == "armed" for status in self.falsifiers.values())


def load_research(root: Path, today=None):
    """content/research.toml: the counts the Research page shows, read by hand from AVE-Core at the commit in pin."""
    path = root / "content" / "research.toml"
    if not path.is_file():
        raise ContentError("content/research.toml does not exist")
    today = today or datetime.date.today()
    raw = tomllib.loads(path.read_text(encoding="utf-8"))
    unknown = sorted(set(raw) - RESEARCH_KEYS)
    if unknown:
        raise ContentError(f"research.toml: unknown key {unknown[0]!r} (one of {', '.join(sorted(RESEARCH_KEYS))})")
    pin = raw.get("pin")
    if not isinstance(pin, str) or not re.fullmatch(r"[0-9a-f]{40}", pin):
        raise ContentError("research.toml: pin must be the full 40-character AVE-Core commit SHA")
    checked = raw.get("checked")
    if not isinstance(checked, datetime.date) or isinstance(checked, datetime.datetime):
        raise ContentError("research.toml: checked must be a date, YYYY-MM-DD (unquoted)")
    if checked > today:
        raise ContentError(f"research.toml: checked {checked.isoformat()} is in the future")
    entries = raw.get("consistency_entries")
    if not isinstance(entries, int) or isinstance(entries, bool) or entries < 0:
        raise ContentError("research.toml: consistency_entries must be a whole number, 0 or more")
    items = raw.get("falsifier", [])
    if not isinstance(items, list) or not all(isinstance(i, dict) for i in items):
        raise ContentError("research.toml: falsifiers must be [[falsifier]] tables")
    falsifiers = {}
    for n, item in enumerate(items, 1):
        where = f"research.toml, falsifier {item.get('id') or '#' + str(n)}"
        unknown = sorted(set(item) - {"id", "status"})
        if unknown:
            raise ContentError(f"{where}: unknown key {unknown[0]!r} (the fields are id and status)")
        fid, status = item.get("id"), item.get("status")
        if not isinstance(fid, str) or not FALSIFIER_ID.fullmatch(fid):
            raise ContentError(f"{where}: id must be lowercase letters, digits and hyphens")
        if fid in falsifiers:
            raise ContentError(f"{where}: duplicate id")
        if status not in FALSIFIER_STATUSES:
            raise ContentError(f"{where}: unknown status {status!r} (one of {', '.join(FALSIFIER_STATUSES)})")
        falsifiers[fid] = status
    return Research(pin=pin, checked=checked.isoformat(), consistency_entries=entries, falsifiers=falsifiers)


# ---------------------------------------------------------------- corrections: content/errata.md
ERRATA_HEADER = re.compile(r"<!-- Copied from Grant-L/electron-plumber-notes ERRATA\.md at commit ([0-9a-f]{40})\. Do not edit here\. -->")
ERRATA_ENTRY = re.compile(r"## (cor-\d{3,}) \u2014 Episode (\d{3}) \((ep\d{3}-c\d{2,})\) \u2014 (CORRECTED|RETRACTED|CLARIFIED)")
# The five bullets of an entry, in the order the notes repo's publish step writes them.
ERRATA_FIELDS = (("date", "Date"), ("was", "As aired"), ("now", "Correction"), ("why", "How it happened"),
                 ("vehicle", "Corrected via"))
ERRATA_NONE = "*No corrections to date.*"
CORRECTION_KINDS = {"corrected": "Corrected", "retracted": "Retracted", "clarified": "Clarified"}
VEHICLE = re.compile(r"description|pinned-comment|erratum-short|segment ep(\d{3})")


@dataclass
class Correction:
    id: str        # cor-001
    episode: int
    claim: str     # ep001-c03
    kind: str      # a CORRECTION_KINDS key
    date: str      # YYYY-MM-DD
    was: str       # As aired, inline HTML
    now: str       # Correction, inline HTML
    why: str       # How it happened, inline HTML
    vehicle: str   # description | pinned-comment | erratum-short | segment epNNN


def load_errata(root: Path, episodes, today=None):
    """content/errata.md, the notes repo's ERRATA.md copied verbatim, as a list of Correction, newest first.
    A missing file means no corrections yet: []."""
    path = root / "content" / "errata.md"
    if not path.is_file():
        return []
    today = today or datetime.date.today()
    lines = path.read_text(encoding="utf-8").splitlines()
    m = ERRATA_HEADER.fullmatch(lines[0]) if lines else None
    if not m:
        raise ContentError("content/errata.md: line 1 must be '<!-- Copied from Grant-L/electron-plumber-notes ERRATA.md "
                           "at commit <40-character SHA>. Do not edit here. -->'")
    if m.group(1) != load_bib(root).sha:
        raise ContentError("content/errata.md: copied from a different notes commit than content/sources.bib; "
                           "re-copy both from the same notes commit")

    entries, current = [], None
    for n, line in enumerate(lines[1:], 2):
        if line.startswith("## "):
            current = (n, line, [])
            entries.append(current)
        elif current is not None and line.strip():
            current[2].append((n, line))
        elif current is None and line.startswith(("- ", "* ")):
            raise ContentError(f"content/errata.md, line {n}: a bullet before the first '## cor-NNN' entry")
    if not entries and ERRATA_NONE not in (line.strip() for line in lines):
        raise ContentError(f"content/errata.md: no entries, so it must say {ERRATA_NONE!r}")

    numbers = {e.number: e for e in episodes}
    prefixes = [f"- **{label}:**" for _, label in ERRATA_FIELDS]
    errata = []
    for n, heading, body in entries:
        m = ERRATA_ENTRY.fullmatch(heading)
        if not m:
            raise ContentError(f"content/errata.md, line {n}: a heading must look like "
                               f"'## cor-001 \u2014 Episode 001 (ep001-c03) \u2014 CORRECTED', got {heading[:80]!r}")
        cor_id, number, claim, kind = m.groups()
        where = f"content/errata.md, {cor_id}"
        if any(c.id == cor_id for c in errata):
            raise ContentError(f"{where}: duplicate id")
        if number != claim[2:5]:
            raise ContentError(f"{where}: Episode {number} does not match claim {claim}")
        ep = numbers.get(int(number))
        if ep is None:
            raise ContentError(f"{where}: Episode {number} is not in episodes.toml")
        if ep.status != "published":
            raise ContentError(f"{where}: Episode {number} is not published")

        for i, prefix in enumerate(prefixes):
            if i >= len(body) or not (body[i][1] + " ").startswith(prefix + " "):
                at = f"line {body[i][0]}" if i < len(body) else "the end of the entry"
                raise ContentError(f"{where}: expected '{prefix}' at {at}; an entry is exactly five bullets, in order: "
                                   + ", ".join(label for _, label in ERRATA_FIELDS))
        if len(body) > len(prefixes):
            raise ContentError(f"{where}, line {body[len(prefixes)][0]}: unexpected {body[len(prefixes)][1][:40]!r} after the five bullets")
        values = {name: body[i][1][len(prefixes[i]):].strip() for i, (name, _) in enumerate(ERRATA_FIELDS)}
        for name, label in ERRATA_FIELDS:
            if values[name] in ("", "?"):
                raise ContentError(f"{where}: {label} is empty or '?'")
            if name in ("was", "now", "why") and MD_LINK.search(values[name]):
                raise ContentError(f"{where}: {label} must not contain links")

        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", values["date"]):
            raise ContentError(f"{where}: Date must be a full date, YYYY-MM-DD")
        _partial_date(values["date"], where, "Date", today)
        if errata and values["date"] > errata[-1].date:
            raise ContentError(f"{where}: dated {values['date']}, after {errata[-1].id} above it; entries go newest first")
        vm = VEHICLE.fullmatch(values["vehicle"])
        if not vm:
            raise ContentError(f"{where}: unknown Corrected via {values['vehicle']!r} "
                               "(description, pinned-comment, erratum-short or segment epNNN)")
        if vm.group(1) and int(vm.group(1)) not in numbers:
            raise ContentError(f"{where}: Corrected via {values['vehicle']!r} names an episode that is not in episodes.toml")

        errata.append(Correction(id=cor_id, episode=int(number), claim=claim, kind=kind.lower(), date=values["date"],
                                 was=md.inline(values["was"]), now=md.inline(values["now"]), why=md.inline(values["why"]),
                                 vehicle=values["vehicle"]))
    return errata


def link_episodes(episodes, timeline, errata):
    """For each live episode, what the public records say about it: the History events that name it (in timeline
    order), its claims that an event or a correction names (sorted), and its corrections (newest first)."""
    for ep in episodes:
        ep.events, ep.claims, ep.corrections = [], [], []
        if not ep.live:
            continue
        prefix = f"ep{ep.number:03d}-"
        claims = set()
        for ev in timeline:
            mine = [c for c in ev.claims if c.startswith(prefix)]
            if mine or ep.number in ev.episodes:
                ep.events.append(ev)
                claims.update(mine)
        ep.corrections = [c for c in errata if c.episode == ep.number]
        claims.update(c.claim for c in ep.corrections)
        ep.claims = sorted(claims, key=lambda c: int(c.split("-c")[1]))
