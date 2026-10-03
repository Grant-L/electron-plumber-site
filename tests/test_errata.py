import datetime
import re

import pytest
from conftest import PUBLISHED_EP1, ROOT, errata_entry, fixture_errata

from sitegen import bib, content

TODAY = datetime.date(2026, 10, 3)


def load(root, text):
    (root / "content" / "errata.md").write_text(text, encoding="utf-8")
    _, episodes = content.load(root)
    return content.load_errata(root, episodes, today=TODAY)


# ------------------------------------------------------------------ 1, 2, 4: the committed copy, a good file, no file
def test_the_committed_errata_parses_and_is_pinned_to_the_bib_commit():
    first = (ROOT / "content" / "errata.md").read_text(encoding="utf-8").splitlines()[0]
    sha = content.ERRATA_HEADER.fullmatch(first).group(1)
    assert sha == bib.load(ROOT / "content" / "sources.bib").sha
    _, episodes = content.load(ROOT)
    assert content.load_errata(ROOT, episodes) == []


def test_two_entries_parse_newest_first(published_root):
    newer = errata_entry("cor-002", claim="ep001-c05", kind="CLARIFIED", date="2026-05-02", was="Was *two*.", now="Now two.",
                         why="Why two.", via="description")
    older = errata_entry(date="2026-03-01", via="segment ep001")
    errata = load(published_root, fixture_errata([newer, older]))
    assert [c.id for c in errata] == ["cor-002", "cor-001"]
    two, one = errata
    assert (two.episode, two.claim, two.kind, two.date, two.vehicle) == (1, "ep001-c05", "clarified", "2026-05-02", "description")
    assert (two.was, two.now, two.why) == ("Was <em>two</em>.", "Now two.", "Why two.")
    assert (one.kind, one.vehicle, one.was, one.now, one.why) == (
        "corrected", "segment ep001", "Fixture as aired.", "Fixture correction.", "Fixture cause.")


def test_no_errata_file_means_no_corrections(published_root):
    (published_root / "content" / "errata.md").unlink()
    _, episodes = content.load(published_root)
    assert content.load_errata(published_root, episodes) == []


# ------------------------------------------------------------------ 3: refusals
ONE = errata_entry()


def without(text, line):
    assert line in text
    return text.replace(line, "")


@pytest.mark.parametrize("text, message", [
    (fixture_errata([ONE]).split("\n", 1)[1], "line 1 must be"),
    (fixture_errata([ONE], sha="0123abc"), "line 1 must be"),
    (fixture_errata([ONE], sha="f" * 40), "re-copy both from the same notes commit"),
    (fixture_errata([ONE.replace(" \u2014 ", " - ")]), "a heading must look like"),
    (fixture_errata([ONE.replace("Episode 001", "Episode 002")]), "Episode 002 does not match claim ep001-c03"),
    (fixture_errata([ONE.replace("CORRECTED", "FIXED")]), "a heading must look like"),
    (fixture_errata([without(ONE, "- **How it happened:** Fixture cause.\n")]), "expected '- **How it happened:**'"),
    (fixture_errata([without(ONE, "- **Corrected via:** pinned-comment\n")]), "the end of the entry"),
    (fixture_errata([ONE + "- **Note:** extra\n"]), "after the five bullets"),
    (fixture_errata([ONE + "\nA stray paragraph.\n"]), "after the five bullets"),
    (fixture_errata([ONE + "\n### A subheading\n"]), "after the five bullets"),
    (fixture_errata([ONE.replace("- **Date:** 2026-03-01\n- **As aired:** Fixture as aired.\n",
                                 "- **As aired:** Fixture as aired.\n- **Date:** 2026-03-01\n")]), "expected '- **Date:**'"),
    (fixture_errata([errata_entry(why="?")]), "How it happened is empty or '?'"),
    (fixture_errata([errata_entry(now="")]), "Correction is empty or '?'"),
    (fixture_errata([errata_entry(date="2026-10-04")]), "in the future"),
    (fixture_errata([errata_entry(date="2026-02-30")]), "not a real date"),
    (fixture_errata([errata_entry(date="2026-03")]), "full date"),
    (fixture_errata([errata_entry("cor-001", date="2026-03-01"), errata_entry("cor-002", date="2026-04-01")]), "newest first"),
    (fixture_errata([errata_entry("cor-001"), errata_entry("cor-001")]), "duplicate id"),
    (fixture_errata([errata_entry(episode=9, claim="ep009-c01")]), "Episode 009 is not in episodes.toml"),
    (fixture_errata([errata_entry(was="See [the paper](https://example.org/).")]), "As aired must not contain links"),
    (fixture_errata([errata_entry(now="See <https://example.org/>.")]), "Correction must not contain links"),
    (fixture_errata([errata_entry(via="tweet")]), "unknown Corrected via"),
    (fixture_errata([errata_entry(via="segment ep009")]), "names an episode that is not in episodes.toml"),
    (fixture_errata().replace("*No corrections to date.*\n", ""), "No corrections to date"),
    (fixture_errata([ONE]).replace("Fixture preamble.", "- **Date:** 2026-03-01"), "a bullet before the first"),
])
def test_bad_errata_are_refused_with_a_message(published_root, text, message):
    with pytest.raises(SystemExit, match=re.escape(message)):
        load(published_root, text)


def test_an_entry_for_an_in_production_episode_is_refused(timeline_root):
    """The committed episodes.toml has Episode 001 in production."""
    with pytest.raises(SystemExit, match="Episode 001 is not published"):
        load(timeline_root, fixture_errata([ONE]))


def test_an_entry_for_a_later_published_episode_still_needs_it_in_episodes_toml(published_root):
    toml = published_root / "content" / "episodes.toml"
    toml.write_text(toml.read_text(encoding="utf-8") + '\n[[episode]]\nnumber = 2\nslug = "002-y"\ntitle = "Y"\nstatus = "in-production"\n',
                    encoding="utf-8")
    [cor] = load(published_root, fixture_errata([errata_entry(via="segment ep002")]))
    assert cor.vehicle == "segment ep002"
    with pytest.raises(SystemExit, match="Episode 002 is not published"):
        load(published_root, fixture_errata([errata_entry(episode=2, claim="ep002-c01")]))


def test_a_published_episode_loads_its_ledger_from_published_toml(content_root):
    (content_root / "content" / "episodes.toml").write_text(PUBLISHED_EP1, encoding="utf-8")
    (content_root / "content" / "episodes" / "001-x.md").write_text("## Learning goals\n\n- a\n", encoding="utf-8")
    sha = bib.load(content_root / "content" / "sources.bib").sha
    [cor] = load(content_root, fixture_errata([ONE], sha=sha))
    assert cor.id == "cor-001"


# ------------------------------------------------------------------ 5: escaping
def test_raw_html_in_an_entry_is_escaped(published_root):
    [cor] = load(published_root, fixture_errata([errata_entry(was="<script>alert(1)</script> & more")]))
    assert cor.was == "&lt;script&gt;alert(1)&lt;/script&gt; &amp; more"
