import datetime
import re
import types
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
from pathlib import Path

import pytest
from conftest import EP1_SOURCE, copy_static

import build
import check
from sitegen import feed

A = "{http://www.w3.org/2005/Atom}"

GOLDEN = """<?xml version="1.0" encoding="utf-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <id>tag:electron-plumber.com,2026:feed</id>
  <title>The Electron Plumber</title>
  <subtitle>I plumb electrons for a living, I just want to know what they ARE</subtitle>
  <link rel="self" type="application/atom+xml" href="https://electron-plumber.com/feed.atom"/>
  <link rel="alternate" type="text/html" href="https://electron-plumber.com/"/>
  <updated>2026-09-19T00:00:00Z</updated>
  <author><name>Grant Lindblom</name></author>
</feed>
"""


def episode(number=1, title="Fixture title", date="2026-11-01", excerpt="A fixture excerpt.", status="published"):
    extra = f'youtube_id = "abcdefghijk"\ndate = "{date}"\nexcerpt = "{excerpt}"\n' + EP1_SOURCE if status == "published" else ""
    return f'[[episode]]\nnumber = {number}\nslug = "{number:03d}-x"\ntitle = "{title}"\narc = "historical"\nstatus = "{status}"\n' + extra


@pytest.fixture
def fixture_build(timeline_root, tmp_path):
    """Build the site from fixture episodes.toml text. Returns (built site path, parsed feed root)."""
    copy_static(timeline_root)

    def run(episodes_toml, drafts=False):
        (timeline_root / "content" / "episodes.toml").write_text(episodes_toml, encoding="utf-8")
        for block in episodes_toml.split("[[episode]]")[1:]:
            if 'status = "published"' in block:
                number = int(re.search(r"number = (\d+)", block)[1])
                (timeline_root / "content" / "episodes" / f"{number:03d}-x.md").write_text("## Notes\n\nFixture notes.\n", encoding="utf-8")
        out = tmp_path / ("drafts" if drafts else "site")
        build.build(out, drafts=drafts, root=timeline_root)
        return out, ET.parse(out / "feed.atom").getroot()
    return run


def test_todays_feed_is_valid_empty_and_exact(tmp_path):
    build.build(tmp_path / "site")
    path = tmp_path / "site" / "feed.atom"
    root = ET.parse(path).getroot()
    assert root.tag == f"{A}feed" and root.findall(f"{A}entry") == []
    assert root.findtext(f"{A}updated") == feed.FEED_EPOCH
    assert [x.get("href") for x in root.findall(f"{A}link") if x.get("rel") == "self"] == ["https://electron-plumber.com/feed.atom"]
    assert path.read_bytes() == GOLDEN.encode("utf-8")
    assert check.check(tmp_path / "site") == []


def test_a_published_episode_becomes_one_entry(fixture_build):
    site, root = fixture_build(episode(title="What is an Electron?"))
    (entry,) = root.findall(f"{A}entry")
    assert entry.findtext(f"{A}id") == "tag:electron-plumber.com,2026:episode-001"
    assert entry.findtext(f"{A}title") == "What is an Electron?"
    assert entry.find(f"{A}link").attrib == {"rel": "alternate", "type": "text/html", "href": "https://electron-plumber.com/episodes/001-x/"}
    assert entry.findtext(f"{A}published") == entry.findtext(f"{A}updated") == "2026-11-01T00:00:00Z"
    assert entry.find(f"{A}category").attrib == {"term": "historical", "label": "Historical"}
    assert entry.findtext(f"{A}summary") == "A fixture excerpt." and entry.find(f"{A}summary").get("type") == "text"
    assert entry.find(f"{A}content") is None
    text = (site / "feed.atom").read_text(encoding="utf-8")
    assert "youtube" not in text.lower() and "abcdefghijk" not in text
    assert check.check_xml(site) == []


def test_entries_are_newest_first(fixture_build):
    _, root = fixture_build(episode(1, date="2026-11-01") + episode(2, date="2026-12-15"))
    assert [e.findtext(f"{A}id")[-3:] for e in root.findall(f"{A}entry")] == ["002", "001"]
    assert root.findtext(f"{A}updated") == "2026-12-15T00:00:00Z"


def test_the_feed_is_deterministic(fixture_build, monkeypatch):
    site, _ = fixture_build(episode())
    first = (site / "feed.atom").read_bytes()

    class OtherDay(datetime.date):
        @classmethod
        def today(cls):
            return cls(2031, 5, 17)

    class OtherTime(datetime.datetime):
        @classmethod
        def now(cls, tz=None):
            return cls(2031, 5, 17, 12, tzinfo=tz)

        @classmethod
        def utcnow(cls):
            return cls(2031, 5, 17, 12)

    monkeypatch.setattr(feed, "datetime", types.SimpleNamespace(date=OtherDay, datetime=OtherTime, timezone=datetime.timezone))
    again, _ = fixture_build(episode())
    assert (again / "feed.atom").read_bytes() == first


