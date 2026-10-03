import shutil
from pathlib import Path

import pytest

import build

ROOT = Path(build.__file__).resolve().parent

# A stand-in for the site's copy of sources.bib. Fixture data only: titles and DOIs are placeholders, not citations.
FIXTURE_SHA = "0123456789abcdef0123456789abcdef01234567"
FIXTURE_KEYS = ("hamilton1865letter", "michelson1887ether", "einstein1905elektrodynamik", "dirac1928electron",
                "schwinger1948moment", "hanneke2008electron", "fan2023electron", "kelvin1867vortex", "secondary2000history")


def fixture_bib(keys=FIXTURE_KEYS):
    entries = "".join(
        f"@article{{{key},\n  author = {{Author, Ann and Writer, Will}},\n  title = {{Fixture entry {key}}},\n"
        f"  journal = {{Fixture Journal}},\n  volume = {{1}},\n  pages = {{1--2}},\n  year = {{2000}},\n"
        f"  doi = {{10.0000/fixture.{key}}}\n}}\n\n" for key in keys)
    return (f"% Copied from Grant-L/electron-plumber-notes sources.bib at commit {FIXTURE_SHA}. Do not edit here.\n\n"
            + entries)


PUBLISHED_EP1 = ('[[episode]]\nnumber = 1\nslug = "001-x"\ntitle = "X"\narc = "historical"\nstatus = "published"\n'
                 'youtube_id = "abcdefghijk"\ndate = "2026-01-01"\nruntime = "18 min"\nexcerpt = "An excerpt."\n')
EP1_SOURCE = '\n  [[episode.source]]\n  key = "kelvin1867vortex"\n  kind = "primary"\n'
# The shape of the notes template, with fixture text.
NOTES = ("# X\n\n<!-- fixture -->\n**Series:** Fixture\n\n## Learning goals\n\n- Fixture goal.\n\n"
         "## Notes\n\nFixture notes.\n")


def errata_entry(id="cor-001", episode=1, claim="ep001-c03", kind="CORRECTED", date="2026-03-01", *,
                 was="Fixture as aired.", now="Fixture correction.", why="Fixture cause.", via="pinned-comment"):
    """One entry in the notes repo's ERRATA.md format. Fixture text only."""
    return (f"## {id} \u2014 Episode {episode:03d} ({claim}) \u2014 {kind}\n\n- **Date:** {date}\n- **As aired:** {was}\n"
            f"- **Correction:** {now}\n- **How it happened:** {why}\n- **Corrected via:** {via}\n")


def fixture_errata(entries=(), sha=FIXTURE_SHA):
    """A stand-in for content/errata.md, newest entry first."""
    return (f"<!-- Copied from Grant-L/electron-plumber-notes ERRATA.md at commit {sha}. Do not edit here. -->\n"
            "# Errata\n\nFixture preamble.\n\n" + ("\n".join(entries) if entries else "*No corrections to date.*\n"))


@pytest.fixture
def content_root(tmp_path):
    """A writable copy of content/ under tmp_path, for tests that change the data. Returns the new root."""
    shutil.copytree(ROOT / "content", tmp_path / "content")
    (tmp_path / "content" / "episodes").mkdir(exist_ok=True)  # git does not track an empty folder
    return tmp_path


@pytest.fixture
def timeline_root(content_root):
    """content_root with the fixture sources.bib and errata.md in place, both from the fixture commit, and no timeline yet."""
    (content_root / "content" / "sources.bib").write_text(fixture_bib(), encoding="utf-8")
    (content_root / "content" / "errata.md").write_text(fixture_errata(), encoding="utf-8")
    (content_root / "content" / "timeline.toml").unlink(missing_ok=True)
    return content_root


@pytest.fixture
def published_root(timeline_root):
    """timeline_root with Episode 001 published (one source, minimal notes) and a copy of static/, so that
    build.build(out, root=published_root) builds a complete fixture site."""
    (timeline_root / "content" / "episodes.toml").write_text(PUBLISHED_EP1 + EP1_SOURCE, encoding="utf-8")
    (timeline_root / "content" / "episodes" / "001-x.md").write_text(NOTES, encoding="utf-8")
    shutil.copytree(ROOT / "static", timeline_root / "static")
    return timeline_root
