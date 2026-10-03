"""Load and validate the site's content: content/site.toml, content/episodes.toml, content/episodes/*.md,
and the History timeline, content/timeline.toml, against its sources in content/sources.bib."""
import datetime
import re
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

from . import bib, md

ARCS = {"historical": "Historical", "speculative": "Speculative", "practical": "Practical"}
STATUSES = {"in-production", "published"}

# The History filters. Each changes only by a spec change; the order is the chip order.
# An era's bounds are inclusive years of an event's sort key; None is an open end.
ERAS = {
    "aether": ("Fields and the aether, 1840\u20131904", 1840, 1904),
    "relativity": ("Relativity and the classical electron, 1905\u20131924", 1905, 1924),
    "quantum-electron": ("The quantum electron, 1925\u20131949", 1925, 1949),
    "precision": ("Precision measurement, 1950\u2013present", 1950, None),
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
DOI = re.compile(r"10\.\d{4,9}/\S+")
MD_LINK = re.compile(r"\]\(|<https?://")


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
    draft: bool = False
    sections: list = field(default_factory=list)  # [(title, html)]

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
        for internal in ("draft", "sections"):
            if internal in item:
                raise ContentError(f"episodes.toml: {internal!r} is not a content field")
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


# ---------------------------------------------------------------- the History timeline
@dataclass
class Source:
    key: str
    kind: str
    locator: str = ""
    doi: str = ""
    url: str = ""
    note: str = ""
    entry: object = field(default=None, init=False, repr=False)  # the bib.Entry, set by load_timeline


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

    @property
    def precision(self):
        return {1: "year", 2: "month", 3: "day"}[len(self.date.split("-"))] if self.date else ""

    @property
    def sort_key(self):
        return date_key(self.date or self.not_before or self.not_after)


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


def load_timeline(root: Path, episodes, today=None):
    """content/timeline.toml as a list of Event, checked against content/sources.bib and the episodes.
    A missing file means no timeline yet: []."""
    path = root / "content" / "timeline.toml"
    bib_path = root / "content" / "sources.bib"
    if not path.is_file():
        return []
    today = today or datetime.date.today()
    raw = tomllib.loads(path.read_text(encoding="utf-8")).get("event", [])
    if not raw:
        return []
    try:
        sources_bib = bib.load(bib_path)
    except bib.BibError as exc:
        raise ContentError(f"content/sources.bib: {exc}") from None
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
        sources = []
        for raw_source in ev.sources:
            if not isinstance(raw_source, dict):
                raise ContentError(f"{where}: each source must be a table")
            try:
                src = Source(**raw_source)
            except TypeError as exc:
                raise ContentError(f"{where}, source: {exc}") from None
            for key in ("key", "kind", "locator", "doi", "url", "note"):
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
            if src.url and not src.url.startswith("https://"):
                raise ContentError(f"{where}, source {src.key!r}: url must start with https://")
            src.entry = sources_bib[src.key]
            sources.append(src)
        ev.sources = sources
        if ev.verified == "primary" and not any(s.kind == "primary" for s in sources):
            raise ContentError(f"{where}: verified = \"primary\" needs at least one source with kind = \"primary\"")

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
    return events
