"""Reading links on History entries (a source's url and fulltext_url, and [[event.further]]) and the phone year row."""
import re

import pytest
from conftest import ROOT, fixture_bib
from test_timeline import EVENT, SEED, _built_with, _css_rules_at, load, parse, render

import check
from sitegen import content

FULLTEXT = "https://archive.org/details/fixture/page/1/mode/1up"
FURTHER_URL = "https://mathshistory.st-andrews.ac.uk/Biographies/Hamilton/"
NEW_COPY = ("Original paper", "Original letter", "Free full text", "Further reading", "tl__read", "tl__further")


def with_source(text, extra):
    return text.replace('  kind = "primary"\n', f'  kind = "primary"\n{extra}', 1)


def further(title="William Rowan Hamilton", publisher="MacTutor, University of St Andrews", url=FURTHER_URL):
    return f'\n  [[event.further]]\n  title = "{title}"\n  publisher = "{publisher}"\n  url = "{url}"\n'


def entry_html(html, id="1843-hamilton-quaternions"):
    return re.search(rf'<li class="tl" id="{id}".*?</article></li>', html).group(0)


def primary_li(html):
    return re.search(r'<ol class="tl__sources"><li>(.*?)</li>', html).group(1)


def card_source(li):
    """What site.js puts after "Source: " on the preview card: the li without its links, its mono spans, and the
    middot before a removed element."""
    return re.sub(r"\s+", " ", re.sub(r"(?: &middot; )?(?:<a\b[^>]*>.*?</a>|<span class=\"mono\">.*?</span>)", "", li)).strip()


# ------------------------------------------------------------------ loading
def test_reading_links_load(timeline_root):
    [ev] = load(timeline_root, with_source(EVENT, f'  fulltext_url = "{FULLTEXT}?page=3"\n') + further()
                + further("Hamilton's Research on Quaternions", "Trinity College Dublin",
                          "https://www.maths.tcd.ie/pub/HistMath/People/Hamilton/Quaternions.html"))
    assert ev.sources[0].fulltext_url == FULLTEXT + "?page=3"
    assert [(f.publisher, f.url) for f in ev.further] == [
        ("MacTutor, University of St Andrews", FURTHER_URL),
        ("Trinity College Dublin", "https://www.maths.tcd.ie/pub/HistMath/People/Hamilton/Quaternions.html")]


def test_an_event_without_reading_links_has_none(timeline_root):
    [ev] = load(timeline_root, EVENT)
    assert ev.further == [] and ev.sources[0].fulltext_url == ""


def test_the_host_allowlist_is_exactly_the_vetted_hosts():
    assert content.FURTHER_HOSTS == {
        "www.maths.tcd.ie", "archive.org", "mathshistory.st-andrews.ac.uk", "ajsonline.org", "www.aps.org",
        "history.aip.org", "www.nobelprize.org", "journals.aps.org", "arxiv.org", "physics.aps.org", "royalsocietypublishing.org"}


