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


@pytest.fixture
def content_root(tmp_path):
    """A writable copy of content/ under tmp_path, for tests that change the data. Returns the new root."""
    shutil.copytree(ROOT / "content", tmp_path / "content")
    (tmp_path / "content" / "episodes").mkdir(exist_ok=True)  # git does not track an empty folder
    return tmp_path


@pytest.fixture
def timeline_root(content_root):
    """content_root with the fixture sources.bib in place and no timeline yet."""
    (content_root / "content" / "sources.bib").write_text(fixture_bib(), encoding="utf-8")
    (content_root / "content" / "timeline.toml").unlink(missing_ok=True)
    return content_root
