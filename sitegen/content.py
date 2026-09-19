"""Load and validate the site's content: content/site.toml, content/episodes.toml, content/episodes/*.md."""
import datetime
import re
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

from . import md

ARCS = {"historical": "Historical", "speculative": "Speculative", "practical": "Practical"}
STATUSES = {"in-production", "published"}


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