@pytest.mark.parametrize("change, message", [
    (lambda t: with_source(t, '  fulltext_url = "http://archive.org/details/x"\n'), "fulltext_url must start with https://"),
    (lambda t: t + further(url="http://mathshistory.st-andrews.ac.uk/Biographies/Hamilton/"), "further url must start with https://"),
    (lambda t: with_source(t, '  url = "https://example.org/letter"\n'), "url host 'example.org' is not in FURTHER_HOSTS"),
    (lambda t: t + further(url="https://archive.org.example.net/x"), "further url host 'archive.org.example.net' is not in"),
    (lambda t: with_source(t, f'  fulltext_url = "{FULLTEXT}?utm_source=x"\n'), "tracking parameter 'utm_source'"),
    (lambda t: t + further(url=FURTHER_URL + "?fbclid=1"), "tracking parameter 'fbclid'"),
    (lambda t: t + further(url=FURTHER_URL + "?gclid=1"), "tracking parameter 'gclid'"),
    (lambda t: t + further(url=FURTHER_URL + "?ref=x"), "tracking parameter 'ref'"),
    (lambda t: t + further(url=FURTHER_URL + "?q=x"), "query parameter 'q' is not allowed (only id, page)"),
    (lambda t: t + further() + further(url="https://arxiv.org/abs/1") + further(url="https://arxiv.org/abs/2"),
     "at most 2 [[event.further]] blocks, got 3"),
    (lambda t: t + further(title="x" * 101), "further title must be one line of 1 to 100 characters"),
    (lambda t: t + further(title=""), "further title must be one line of 1 to 100 characters"),
    (lambda t: t + further(publisher="x" * 61), "further publisher must be one line of 1 to 60 characters"),
    (lambda t: t + further(title="See [TODO]"), "further title has a capitalised bracket placeholder"),
    (lambda t: t + further(title="An AVE essay"), "further title must spell out the framework's name"),
    (lambda t: t + further(title="A *bold* essay"), "further title must be plain text"),
    (lambda t: t + further() + further(url=FURTHER_URL), "further url duplicates the further url"),
    (lambda t: with_source(t, f'  fulltext_url = "{FURTHER_URL}"\n') + further(), "further url duplicates the source"),
    (lambda t: with_source(t, '  fulltext_url = "https://doi.org/10.0000/fixture.hamilton1865letter"\n'),
     "host 'doi.org' is not in FURTHER_HOSTS"),
    (lambda t: t + further(url="https://github.com/Grant-L/some-repo/blob/main/x.md"), "further url points at a private location"),
    (lambda t: t + further(url="https://raw.githubusercontent.com/grant-l/some-repo/main/x.md"), "points at a private location"),
    (lambda t: t + further(url="https://archive.org/details/_private/notes"), "further url points at a private location"),
    (lambda t: t + further().replace('url = "', 'note = "x"\n  url = "'), "unexpected keyword argument 'note'"),
])
def test_bad_reading_links_are_refused(timeline_root, change, message):
    with pytest.raises(SystemExit, match=r"timeline\.toml, event 1843-hamilton-quaternions(, [^:]+)?: .*" + re.escape(message)):
        load(timeline_root, change(EVENT))


def test_a_fulltext_url_that_is_the_doi_target_is_a_duplicate(timeline_root, monkeypatch):
    monkeypatch.setattr(content, "FURTHER_HOSTS", content.FURTHER_HOSTS | {"doi.org"})
    with pytest.raises(SystemExit, match="fulltext_url duplicates the source 'hamilton1865letter' doi"):
        load(timeline_root, with_source(EVENT, '  fulltext_url = "https://doi.org/10.0000/FIXTURE.hamilton1865letter"\n'))


def test_a_private_term_in_a_further_title_is_refused_without_repeating_it(timeline_root, monkeypatch):
    monkeypatch.setenv("FORBIDDEN_TERMS", "zzqx-corp")
    with pytest.raises(SystemExit) as exc:
        load(timeline_root, EVENT + further(title="Funded by ZZQX-Corp"))
    assert "must never appear" in str(exc.value) and "zzqx" not in str(exc.value).lower()


# ------------------------------------------------------------------ rendering
def test_the_primary_source_links_the_original_paper_with_its_doi(timeline_root):
    li = primary_li(render(timeline_root, EVENT))
    doi = "10.0000/fixture.hamilton1865letter"
    assert li.endswith(f'<a class="tl__read" href="https://doi.org/{doi}">Original paper</a> <span class="mono">doi:{doi}</span> '
                       '<span class="mono">Primary</span>')
    assert "Free full text" not in li and "rel=" not in li


def test_free_full_text_shows_only_when_present(timeline_root):
    li = primary_li(render(timeline_root, with_source(EVENT, f'  fulltext_url = "{FULLTEXT}"\n')))
    assert f'</span> &middot; <a href="{FULLTEXT}">Free full text</a> <span class="mono">Primary</span>' in li
    assert li.count("Free full text") == 1


@pytest.mark.parametrize("title, label", [("Letter to Rev. Archibald H. Hamilton, 5 August 1865", "Original letter"),
                                          ("Fixture entry hamilton1865letter", "Original")])
