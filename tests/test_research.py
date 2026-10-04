"""content/research.toml: the Research page's counts come from data, and a card and its count cannot disagree."""
import datetime

import pytest
from conftest import ROOT

import build
from sitegen import content

GOOD = '''pin = "0123456789abcdef0123456789abcdef01234567"
checked = 2026-10-01
consistency_entries = 44

[[falsifier]]
id = "electrostatic-gauntlet"
status = "excluded"

[[falsifier]]
id = "vacuum-birefringence"
status = "armed"
'''
TODAY = datetime.date(2026, 10, 3)


def load(root, text, today=TODAY):
    (root / "content" / "research.toml").write_text(text, encoding="utf-8")
    return content.load_research(root, today=today)


def research_page(out):
    return (out / "research" / "index.html").read_text(encoding="utf-8")


def test_the_stat_line_reads_from_the_real_file(tmp_path):
    counts = content.load_research(ROOT)
    assert (counts.armed, counts.consistency_entries) == (1, 44)
    build.build(tmp_path / "site")
    html = research_page(tmp_path / "site")
    assert ('Apache-2.0 &nbsp;&middot;&nbsp; 1 armed forward falsifier &nbsp;&middot;&nbsp; '
            "44 consistency-class entries</div>") in html
    assert "Excluded by data" in html and "Armed &middot; pre-registered" in html


def test_two_armed_falsifiers_read_as_a_plural(tmp_path, published_root):
    load(published_root, GOOD.replace('status = "excluded"', 'status = "armed"'))
    build.build(tmp_path / "site", root=published_root)
    html = research_page(tmp_path / "site")
    assert "2 armed forward falsifiers &nbsp;&middot;&nbsp; 44 consistency-class entries" in html
    assert "Excluded by data" not in html and html.count("Armed &middot; pre-registered") == 2


@pytest.mark.parametrize("change, message", [
    (('"0123456789abcdef0123456789abcdef01234567"', '"0123456"'), "pin must be the full 40-character"),
    (('"0123456789abcdef0123456789abcdef01234567"', '"0123456789ABCDEF0123456789ABCDEF01234567"'), "pin must be"),
    (("checked = 2026-10-01", "checked = 2026-10-04"), "is in the future"),
    (("checked = 2026-10-01", 'checked = "2026-10-01"'), "checked must be a date"),
    (("consistency_entries = 44", "consistency_entries = -1"), "consistency_entries must be"),
    (("consistency_entries = 44", 'consistency_entries = "44"'), "consistency_entries must be"),
    (('id = "vacuum-birefringence"', 'id = "electrostatic-gauntlet"'), "duplicate id"),
    (('id = "vacuum-birefringence"', 'id = "Vacuum_Birefringence"'), "id must be"),
    (('status = "armed"', 'status = "pending"'), "unknown status"),
    (("consistency_entries = 44", "consistency_entries = 44\ncolour = 1"), "unknown key 'colour'"),
    (('status = "armed"', 'status = "armed"\nnote = "x"'), "unknown key 'note'"),
])
def test_bad_research_data_is_refused_with_a_message(content_root, change, message):
    with pytest.raises(SystemExit, match=r"research\.toml.*" + message):
        load(content_root, GOOD.replace(*change))


def test_a_missing_file_is_refused(content_root):
    (content_root / "content" / "research.toml").unlink()
    with pytest.raises(SystemExit, match=r"research\.toml does not exist"):
        content.load_research(content_root)


@pytest.mark.parametrize("text, message", [
    (GOOD + '\n[[falsifier]]\nid = "proton-radius"\nstatus = "armed"\n', "'proton-radius' has no card"),
    (GOOD.replace('id = "vacuum-birefringence"', 'id = "vacuum-dichroism"'), "no \\[\\[falsifier\\]\\] with id 'vacuum-birefringence'"),
])
def test_a_card_and_its_data_entry_must_match(tmp_path, published_root, text, message):
    load(published_root, text)
    with pytest.raises(SystemExit, match=r"research\.toml: .*" + message):
        build.build(tmp_path / "site", root=published_root)
