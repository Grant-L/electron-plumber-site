import re
from html.parser import HTMLParser

import pytest
from conftest import EP1_SOURCE, NOTES, PUBLISHED_EP1, ROOT, copy_static, errata_entry, fixture_errata

import build
import check
from sitegen import content, pages
from sitegen.html import Ctx

# Fixture events: real ids, dates and keys from the fixture bib; the wording is not real.
KELVIN = '''[[event]]
id = "1867-kelvin-vortex-atoms"
date = "1867-02-18"
date_basis = "read"
title = "Fixture Kelvin title"
summary = "Fixture summary."
era = "ether"
class = "theory"
thread = ["vortex-atoms"]
verified = "primary"
checked_by = "Historian"
checked_date = "2026-10-03"
{extra}
  [[event.source]]
  key = "kelvin1867vortex"
  kind = "primary"
'''
MICHELSON = KELVIN.replace("1867-kelvin-vortex-atoms", "1887-michelson-morley").replace('"1867-02-18"', '"1887-11"') \
    .replace("Fixture Kelvin title", "Fixture Michelson title").replace('date_basis = "read"', 'date_basis = "published"')


def kelvin(extra=""):
    return KELVIN.format(extra=extra)


def michelson(extra=""):
    return MICHELSON.format(extra=extra)


def write(root, *, timeline=None, errata=None, episodes=None, notes=None):
    c = root / "content"
    if timeline is not None:
        (c / "timeline.toml").write_text(timeline, encoding="utf-8")
    if errata is not None:
        (c / "errata.md").write_text(fixture_errata(errata), encoding="utf-8")
    if episodes is not None:
        (c / "episodes.toml").write_text(episodes, encoding="utf-8")
    if notes is not None:
        (c / "episodes" / "001-x.md").write_text(notes, encoding="utf-8")


def build_site(tmp_path, root, **files):
    write(root, **files)
    site = tmp_path / "site"
    build.build(site, root=root)
    return site


def read(site, path):
    return (site / path).read_text(encoding="utf-8")


def section(html, id):
    m = re.search(rf'<section class="block" id="{id}">(.*?)</section>', html, re.S)
    return m.group(1) if m else None