def test_without_a_doi_the_url_is_the_original(timeline_root, title, label):
    bib = fixture_bib().replace("title = {Fixture entry hamilton1865letter}", f"title = {{{title}}}")
    bib = bib.replace("  doi = {10.0000/fixture.hamilton1865letter}\n", "").replace("year = {2000},\n}", "year = {2000}\n}")
    (timeline_root / "content" / "sources.bib").write_text(bib, encoding="utf-8")
    url = "https://archive.org/details/lifeofsirwilliam02gravuoft/page/434/mode/1up"
    fulltext = "https://www.maths.tcd.ie/pub/HistMath/People/Hamilton/Letters/BroomeBridge.html"
    li = primary_li(render(timeline_root, with_source(EVENT, f'  url = "{url}"\n  fulltext_url = "{fulltext}"\n')))
    assert f'<a class="tl__read" href="{url}">{label}</a> &middot; <a href="{fulltext}">Free full text</a>' in li
    assert "doi" not in li


def test_with_only_a_fulltext_url_the_line_shows_just_free_full_text(timeline_root):
    bib = fixture_bib().replace("  doi = {10.0000/fixture.hamilton1865letter}\n", "").replace("year = {2000},\n}", "year = {2000}\n}")
    (timeline_root / "content" / "sources.bib").write_text(bib, encoding="utf-8")
    li = primary_li(render(timeline_root, with_source(EVENT, f'  fulltext_url = "{FULLTEXT}"\n')))
    assert li.endswith(f'(2000). <a class="tl__read" href="{FULLTEXT}">Free full text</a> <span class="mono">Primary</span>')
    assert "Original" not in li and "&middot;" not in li


def test_a_secondary_source_keeps_the_small_doi_link(timeline_root):
    text = EVENT + '\n  [[event.source]]\n  key = "secondary2000history"\n  kind = "secondary"\n'
    li = re.findall(r"<li>(.*?)</li>", entry_html(render(timeline_root, text)))[1]
    doi = "10.0000/fixture.secondary2000history"
    assert f'<a href="https://doi.org/{doi}" rel="noopener">doi:{doi}</a> <span class="mono">Secondary</span>' in li
    assert "tl__read" not in li


def test_further_reading_is_one_line_between_the_sources_and_the_check(timeline_root):
    html = entry_html(render(timeline_root, EVENT + further("Hamilton's \\\"quaternions\\\"") + further(
        "Einstein: Image and Impact", "American Institute of Physics", "https://history.aip.org/exhibits/einstein/")))
    assert ('</ol><p class="small tl__further">Further reading: <a href="https://mathshistory.st-andrews.ac.uk/Biographies/Hamilton/">'
            "Hamilton\u2019s \u201cquaternions\u201d</a> (MacTutor, University of St Andrews); "
            '<a href="https://history.aip.org/exhibits/einstein/">Einstein: Image and Impact</a> (American Institute of Physics).</p>'
            '<p class="mono tl__checked">') in html


def test_no_further_line_when_there_is_none(timeline_root):
    assert "tl__further" not in render(timeline_root, EVENT) and "Further reading" not in render(timeline_root, EVENT)


def test_the_preview_card_source_line_gets_nothing_new(timeline_root):
    before = card_source(primary_li(render(timeline_root, EVENT)))
    assert before == "<cite>Fixture entry hamilton1865letter</cite>. Ann Author and Will Writer. Fixture Journal 1, 1\u20132 (2000)."
    html = render(timeline_root, with_source(EVENT, f'  fulltext_url = "{FULLTEXT}"\n') + further())
    assert card_source(primary_li(html)) == before
    assert not any(s in re.search(r'data-oneliner="[^"]*"|$', html).group(0) for s in NEW_COPY)
    js = (ROOT / "static" / "js" / "site.js").read_text(encoding="utf-8")
    assert 'querySelector(".mono:last-child").textContent === "Primary"' in js
    assert 'n.previousSibling?.nodeValue === " \\u00b7 "' in js
    assert not any(s in js for s in NEW_COPY)