def test_markup_characters_stay_well_formed_and_round_trip(fixture_build):
    title, excerpt = "Fixture & <title> ]]> end", "An excerpt with & and < and ]]> in it."
    site, root = fixture_build(episode(title=title, excerpt=excerpt))
    (entry,) = root.findall(f"{A}entry")
    assert entry.findtext(f"{A}title") == title and entry.findtext(f"{A}summary") == excerpt
    assert check.check_xml(site) == []


def test_a_draft_never_reaches_the_feed(fixture_build, content_root):
    drafts = content_root / "_private" / "drafts"
    drafts.mkdir(parents=True)
    (drafts / "001-x.md").write_text("## Notes\n\nFixture draft.\n", encoding="utf-8")
    site, root = fixture_build(episode(status="in-production"), drafts=True)
    assert (site / "episodes" / "001-x" / "index.html").is_file()
    assert root.findall(f"{A}entry") == []


def test_an_episode_in_production_is_not_in_the_feed(fixture_build):
    _, root = fixture_build(episode(status="in-production"))
    assert root.findall(f"{A}entry") == []


@pytest.fixture
def published_site(fixture_build):
    site, _ = fixture_build(episode())
    return site


def _edit_feed(site, old, new):
    path = site / "feed.atom"
    text = path.read_text(encoding="utf-8")
    assert old in text
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


@pytest.mark.parametrize("old, new, message", [
    ("</feed>\n", "", "not well-formed"),
    ("<id>tag:electron-plumber.com,2026:feed</id>", "", "missing <id>"),
    ("/episodes/001-x/", "/episodes/nope/", "broken link"),
    ("<title>Fixture title</title>", "<title>The AVE episode</title>", "spelled out"),
    ("A fixture excerpt.", "[PLACEHOLDER]", "placeholder"),
])
def test_the_xml_gate_catches_problems(published_site, old, new, message):
    _edit_feed(published_site, old, new)
    assert any(p.startswith("feed.atom: ") and message in p for p in check.check(published_site))


def test_a_private_term_in_the_feed_is_caught(published_site, monkeypatch):
    monkeypatch.setenv("FORBIDDEN_TERMS", "zzqx-corp")
    _edit_feed(published_site, "A fixture excerpt.", "Funded by ZZQX-Corp.")
    assert any(p.startswith("feed.atom: ") and "must never appear" in p for p in check.check(published_site))


def test_the_sitemap_passes_the_xml_gate(tmp_path):
    build.build(tmp_path / "site")
    assert (tmp_path / "site" / "sitemap.xml").is_file()
    assert check.check_xml(tmp_path / "site") == []
    (tmp_path / "site" / "sitemap.xml").write_text("<urlset>", encoding="utf-8")
    assert any(p.startswith("sitemap.xml: not well-formed") for p in check.check_xml(tmp_path / "site"))


class FeedLinks(HTMLParser):
    def __init__(self):
        super().__init__()
        self.alternates, self.footer_links, self._footer, self._href = [], [], False, None

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "link" and a.get("rel") == "alternate" and a.get("type") == "application/atom+xml":
            self.alternates.append(a)
        self._footer |= tag == "footer"
        if tag == "a" and self._footer:
            self._href = a.get("href")

    def handle_endtag(self, tag):
        self._footer &= tag != "footer"
        self._href = None if tag == "a" else self._href

    def handle_data(self, data):
        if self._href is not None and data.strip() == "Feed":
            self.footer_links.append(self._href)


def _resolves_to_feed(site, page, href):
    target = site / href.lstrip("/") if href.startswith("/") else (page.parent / href).resolve()
    return target == (site / "feed.atom").resolve()


def test_every_page_links_the_feed_from_its_head_and_footer(tmp_path):
    site = (tmp_path / "site").resolve()
    build.build(site)
    pages = [p for p in site.rglob("*.html") if 'http-equiv="refresh"' not in p.read_text(encoding="utf-8")]
    assert len(pages) >= 7
    for page in pages:
        parser = FeedLinks()
        parser.feed(page.read_text(encoding="utf-8"))
        (alt,) = parser.alternates
        assert alt["title"] == "The Electron Plumber: episodes" and _resolves_to_feed(site, page, alt["href"]), page
        (footer,) = parser.footer_links
        assert _resolves_to_feed(site, page, footer), page


def test_feed_module_uses_only_the_standard_library():
    source = Path(feed.__file__).read_text(encoding="utf-8")
    imports = {line.split()[1].split(".")[0] for line in source.splitlines() if line.startswith(("import ", "from "))}
    assert imports <= {"datetime", "xml", ""}