class Ids(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if a.get("id"):
            self.ids.append((tag, a["id"], a.get("class", "")))


def ids(html):
    p = Ids()
    p.feed(html)
    return p.ids


# ------------------------------------------------------------------ 1: today's public build
def test_todays_public_build_shows_none_of_it(tmp_path):
    build.build(tmp_path / "site")
    site = tmp_path / "site"
    assert not list((site / "episodes").glob("*/index.html"))
    assert "tl__episodes" not in read(site, "history/index.html")
    assert check.check(site) == []
    for page in ("index.html", "episodes/index.html", "history/index.html", "corrections/index.html"):
        html = read(site, page)
        assert not any(mark in html for mark in ("ep-claims", "ep-sources", "ep-history", "ledger__row")), page


# ------------------------------------------------------------------ 2: [[episode.source]] refusals
IN_PRODUCTION = '[[episode]]\nnumber = 1\nslug = "001-x"\ntitle = "X"\nstatus = "in-production"\n'


def test_a_source_on_an_in_production_episode_is_refused(content_root):
    write(content_root, episodes=IN_PRODUCTION + EP1_SOURCE)
    with pytest.raises(SystemExit, match="sources go with a published episode"):
        content.load(content_root)


@pytest.mark.parametrize("sources, message", [
    (EP1_SOURCE.replace("kelvin1867vortex", "nobody1900nothing"), "'nobody1900nothing' is not in content/sources.bib"),
    (EP1_SOURCE + EP1_SOURCE, "listed twice"),
    (EP1_SOURCE.replace('kind = "primary"', 'kind = "primary"\n  doi = "10.9999/other"'), "doi disagrees with sources.bib"),
    (EP1_SOURCE.replace('kind = "primary"', 'kind = "tertiary"'), "unknown kind"),
    (EP1_SOURCE.replace('kind = "primary"', 'kind = "primary"\n  url = "http://example.org/"'), "https://"),
    (EP1_SOURCE.replace('kind = "primary"', 'kind = "primary"\n  pages = "3"'), "pages"),
    ("", "a published historical episode needs at least one [[episode.source]]"),
])
def test_bad_episode_sources_are_refused(tmp_path, published_root, sources, message):
    with pytest.raises(SystemExit, match=re.escape(message)):
        build_site(tmp_path, published_root, episodes=PUBLISHED_EP1 + sources)


@pytest.mark.parametrize("key", ["events", "claims", "corrections", "sources"])
def test_derived_fields_are_not_content_fields(content_root, key):
    write(content_root, episodes=PUBLISHED_EP1 + f"{key} = []\n")
    with pytest.raises(SystemExit, match="not a content field"):
        content.load(content_root)


# ------------------------------------------------------------------ 3: sources
def test_sources_render_as_citations(tmp_path, published_root):
    two = EP1_SOURCE + EP1_SOURCE.replace("kelvin1867vortex", "fan2023electron").replace('kind = "primary"', 'kind = "secondary"\n  locator = "sec. 2"')
    html = read(build_site(tmp_path, published_root, episodes=PUBLISHED_EP1 + two), "episodes/001-x/index.html")
    block = section(html, "ep-sources")
    assert block.startswith('<h2>Sources</h2><ol class="tl__sources">')
    assert "<cite>Fixture entry kelvin1867vortex</cite>. Ann Author and Will Writer. Fixture Journal 1, 1\u20132 (2000)." in block
    assert "Fixture Journal 1, 1\u20132 (2000), sec. 2." in block and block.count("<li>") == 2


def test_a_non_historical_episode_without_sources_has_no_sources_section(tmp_path, published_root):
    html = read(build_site(tmp_path, published_root, episodes=PUBLISHED_EP1.replace('"historical"', '"practical"')),
                "episodes/001-x/index.html")
    assert 'id="ep-sources"' not in html and section(html, "corrections") is not None


# ------------------------------------------------------------------ 4, 5: History, both ways
def test_a_claim_links_both_ways(tmp_path, published_root):
    site = build_site(tmp_path, published_root, timeline=kelvin('claims = ["ep001-c03"]'))
    page, history = read(site, "episodes/001-x/index.html"), read(site, "history/index.html")
    claims = section(page, "ep-claims")
    assert f"<h2>Claims</h2><p>{pages.CLAIMS_INTRO}</p>" in claims
    assert ('<li id="ep001-c03"><code>ep001-c03</code> &middot; As aired &middot; On the History page: '
            '<a href="../../history/#1867-kelvin-vortex-atoms">Fixture Kelvin title</a></li>') in claims
    assert section(page, "ep-history") == (
        '<h2>On the History page</h2><ul class="ep-history"><li>Read <time datetime="1867-02-18">18 February 1867</time> '
        '<a href="../../history/#1867-kelvin-vortex-atoms">Fixture Kelvin title</a> (claim <a href="#ep001-c03">ep001-c03</a>)</li></ul>')
    para = re.search(r'<p class="small tl__episodes">(.*?)</p>', history).group(1)
    assert 'href="../episodes/001-x/#ep001-c03"' in para
    assert re.sub(r"<[^>]+>", "", para) == "In Episode 001 (claim ep001-c03)"
    assert check.check(site) == []


def test_an_episode_link_lists_the_event_with_no_claim(tmp_path, published_root):
    page = read(build_site(tmp_path, published_root, timeline=kelvin("episodes = [1]")), "episodes/001-x/index.html")
    assert section(page, "ep-history").endswith('<a href="../../history/#1867-kelvin-vortex-atoms">Fixture Kelvin title</a></li></ul>')
    assert 'id="ep-claims"' not in page


def test_history_and_claims_keep_timeline_order_and_sort_claims(tmp_path, published_root):
    timeline = kelvin('claims = ["ep001-c10", "ep001-c02"]') + "\n" + michelson('claims = ["ep001-c02"]')
    page = read(build_site(tmp_path, published_root, timeline=timeline), "episodes/001-x/index.html")
    assert [i for _, i, cls in ids(page) if i.startswith("ep001-")] == ["ep001-c02", "ep001-c10"]
    history = section(page, "ep-history")
    assert history.index("Fixture Kelvin title") < history.index("Fixture Michelson title")
    assert "(claims <a href=\"#ep001-c10\">ep001-c10</a>, <a href=\"#ep001-c02\">ep001-c02</a>)" in history
    c02 = re.search(r'<li id="ep001-c02">(.*?)</li>', page).group(1)
    assert "Fixture Kelvin title</a>, <a href=\"../../history/#1887-michelson-morley\">Fixture Michelson title</a>" in c02


# ------------------------------------------------------------------ 6, 7, 8, 11b: corrections
def test_a_correction_renders_a_ledger_row_and_hides_the_fallback(tmp_path, published_root):
    page = read(build_site(tmp_path, published_root, errata=[errata_entry(claim="ep001-c04")]), "episodes/001-x/index.html")
    assert page.count('id="corrections"') == 1
    block = section(page, "corrections")
    assert block.startswith('<h2>Corrections</h2><div class="ledger__head" aria-hidden="true"><div>Claim</div>')
    assert ('<div class="ledger__row" id="cor-001"><div><span class="vh">Claim</span> <a href="#ep001-c04">ep001-c04</a></div>'
            '<div><span class="vh">What I said</span> Fixture as aired.</div>'
            '<div><span class="vh">What&rsquo;s right</span> Fixture correction.</div>'
            '<div><span class="vh">Fixed in</span> Pinned comment &middot; <time datetime="2026-03-01">1 March 2026</time> '
            '&middot; Corrected</div></div>') in block
    assert "ERRATA.md" not in block and pages.CORRECTIONS_FALLBACK not in page
    claim = re.search(r'<li id="ep001-c04">(.*?)</li>', page).group(1)
    assert claim == '<code>ep001-c04</code> &middot; Corrected &middot; <a href="#cor-001">cor-001</a>'


def test_no_corrections_leaves_the_corrections_block_as_it_is_today(tmp_path, published_root):
    page = read(build_site(tmp_path, published_root), "episodes/001-x/index.html")
    assert section(page, "corrections") == "<h2>Corrections</h2>" + pages.CORRECTIONS_FALLBACK
    assert "ledger__head" not in page and "ledger__row" not in page


NOTES_WITH_CORRECTIONS = NOTES + "\n## Corrections\n\nFixture: none to date.\n"


def test_notes_with_their_own_corrections_section_keep_one_corrections_id(tmp_path, published_root):
    page = read(build_site(tmp_path, published_root, notes=NOTES_WITH_CORRECTIONS), "episodes/001-x/index.html")
    assert page.count('id="corrections"') == 1
    assert section(page, "corrections") == "<h2>Corrections</h2><p>Fixture: none to date.</p>"
    assert pages.CORRECTIONS_FALLBACK not in page

    page = read(build_site(tmp_path, published_root, errata=[errata_entry()]), "episodes/001-x/index.html")
    assert page.count('id="corrections"') == 1
    assert "Fixture: none to date." not in page and 'id="cor-001"' in section(page, "corrections")


def test_the_corrections_block_comes_after_the_new_sections(tmp_path, published_root):
    page = read(build_site(tmp_path, published_root, notes=NOTES_WITH_CORRECTIONS, timeline=kelvin('claims = ["ep001-c03"]')),
                "episodes/001-x/index.html")
    order = [i for tag, i, _ in ids(page) if tag == "section"]
    assert order == ["learning-goals", "notes", "ep-sources", "ep-claims", "ep-history", "corrections"]


def test_a_claim_with_several_corrections_takes_the_newest_status(tmp_path, published_root):
    errata = [errata_entry("cor-002", kind="RETRACTED", date="2026-05-01", via="erratum-short"), errata_entry("cor-001")]
    page = read(build_site(tmp_path, published_root, errata=errata), "episodes/001-x/index.html")
    claim = re.search(r'<li id="ep001-c03">(.*?)</li>', page).group(1)
    assert claim == '<code>ep001-c03</code> &middot; Retracted &middot; <a href="#cor-002">cor-002</a>, <a href="#cor-001">cor-001</a>'
    rows = re.findall(r'class="ledger__row" id="(cor-\d+)"', page)
    assert rows == ["cor-002", "cor-001"] and "Erratum short &middot;" in page


def test_a_clarification_renders_as_a_clarified_row(tmp_path, published_root):
    page = read(build_site(tmp_path, published_root, errata=[errata_entry(kind="CLARIFIED", via="description")]),
                "episodes/001-x/index.html")
    assert re.search(r'<div class="ledger__row" id="cor-001">.*Description edit &middot; <time[^>]*>1 March 2026</time> '
                     r'&middot; Clarified</div></div>', page)
    assert "&middot; Clarified &middot;" in re.search(r'<li id="ep001-c03">(.*?)</li>', page).group(1)


def test_a_segment_vehicle_links_its_episode_only_when_live(tmp_path, published_root):
    episodes = PUBLISHED_EP1 + EP1_SOURCE + '\n[[episode]]\nnumber = 2\nslug = "002-y"\ntitle = "Y"\nstatus = "in-production"\n'
    page = read(build_site(tmp_path, published_root, episodes=episodes, errata=[errata_entry(via="segment ep002")]),
                "episodes/001-x/index.html")
    assert "Segment in Episode 002 &middot;" in page
    page = read(build_site(tmp_path, published_root, episodes=PUBLISHED_EP1 + EP1_SOURCE, errata=[errata_entry(via="segment ep001")]),
                "episodes/001-x/index.html")
    assert 'Segment in <a href="../../episodes/001-x/">Episode 001</a> &middot;' in page


def test_ledger_row_can_link_the_claim_to_its_episode(published_root):
    _, episodes = content.load(published_root)
    cor = content.Correction("cor-001", 1, "ep001-c03", "corrected", "2026-03-01", "a", "b", "c", "description")
    row = pages._ledger_row(Ctx({}, episodes, "corrections/", "v"), cor, link_episode=True)
    assert '<a href="../episodes/001-x/#ep001-c03">ep001-c03</a>' in row


# ------------------------------------------------------------------ 9, 10, 11: the gate
def test_a_full_fixture_build_passes_the_gate_and_a_broken_claim_anchor_is_caught(tmp_path, published_root):
    timeline = kelvin('claims = ["ep001-c03"]') + "\n" + michelson("episodes = [1]")
    site = build_site(tmp_path, published_root, timeline=timeline,
                      errata=[errata_entry("cor-002", claim="ep001-c05", date="2026-04-01"), errata_entry()])
    assert check.check(site) == []
    about = site / "about" / "index.html"
    about.write_text(read(site, "about/index.html").replace("</main>", '<a href="../episodes/001-x/#ep001-c99">x</a></main>'),
                     encoding="utf-8")
    assert any("missing anchor" in p and "ep001-c99" in p for p in check.check(site))


def test_the_gate_reports_a_duplicate_id(tmp_path):
    build.build(tmp_path / "site")
    page = tmp_path / "site" / "about" / "index.html"
    page.write_text(page.read_text(encoding="utf-8").replace("</main>", '<p id="main">x</p></main>'), encoding="utf-8")
    assert "about/index.html: duplicate id 'main'" in check.check(tmp_path / "site")


def test_a_private_term_in_a_correction_is_caught_on_the_episode_page(tmp_path, published_root, monkeypatch):
    monkeypatch.setenv("FORBIDDEN_TERMS", "zzqx-corp")
    site = build_site(tmp_path, published_root, errata=[errata_entry(now="Funded by ZZQX-Corp.")])
    assert any(p.startswith("episodes/001-x/index.html") and "must never appear" in p for p in check.check(site))


# ------------------------------------------------------------------ 12: drafts
def test_a_draft_gets_no_corrections_but_its_timeline_links_render(timeline_root):
    """A drafts build without _private/: the in-production episode is marked as a draft by hand."""
    write(timeline_root, timeline=kelvin('claims = ["ep001-c03"]'), episodes=IN_PRODUCTION + 'arc = "historical"\n')
    site, episodes = content.load(timeline_root)
    timeline = content.load_timeline(timeline_root, episodes)
    with pytest.raises(SystemExit, match="Episode 001 is not published"):
        write(timeline_root, errata=[errata_entry()])
        content.load_errata(timeline_root, episodes)

    [ep] = episodes
    ep.draft, ep.sections = True, [("Learning goals", "<ul><li>a</li></ul>")]
    content.link_episodes(episodes, timeline, [])
    site["_root"] = str(ROOT)
    page = pages.episode(Ctx(site, episodes, ep.url, "v", timeline=timeline), ep)
    assert '<li id="ep001-c03">' in page and 'href="../../history/#1867-kelvin-vortex-atoms"' in page
    assert "ledger__row" not in page and 'name="robots" content="noindex"' in page
    history = pages.history(Ctx(site, episodes, "history/", "v", timeline=timeline))
    assert 'href="../episodes/001-x/#ep001-c03"' in history


def test_a_drafts_build_of_an_episode_with_no_arc_yet_shows_no_badge(tmp_path, timeline_root):
    """build.py --drafts with a fixture draft (in tmp_path, not the repo's _private/) for an episode with no arc."""
    write(timeline_root, episodes=IN_PRODUCTION)
    (timeline_root / "_private" / "drafts").mkdir(parents=True)
    (timeline_root / "_private" / "drafts" / "001-x.md").write_text(NOTES, encoding="utf-8")
    copy_static(timeline_root)
    build.build(tmp_path / "out", drafts=True, root=timeline_root)
    for page in ("index.html", "episodes/index.html", "episodes/001-x/index.html"):
        assert 'badge--"' not in (tmp_path / "out" / page).read_text(encoding="utf-8")
    assert "badge--" not in (tmp_path / "out" / "episodes" / "001-x" / "index.html").read_text(encoding="utf-8")


def test_links_to_an_in_production_episode_drop_silently(timeline_root):
    write(timeline_root, timeline=kelvin('claims = ["ep001-c03"]'), episodes=IN_PRODUCTION)
    _, episodes = content.load(timeline_root)
    content.link_episodes(episodes, content.load_timeline(timeline_root, episodes), [])
    assert (episodes[0].events, episodes[0].claims, episodes[0].corrections) == ([], [], [])