# ------------------------------------------------------------------ the phone year row
def test_the_year_row_links_every_entry_by_its_year(timeline_root):
    html = render(timeline_root, SEED)
    nav = re.search(r'<nav class="tl-years" aria-label="Jump to a year">(.*?)</nav>', html).group(1)
    links = re.findall(r'<a href="#([\w-]+)">(\d{4})</a>', nav)
    ids = [item["id"] for item in parse(html).items]
    assert [i for i, _ in links] == ids and [y for _, y in links] == [i[:4] for i in ids]
    assert html.index('class="tl-years"') < html.index("data-filters") < html.index('<ol class="timeline">')


def test_the_committed_timeline_gives_eight_year_links_to_existing_ids(tmp_path):
    import build
    build.build(tmp_path / "site")
    html = (tmp_path / "site" / "history" / "index.html").read_text(encoding="utf-8")
    nav = re.search(r'<nav class="tl-years" aria-label="Jump to a year">(.*?)</nav>', html).group(1)
    links = re.findall(r'<a href="#([\w-]+)">(\d{4})</a>', nav)
    assert [y for _, y in links] == ["1843", "1867", "1887", "1905", "1928", "1948", "2008", "2023"]
    assert all(f'<li class="tl" id="{i}"' in html for i, _ in links) and nav.count("<a ") == 8


def _declared(width, selector):
    decls = {}
    for sel, d in _css_rules_at((ROOT / "static" / "css" / "site.css").read_text(encoding="utf-8"), width):
        if selector in [s.strip() for s in sel.split(",")]:
            decls.update(d)
    return decls


@pytest.mark.parametrize("width", [561, 768, 1280])
def test_the_year_row_is_hidden_above_560px(width):
    assert _declared(width, ".tl-years")["display"] == "none"


@pytest.mark.parametrize("width", [320, 390, 560])
def test_the_year_row_shows_on_phones_with_44px_targets_that_wrap(width):
    row, link = _declared(width, ".tl-years"), _declared(width, ".tl-years a")
    assert row["display"] == "grid" and row["grid-template-columns"] == "repeat(4, 1fr)"
    assert link["min-height"] == "44px" and "position" not in row and "overflow" not in row
    pad = 24 if width < 360 else width * 6.667 / 100  # --pad: clamp(24px, 6.667vw, 96px)
    assert (width - 2 * pad) / 4 >= 44


# ------------------------------------------------------------------ the gate
def test_a_history_page_with_reading_links_passes_every_check(tmp_path, timeline_root):
    text = SEED.replace('  key = "hamilton1865letter"\n  kind = "primary"\n',
                        f'  key = "hamilton1865letter"\n  kind = "primary"\n  fulltext_url = "{FULLTEXT}"\n', 1)
    text = text.replace('[[event]]\nid = "1887-michelson-morley"', further().lstrip("\n") + '\n[[event]]\nid = "1887-michelson-morley"')
    site = _built_with(tmp_path, timeline_root, text)
    assert check.check(site) == []


def test_every_new_href_on_the_built_history_page_is_external_https_or_resolves(tmp_path):
    import build
    build.build(tmp_path / "site")
    assert check.check(tmp_path / "site") == []
    html = (tmp_path / "site" / "history" / "index.html").read_text(encoding="utf-8")
    hrefs = re.findall(r'class="tl__read" href="([^"]+)"|href="([^"]+)">Free full text<', html)
    hrefs = [a or b for a, b in hrefs] + re.findall(r'<a href="([^"]+)">[^<]*</a> \(', html)
    hrefs += re.findall(r'href="(#[^"]+)"', re.search(r'<nav class="tl-years".*?</nav>', html).group(0))
    assert len(hrefs) == 7 + 8 + 13 + 8  # Kelvin's paper has no DOI or url: it shows only its free full text
    for href in hrefs:
        assert href.startswith("https://") or f'id="{href[1:]}"' in html, href
