import gzip
import re
from html.parser import HTMLParser

import pytest
from conftest import PUBLISHED_EP1, ROOT, fixture_bib

import build
import check
from sitegen import bib, content, pages
from sitegen.html import NAV, Ctx

# Fixture events: the field values that matter are real (ids, dates, eras, classes, threads, keys); the wording is not.
EVENT = '''[[event]]
id = "1843-hamilton-quaternions"
date = "1843-10-16"
title = "Fixture title"
summary = "Fixture summary."
era = "ether"
class = "theory"
thread = ["vectors-quaternions"]
verified = "primary"
checked_by = "Historian"
checked_date = "2026-10-03"

  [[event.source]]
  key = "hamilton1865letter"
  kind = "primary"
'''


def event(id, date, era, cls, thread, key, *, basis="", extra=""):
    lines = [f'[[event]]\nid = "{id}"', f'date = "{date}"' if date else "", f'date_basis = "{basis}"' if basis else "",
             f'title = "Title {id}"\nsummary = "Summary {id}."\nera = "{era}"\nclass = "{cls}"',
             "thread = [" + ", ".join(f'"{t}"' for t in thread) + "]",
             'verified = "primary"\nchecked_by = "Historian"\nchecked_date = "2026-10-03"', extra,
             f'\n  [[event.source]]\n  key = "{key}"\n  kind = "primary"\n']
    return "\n".join(line for line in lines if line)


# The Historian's v1 seed (spec section 1): dates, bases, eras, classes, threads and source keys.
SEED = "\n".join([
    event("1843-hamilton-quaternions", "1843-10-16", "ether", "theory", ["vectors-quaternions"], "hamilton1865letter"),
    event("1887-michelson-morley", "1887-11", "ether", "experiment", ["ether"], "michelson1887ether", basis="published"),
    event("1905-einstein-electrodynamics", "1905-06-30", "relativity", "theory", ["relativity", "electromagnetism"],
          "einstein1905elektrodynamik", basis="received"),
    event("1928-dirac-electron", "1928-02-01", "quantum-electron", "theory", ["quantum", "spin-and-moment", "g-factor"],
          "dirac1928electron", basis="published"),
    event("1948-schwinger-moment", "1948-02-15", "quantum-electron", "theory", ["quantum", "g-factor"], "schwinger1948moment",
          basis="published"),
    event("2008-hanneke-electron-moment", "2008-03-26", "precision", "measurement", ["g-factor", "spin-and-moment"],
          "hanneke2008electron", basis="published"),
    event("2023-fan-electron-moment", "2023-02-13", "precision", "measurement", ["g-factor", "spin-and-moment"], "fan2023electron",
          basis="published"),
])
SEED_KEYS = re.findall(r'key = "(\w+)"', SEED)


def load(root, text):
    (root / "content" / "timeline.toml").write_text(text, encoding="utf-8")
    _, episodes = content.load(root)
    return content.load_timeline(root, episodes)


def render(root, text):
    events = load(root, text)
    site, episodes = content.load(root)
    site["_root"] = str(ROOT)
    return pages.history(Ctx(site, episodes, "history/", "v", timeline=events))


class Items(HTMLParser):
    """The <li class="tl"> items, the filter block and the chips of a History page."""

    def __init__(self):
        super().__init__()
        self.items, self.filter, self.chips, self.times = [], None, {}, []
        self._group = None

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "li" and a.get("class") == "tl":
            self.items.append(a)
        if "data-filters" in a:
            self.filter = a
        if a.get("data-filter"):
            self._group = a["data-filter"]
            self.chips[self._group] = []
        if tag == "button" and self._group:
            self.chips[self._group].append(a["data-value"])
        if tag == "time":
            self.times.append(a["datetime"])


def parse(html):
    p = Items()
    p.feed(html)
    return p


# ------------------------------------------------------------------ 1-4: loading and refusals
def test_a_minimal_event_loads(timeline_root):
    [ev] = load(timeline_root, EVENT)
    assert ev.cls == "theory" and ev.date_basis == "event" and ev.precision == "day"
    assert ev.sources[0].entry.key == "hamilton1865letter"


def test_no_timeline_file_means_no_events(content_root):
    (content_root / "content" / "timeline.toml").unlink(missing_ok=True)
    assert content.load_timeline(content_root, []) == []


LONG = "x" * 121


@pytest.mark.parametrize("change, message", [
    (('title = "Fixture title"\n', ""), "title"),
    (('era = "ether"', 'era = "ether"\ncolour = "red"'), "colour"),
    (('era = "ether"', 'era = "ether"\ntags = ["theory"]'), "tags"),
    (('"1843-10-16"', '"1843-13"'), "not a real date"),
    (('"1843-10-16"', '"1843-02-30"'), "not a real date"),
    (('"1843-10-16"', '"97"'), "YYYY"),
    (('"1843-10-16"', '"2999"'), "in the future"),
    (('date = "1843-10-16"', 'date = "1843-10-16"\nend = "1842"'), "later than date"),
    (('date = "1843-10-16"', 'date = "1843-10-16"\ncirca = true'), "circa"),
    (('date = "1843-10-16"', 'date = "1843-10-16"\ndate_basis = "printed"'), "date_basis"),
    (('id = "1843-hamilton-quaternions"', 'id = "hamilton-quaternions"'), "id must look like"),
    (('id = "1843-hamilton-quaternions"', 'id = "1843-Hamilton"'), "id must look like"),
    (('\n  [[event.source]]\n  key = "hamilton1865letter"\n  kind = "primary"\n', ""), "at least one"),
    (('key = "hamilton1865letter"', 'key = "nobody1900nothing"'), "not in content/sources.bib"),
    (('kind = "primary"', 'kind = "primary"\n  doi = "doi:10.1/x"'), "does not look like a DOI"),
    (('kind = "primary"', 'kind = "primary"\n  doi = "10.9999/other"'), "disagrees with sources.bib"),
    (('kind = "primary"', 'kind = "primary"\n  url = "http://example.org/"'), "https://"),
    (('verified = "primary"', 'verified = "yes"'), "unknown verified"),
    (('kind = "primary"', 'kind = "secondary"'), 'needs at least one source with kind = "primary"'),
    (('checked_by = "Historian"\n', ""), "checked_by"),
    (('checked_date = "2026-10-03"\n', ""), "checked_date"),
    (('"Historian"', '"00000000-1111-2222-3333-444444444444"'), "public display name"),
    (('"Historian"', '"historian bot 2"'), "public display name"),
    (('"2026-10-03"', '"2999-01-01"'), "in the future"),
    (('"2026-10-03"', '"2026-10"'), "full date"),
    (('era = "ether"', 'era = "ether"\nclaims = ["ep1-c3"]'), "must look like ep001-c03"),
    (('era = "ether"', 'era = "ether"\nclaims = ["ep009-c01"]'), "not in episodes.toml"),
    (('era = "ether"', 'era = "ether"\nclaims = ["ep001-c03", "ep001-c03"]'), "duplicate"),
    (('era = "ether"', 'era = "ether"\nclaims = ["ep001-c03"]\nepisodes = [1]'), "already linked through a claim"),
    (('era = "ether"', 'era = "ether"\nepisodes = [9]'), "not in episodes.toml"),
    (('era = "ether"', 'era = "ether"\nrelated = ["1900-nothing"]'), "related id"),
    (('era = "ether"', 'era = "ether"\nrelated = ["1843-hamilton-quaternions"]'), "related id"),
    (('"Fixture summary."', '"See [the letter](https://example.org/)."'), "links"),
    (('"Fixture title"', f'"{LONG}"'), "title must be"),
    (('"Fixture title"', '"Two\\nlines"'), "title must be"),
    (('"Fixture summary."', '"' + "y" * 601 + '"'), "summary must be"),
    (('era = "ether"\n', ""), "era"),
    (('era = "ether"', 'era = "classical"'), "unknown era"),
    (('class = "theory"\n', ""), "'class'"),
    (('class = "theory"', 'class = "mathematics"'), "unknown class"),
    (('thread = ["vectors-quaternions"]', "thread = []"), "1 to 3"),
    (('thread = ["vectors-quaternions"]', 'thread = ["ether", "quantum", "charge", "cosmology"]'), "1 to 3"),
    (('thread = ["vectors-quaternions"]', 'thread = ["mathematics"]'), "unknown thread"),
    (('thread = ["vectors-quaternions"]', 'thread = ["ether", "ether"]'), "duplicate"),
])
def test_bad_timeline_data_is_refused_with_a_message(timeline_root, change, message):
    with pytest.raises(SystemExit, match=re.escape(message)):
        load(timeline_root, EVENT.replace(*change))


def test_a_duplicate_id_is_refused(timeline_root):
    with pytest.raises(SystemExit, match="duplicate id"):
        load(timeline_root, EVENT + "\n" + EVENT)


def test_the_year_in_an_id_is_not_checked_against_the_date(timeline_root):
    [ev] = load(timeline_root, EVENT.replace('id = "1843-hamilton-quaternions"', 'id = "1866-x"').replace('"1843-10-16"', '"1867"'))
    assert ev.id == "1866-x" and ev.date == "1867" and ev.precision == "year"


def test_secondary_only_loads_without_a_primary_source(timeline_root):
    [ev] = load(timeline_root, EVENT.replace('verified = "primary"', 'verified = "secondary-only"')
                .replace('key = "hamilton1865letter"\n  kind = "primary"', 'key = "secondary2000history"\n  kind = "secondary"'))
    assert ev.verified == "secondary-only" and [s.kind for s in ev.sources] == ["secondary"]


# ------------------------------------------------------------------ 5-7a: date basis, bounds, order, eras
KELVIN = event("1867-kelvin-vortex-atoms", "1867-02-18", "ether", "theory", ["vortex-atoms"], "kelvin1867vortex", basis="read")


def test_kelvin_read_date_renders_with_its_basis(timeline_root):
    html = render(timeline_root, KELVIN)
    assert 'Read <time datetime="1867-02-18">18 February 1867</time>' in html


def bounded(id, extra, era="ether"):
    return event(id, "", era, "theory", ["ether"], "hamilton1865letter", extra=extra)


@pytest.mark.parametrize("extra, text", [
    ('not_after = "1850"', 'Before <time datetime="1850">1850</time>'),
    ('not_before = "1845"', 'After <time datetime="1845">1845</time>'),
    ('not_before = "1845"\nnot_after = "1850"', 'Between <time datetime="1845">1845</time> and <time datetime="1850">1850</time>'),
])
def test_bounds_load_and_render(timeline_root, extra, text):
    assert text in render(timeline_root, bounded("1850-bounded", extra))


@pytest.mark.parametrize("extra, message", [
    ('not_before = "1850"\nnot_after = "1850"', "earlier than not_after"),
    ('not_before = "1851"\nnot_after = "1850"', "earlier than not_after"),
    ('date = "1849"\nnot_after = "1850"', "not both"),
    ('not_after = "1850"\ncirca = true', "not with not_before"),
    ('not_after = "1850"\nend = "1851"', "not with not_before"),
    ("", "needs a date"),
])
def test_bad_bounds_are_refused(timeline_root, extra, message):
    with pytest.raises(SystemExit, match=message):
        load(timeline_root, bounded("1850-bounded", extra))


def test_a_bound_sorts_at_its_own_year(timeline_root):
    e1849 = event("1849-a", "1849", "ether", "theory", ["ether"], "hamilton1865letter")
    e1851 = event("1851-c", "1851", "ether", "theory", ["ether"], "hamilton1865letter")
    before = bounded("1850-b", 'not_after = "1850"')
    assert [e.id for e in load(timeline_root, "\n".join([e1849, before, e1851]))] == ["1849-a", "1850-b", "1851-c"]
    with pytest.raises(SystemExit, match="out of order"):
        load(timeline_root, "\n".join([before, e1849, e1851]))
    with pytest.raises(SystemExit, match="out of order"):
        load(timeline_root, "\n".join([e1849, e1851, before]))


def test_out_of_order_events_are_refused_naming_both(timeline_root):
    later = event("1887-later", "1887", "ether", "experiment", ["ether"], "michelson1887ether")
    with pytest.raises(SystemExit, match="1843-hamilton-quaternions.*1887-later"):
        load(timeline_root, later + "\n" + EVENT)


def test_non_contiguous_eras_are_refused(timeline_root, monkeypatch):
    """The era bounds already imply contiguity; this second check needs overlapping test eras to fire."""
    monkeypatch.setattr(content, "ERAS", {"a": ("A", 1840, 1904), "b": ("B", 1840, 1904)})
    text = "\n".join([event("1850-x", "1850", "a", "theory", ["ether"], "hamilton1865letter"),
                      event("1860-y", "1860", "b", "theory", ["ether"], "hamilton1865letter"),
                      event("1870-z", "1870", "a", "theory", ["ether"], "hamilton1865letter")])
    with pytest.raises(SystemExit, match="not contiguous"):
        load(timeline_root, text)


def test_an_unquoted_toml_date_is_accepted(timeline_root):
    [ev] = load(timeline_root, EVENT.replace('date = "1843-10-16"', "date = 1843-10-16"))
    assert ev.date == "1843-10-16"


@pytest.mark.parametrize("date, era, ok", [
    ("1904", "relativity", False), ("1905", "relativity", True), ("1924", "relativity", True), ("1925", "relativity", False),
    ("2025", "precision", True), ("1949", "precision", False), ("1904", "ether", True),
])
def test_era_bounds(timeline_root, date, era, ok):
    text = event(f"{date}-x", date, era, "theory", ["relativity"], "einstein1905elektrodynamik")
    if ok:
        assert load(timeline_root, text)[0].era == era
    else:
        with pytest.raises(SystemExit, match="outside the"):
            load(timeline_root, text)


def test_a_bounds_event_is_checked_on_its_sort_key_year(timeline_root):
    with pytest.raises(SystemExit, match="1905 is outside the 'ether' era"):
        load(timeline_root, bounded("1905-x", 'not_after = "1905"'))


@pytest.mark.parametrize("era", list(content.ERAS))
def test_an_1839_event_fits_no_era(timeline_root, era):
    with pytest.raises(SystemExit, match="outside the"):
        load(timeline_root, event("1839-x", "1839", era, "theory", ["ether"], "hamilton1865letter"))


# ------------------------------------------------------------------ 7b: the seed and the ship blocker
def test_the_seed_loads_when_every_key_is_in_the_bib(timeline_root):
    events = load(timeline_root, SEED)
    assert len(events) == 7
    assert [e.date for e in events] == ["1843-10-16", "1887-11", "1905-06-30", "1928-02-01", "1948-02-15", "2008-03-26", "2023-02-13"]
    assert 'Received <time datetime="1905-06-30">30 June 1905</time>' in render(timeline_root, SEED)


def test_the_seed_is_refused_without_hanneke2008electron(timeline_root):
    """Encodes the ship blocker: the seed cannot load until the bib copy carries hanneke2008electron."""
    keys = [k for k in SEED_KEYS if k != "hanneke2008electron"]
    (timeline_root / "content" / "sources.bib").write_text(fixture_bib(keys), encoding="utf-8")
    with pytest.raises(SystemExit, match="hanneke2008electron.*sources.bib"):
        load(timeline_root, SEED)


def test_the_seed_is_refused_without_a_bib_copy(timeline_root):
    (timeline_root / "content" / "sources.bib").unlink()
    with pytest.raises(SystemExit, match="sources.bib"):
        load(timeline_root, SEED)


def test_the_seed_sources_are_in_the_copied_bib():
    """Expected to fail until content/sources.bib is copied from a notes commit that has hanneke2008electron."""
    path = ROOT / "content" / "sources.bib"
    assert path.is_file(), "content/sources.bib has not been copied from Grant-L/electron-plumber-notes yet"
    missing = [k for k in SEED_KEYS if k not in bib.load(path)]
    assert not missing, f"not in content/sources.bib: {', '.join(missing)}"


# ------------------------------------------------------------------ 8-12: the page
def test_every_event_renders_without_javascript(timeline_root):
    events = load(timeline_root, SEED)
    html = render(timeline_root, SEED)
    p = parse(html)
    assert len(p.items) == len(events)
    for item, ev in zip(p.items, events, strict=True):
        assert item["id"] == ev.id and item["data-era"] == ev.era and item["data-class"] == ev.cls
        assert item["data-thread"] == " ".join(ev.thread) and item["data-verified"] == ev.verified
        assert "hidden" not in item
        assert f'<time datetime="{ev.date}">' in html
    assert p.filter is not None and "hidden" in p.filter
    assert html.count("Checked against the original") == 7
    assert "Historian" not in html  # the checked mark shows its date, never who checked


def test_the_secondary_only_mark_renders(timeline_root):
    html = render(timeline_root, EVENT.replace('verified = "primary"', 'verified = "secondary-only"'))
    assert "Secondary sources only" in html and 'data-verified="secondary-only"' in html


def test_the_page_shows_the_approved_copy(timeline_root):
    html = render(timeline_root, EVENT)
    assert pages.HISTORY_INTRO in html and pages.HISTORY_LEGEND in html
    assert f'content="{pages.HISTORY_DESCRIPTION}"' in html
    assert 'Checked <time datetime="2026-10-03">3 October 2026</time>' in html


def test_citation_text_comes_from_the_bib(timeline_root):
    html = render(timeline_root, EVENT)
    assert "<cite>Fixture entry hamilton1865letter</cite>. Ann Author and Will Writer. Fixture Journal 1, 1\u20132 (2000)." in html
    assert 'href="https://doi.org/10.0000/fixture.hamilton1865letter"' in html


def test_et_al_does_not_double_its_full_stop():
    entry = bib.Entry("article", "k", {"title": "T", "journal": "J", "year": "2023"}, ("A", "B", "C", "D"))
    assert "A et al. J (2023)." in pages._citation(entry, content.Source(key="k", kind="primary"))


@pytest.mark.parametrize("title, expected", [
    ("Is it?", "<cite>Is it?</cite> A. J (2023)."),
    ("It is!", "<cite>It is!</cite> A. J (2023)."),
    ("It is", "<cite>It is</cite>. A. J (2023)."),
    ("Q & <A>?", "<cite>Q &amp; &lt;A&gt;?</cite> A. J (2023)."),
])
def test_a_title_ending_in_punctuation_gets_no_extra_full_stop(title, expected):
    entry = bib.Entry("article", "k", {"title": title, "journal": "J", "year": "2023"}, ("A",))
    assert expected in pages._citation(entry, content.Source(key="k", kind="primary"))


def test_claims_render_only_for_published_episodes(timeline_root):
    text = EVENT.replace('era = "ether"', 'era = "ether"\nclaims = ["ep001-c03"]')
    html = render(timeline_root, text)  # Episode 001 is in production
    assert "ep001-c03" not in html and "episodes/001" not in html
    (timeline_root / "content" / "episodes.toml").write_text(PUBLISHED_EP1, encoding="utf-8")
    (timeline_root / "content" / "episodes" / "001-x.md").write_text("## Learning goals\n\n- a\n", encoding="utf-8")
    html = render(timeline_root, text)
    assert '<a href="../episodes/001-x/">Episode 001</a> (claim <a href="../episodes/001-x/#ep001-c03">ep001-c03</a>)' in html


def test_an_unpublished_episode_is_not_linked_through_episodes_either(timeline_root):
    html = render(timeline_root, EVENT.replace('era = "ether"', 'era = "ether"\nepisodes = [1]'))
    assert "tl__episodes" not in html and "episodes/001" not in html


def test_chips_are_all_plus_the_values_in_use(timeline_root):
    p = parse(render(timeline_root, SEED))
    assert p.chips["era"] == ["all", "ether", "relativity", "quantum-electron", "precision"]
    assert p.chips["class"] == ["all", "experiment", "measurement", "theory"]
    assert p.chips["thread"] == ["all", "ether", "electromagnetism", "vectors-quaternions", "relativity", "quantum",
                                 "spin-and-moment", "g-factor"]
    p = parse(render(timeline_root, EVENT))
    assert p.chips == {"era": ["all", "ether"], "thread": ["all", "vectors-quaternions"], "class": ["all", "theory"]}


def test_the_meta_line_shows_the_era_label_with_its_years_and_the_chip_shows_the_label(timeline_root):
    html = render(timeline_root, SEED)
    for meta in ("Fields and ether, 1840\u20131904", "Relativity, 1905\u20131924", "Quantum electron, 1925\u20131949",
                 "Precision, 1950\u2013present"):
        assert f"{meta} &middot; " in html
    for label in ("Fields and ether", "Relativity", "Quantum electron", "Precision"):
        assert f'aria-pressed="false">{label}</button>' in html


def test_timeline_text_is_escaped(timeline_root):
    html = render(timeline_root, EVENT.replace('"Fixture title"', '"X & <Y>"').replace('"Fixture summary."', '"a < b & c"'))
    assert "X &amp; &lt;Y&gt;" in html and "<Y>" not in html and "a &lt; b &amp; c" in html


def test_related_links_point_at_the_other_entry(timeline_root):
    other = event("1887-michelson-morley", "1887-11", "ether", "experiment", ["ether"], "michelson1887ether")
    html = render(timeline_root, EVENT.replace('era = "ether"', 'era = "ether"\nrelated = ["1887-michelson-morley"]') + "\n" + other)
    assert 'See also <a href="#1887-michelson-morley">Title 1887-michelson-morley</a>' in html


def test_an_empty_timeline_renders_the_empty_state_without_filters():
    site, episodes = content.load(ROOT)
    site["_root"] = str(ROOT)
    html = pages.history(Ctx(site, episodes, "history/", "v", timeline=[]))
    assert "Nothing published yet." in html and "data-filters" not in html and pages.HISTORY_INTRO in html


# ------------------------------------------------------------------ 13-17: shell, links and the gate
def test_nav_puts_history_right_after_episodes(tmp_path):
    assert [name for name, _ in NAV][:2] == ["Episodes", "History"]
    build.build(tmp_path / "site")
    history = (tmp_path / "site" / "history" / "index.html").read_text(encoding="utf-8")
    assert '<a href="../history/" aria-current="page">History</a>' in history
    for other in ("index.html", "episodes/index.html", "corrections/index.html", "about/index.html"):
        text = (tmp_path / "site" / other).read_text(encoding="utf-8")
        assert re.search(r'href="[./]*history/">History</a>', text) and 'aria-current="page">History' not in text


def test_without_javascript_the_narrow_header_still_shows_the_nav(tmp_path):
    build.build(tmp_path / "site")
    css = (ROOT / "static" / "css" / "site.css").read_text(encoding="utf-8")
    breakpoint = re.search(r"@media \(max-width: (\d+)px\) \{\n  \.nav-toggle \{ display: flex; \}", css).group(1)
    for page in ("index.html", "history/index.html", "episodes/index.html", "404.html"):
        head = (tmp_path / "site" / page).read_text(encoding="utf-8").split("</head>")[0]
        assert f"<noscript><style>@media (max-width: {breakpoint}px) {{ .nav-toggle {{ display: none; }}" in head


def test_the_menu_breakpoint_matches_in_site_css_and_html_py():
    from sitegen import html
    css = (ROOT / "static" / "css" / "site.css").read_text(encoding="utf-8")
    in_css = re.findall(r"@media \(max-width: (\d+)px\) \{\n  \.nav-toggle \{ display: flex; \}", css)
    in_html = re.findall(r"@media \(max-width: (\d+)px\)", html.NOSCRIPT_NAV)
    assert len(in_css) == 1 and in_html == in_css


def _css_rules_at(css, width):
    """(selector, declarations) for every rule that applies at a viewport of `width` px, in source order.
    Only the plain-rule and @media (max-width: Npx) forms that site.css uses are understood."""
    css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    rules, i = [], 0
    while True:
        m = re.compile(r"\s*([^{}]+)\{").match(css, i)
        if not m:
            return rules
        head, i = m.group(1).strip(), m.end()
        if head.startswith("@"):
            depth, start = 1, i
            while depth:
                depth += {"{": 1, "}": -1}.get(css[i], 0)
                i += 1
            limit = re.fullmatch(r"@media \(max-width: (\d+)px\)", head)
            if limit and width <= int(limit.group(1)):
                rules += _css_rules_at(css[start:i - 1], width)
        else:
            end = css.index("}", i)
            decls = dict(d.split(":", 1) for d in css[i:end].split(";") if ":" in d)
            rules.append((head, {k.strip(): v.strip() for k, v in decls.items()}))
            i = end + 1


def test_the_menu_button_keeps_a_44px_tap_target_at_320px():
    """CSS-level, not a browser test: CI has no headless browser in the gate. At 320px the button must be shown,
    44px wide and tall, and not allowed to shrink, so the brand beside it cannot squeeze it."""
    rules = _css_rules_at((ROOT / "static" / "css" / "site.css").read_text(encoding="utf-8"), 320)
    toggle = {}
    for selector, decls in rules:
        if ".nav-toggle" in [s.strip() for s in selector.split(",")]:
            toggle.update(decls)
    assert toggle["display"] == "flex" and toggle["flex-shrink"] == "0"
    assert toggle["width"] == toggle["height"] == "44px" and "min-width" not in toggle and "max-width" not in toggle


def test_home_and_corrections_link_to_history(tmp_path):
    build.build(tmp_path / "site")
    home = (tmp_path / "site" / "index.html").read_text(encoding="utf-8")
    historical = home.split('class="stack arc-col"')[1]
    assert 'href="./history/"><span>The timeline' in historical
    assert home.count('history/"><span>The timeline') == 1
    corrections = (tmp_path / "site" / "corrections" / "index.html").read_text(encoding="utf-8")
    assert ('Entries on the <a href="../history/">History</a> page follow the same rules: each cites its sources in '
            "sources.bib, and a factual error in one gets a row in this ledger.") in corrections
    assert "/history/</loc>" in (tmp_path / "site" / "sitemap.xml").read_text(encoding="utf-8")


def _built_with(tmp_path, root, text):
    """The public build, with its History page re-rendered from fixture data."""
    build.build(tmp_path / "site")
    (tmp_path / "site" / "history" / "index.html").write_text(render(root, text), encoding="utf-8")
    return tmp_path / "site"


def test_a_history_page_with_events_passes_every_check(tmp_path, timeline_root):
    assert check.check(_built_with(tmp_path, timeline_root, SEED)) == []


def test_a_broken_history_anchor_is_caught(tmp_path, timeline_root):
    site = _built_with(tmp_path, timeline_root, EVENT)
    about = site / "about" / "index.html"
    about.write_text(about.read_text(encoding="utf-8").replace("</main>", '<a href="../history/#1843-nope">x</a></main>'), encoding="utf-8")
    assert any("missing anchor" in p for p in check.check(site))


def test_a_private_term_in_an_event_is_caught(tmp_path, timeline_root, monkeypatch):
    monkeypatch.setenv("FORBIDDEN_TERMS", "zzqx-corp")
    site = _built_with(tmp_path, timeline_root, EVENT.replace('"Fixture summary."', '"Funded by ZZQX-Corp."'))
    assert any(p.startswith("history/index.html") and "must never appear" in p for p in check.check(site))


# ------------------------------------------------------------------ 18: the interactive axis (site.js draws it)
# The fixture EVENT as main rendered it before the axis: the axis may only add data-year and data-from/data-to.
GOLDEN_LI = ('<li class="tl" id="1843-hamilton-quaternions" data-era="ether" data-thread="vectors-quaternions" data-class="theory" '
             'data-verified="primary"><article><p class="mono tl__date"><time datetime="1843-10-16">16 October 1843</time></p>'
             '<h3 class="h3 tl__title"><a href="#1843-hamilton-quaternions">Fixture title</a></h3><p class="mono tl__meta">'
             "Fields and ether, 1840\u20131904 &middot; Theory &middot; Vectors and quaternions &middot; Checked against the original</p>"
             '<p class="small tl__summary">Fixture summary.</p><ol class="tl__sources"><li><cite>Fixture entry hamilton1865letter</cite>. '
             "Ann Author and Will Writer. Fixture Journal 1, 1\u20132 (2000). "
             '<a href="https://doi.org/10.0000/fixture.hamilton1865letter" rel="noopener">doi:10.0000/fixture.hamilton1865letter</a> '
             '<span class="mono">Primary</span></li></ol><p class="mono tl__checked">Checked <time datetime="2026-10-03">3 October 2026</time>'
             "</p></article></li>")
GOLDEN_ERA_CHIPS = ('<div class="filter__chips" role="group" aria-label="Filter by era" data-filter="era"><button class="chip" type="button" '
                    'data-value="all" aria-pressed="true">All eras</button><button class="chip" type="button" data-value="ether" '
                    'aria-pressed="false">Fields and ether</button></div>')
AXIS_ATTRS = re.compile(r' data-(?:year|from|to)="[^"]*"')
# Bytes. Raised with the site owner's approval; measured with the back-button figure spacing in: site.js 17,493, gzip -9 6,385; site.css 30,117.
# The gzip ceiling keeps the raw raise's proportion (6,400 x 19,000 / 17,500). Raising one
# is a decision for the PR that needs it, not a test fix.
JS_CEILING, JS_GZIP_CEILING, CSS_CEILING = 19_000, 6_950, 32_000


def test_each_entry_carries_its_sort_key_year(timeline_root):
    events = load(timeline_root, SEED)
    p = parse(render(timeline_root, SEED))
    assert [item["data-year"] for item in p.items] == [str(ev.sort_key[0]) for ev in events]
    html = render(timeline_root, bounded("1850-bounded", 'not_before = "1845"\nnot_after = "1850"'))
    assert parse(html).items[0]["data-year"] == "1845"


def test_era_chips_carry_the_era_bounds_in_chip_order(timeline_root):
    html = render(timeline_root, SEED)
    era_group = re.search(r'data-filter="era">(.*?)</div>', html).group(1)
    bounds = re.findall(r'data-value="([\w-]+)" data-from="(\d+)" data-to="(\d*)"', era_group)
    assert bounds == [(slug, str(first), str(last or "")) for slug, (_, first, last) in content.ERAS.items()]
    assert bounds[-1] == ("precision", "1950", "")
    assert html.count("data-from=") == len(content.ERAS) and 'data-value="all" data-from' not in html


def test_without_javascript_the_markup_is_otherwise_unchanged(timeline_root):
    html = render(timeline_root, EVENT)
    assert 'data-verified="primary" data-year="1843"><article>' in html
    stripped = AXIS_ATTRS.sub("", html)
    assert GOLDEN_LI in stripped and GOLDEN_ERA_CHIPS in stripped
    assert "tl-axis" not in html and "tl--current" not in html  # the axis and the highlight exist only once site.js runs


def test_the_axis_css_only_styles_what_site_js_adds():
    css = re.sub(r"/\*.*?\*/", "", (ROOT / "static" / "css" / "site.css").read_text(encoding="utf-8"), flags=re.S)
    start = css.index(".tl-axis {")
    last = "@media print, (max-width: 560px) {\n  .tl-axis { display: none; }\n}"
    end = css.index(last) + len(last)
    for selector in re.findall(r"([^{}]+)\{", css[start:end]):
        selector = selector.strip()
        assert selector.startswith("@media") or all(any(c in s for c in ("tl-axis", "tl--current", "tl-card", "tl__back"))
                                                    for s in selector.split(",")), selector


def test_site_js_requests_nothing_but_the_video_embed():
    js = (ROOT / "static" / "js" / "site.js").read_text(encoding="utf-8")
    assert re.findall(r"https?://[^\"'`\s]+", js) == ["https://www.youtube-nocookie.com/embed/"]
    assert not re.search(r"[\"'`]//", js)
    assert not any(word in js for word in ("fetch(", "XMLHttpRequest", "import(", "sendBeacon", "WebSocket", "new Image"))


def test_site_js_and_css_stay_within_the_axis_budget():
    """Raw bytes as served: the site has no minify step. Gzip is what the browser transfers."""
    js = (ROOT / "static" / "js" / "site.js").read_bytes()
    css = (ROOT / "static" / "css" / "site.css").read_bytes()
    assert len(css) <= CSS_CEILING
    assert len(js) <= JS_CEILING
    assert len(gzip.compress(js, 9)) <= JS_GZIP_CEILING


# ------------------------------------------------------------------ 19: the preview card (site.js builds it)
ONELINER = "Hamilton found a way to multiply four-part numbers."


def with_oneliner(text, value):
    return text.replace('summary = "Fixture summary."', f'summary = "Fixture summary."\noneliner = {value}')


@pytest.mark.parametrize("value", ['"' + "x" * 139 + '."', f'"{ONELINER}"', '"Why?"', '"  Padded!  "'])
def test_a_oneliner_loads(timeline_root, value):
    [ev] = load(timeline_root, with_oneliner(EVENT, value))
    assert ev.oneliner and len(ev.oneliner) <= 140 and ev.oneliner == ev.oneliner.strip()


def test_an_event_without_a_oneliner_has_none(timeline_root):
    assert load(timeline_root, EVENT)[0].oneliner == ""


@pytest.mark.parametrize("value, message", [
    ('"' + "x" * 140 + '."', "oneliner is longer than 140 characters (141)"),
    ('"Two\\nlines."', "oneliner must be one line of plain text"),
    ('"a <b> tag."', "oneliner must be one line of plain text"),
    ('"a > b."', "oneliner must be one line of plain text"),
    ('""', "oneliner must be one line of plain text"),
    ('"   "', "oneliner must be one line of plain text"),
    ("140", "oneliner must be one line of plain text"),
    ('["A list."]', "oneliner must be one line of plain text"),
    ('"No full stop"', "oneliner must end with . ? or !"),
    ('"Fixture title!"', "oneliner must not repeat the title"),
    ('"Ends [TODO: fix]."', "oneliner has a capitalised bracket placeholder"),
    ('"See [PLACEHOLDER]."', "oneliner has a capitalised bracket placeholder"),
    ('"An AVE result."', "oneliner must spell out the framework's name"),
])
def test_a_bad_oneliner_is_refused_with_its_message(timeline_root, value, message):
    text = with_oneliner(EVENT, value).replace('title = "Fixture title"', 'title = "Fixture title!"')
    with pytest.raises(SystemExit, match=r"event 1843-hamilton-quaternions: " + re.escape(message)):
        load(timeline_root, text)


def test_oneliner_is_exported_after_summary_and_round_trips(tmp_path, timeline_root):
    from tools import export_timeline as ex
    assert ex.EVENT_FIELDS[ex.EVENT_FIELDS.index("summary") + 1] == "oneliner"
    tracker = tmp_path / "tracker"
    tracker.mkdir()
    (tracker / "HISTORY-LINKS.md").write_text("| ID | Name |\n|---|---|\n| HL-001 | fixture |\n", encoding="utf-8")
    record = 'link = "HL-001"\nhistorian = "confirmed"\npublic = true\n' + EVENT.split("\n", 1)[1]
    record = record.replace('summary = "Fixture summary."', f'oneliner = "{ONELINER}"\nsummary = "Fixture summary."')
    (tracker / "HISTORY-CONFIRMED.toml").write_text("[[confirmed]]\n" + record.replace("[[event.source]]", "[[confirmed.source]]"),
                                                     encoding="utf-8")
    out = tmp_path / "timeline.toml"
    assert ex.export(tracker / "HISTORY-CONFIRMED.toml", tracker / "HISTORY-LINKS.md", out, root=timeline_root) == 0
    text = out.read_text(encoding="utf-8")
    assert f'summary = "Fixture summary."\noneliner = "{ONELINER}"\nera = "ether"' in text
    [ev] = load(timeline_root, text)
    assert ev.oneliner == ONELINER


def test_the_export_refuses_a_placeholder_in_a_oneliner(timeline_root):
    from tools import export_timeline as ex
    event = {"id": "1843-x", "title": "T", "summary": "S.", "oneliner": "Ends [TODO].", "checked_by": "Historian", "source": []}
    with pytest.raises(SystemExit, match="capitalised bracket in oneliner"):
        ex.guard([event])


def test_data_oneliner_renders_typographic_escaped_and_only_when_present(timeline_root):
    html = render(timeline_root, with_oneliner(EVENT, '"Kelvin\'s rods & \\"rings\\" turn."'))
    assert '<li class="tl" id="1843-hamilton-quaternions"' in html
    assert 'data-year="1843" data-oneliner="Kelvin\u2019s rods &amp; \u201crings\u201d turn."><article>' in html
    assert parse(html).items[0]["data-oneliner"] == "Kelvin\u2019s rods & \u201crings\u201d turn."
    without = render(timeline_root, EVENT)
    assert "data-oneliner" not in without
    assert AXIS_ATTRS.sub("", without).count(GOLDEN_LI) == 1


def test_the_card_and_the_back_button_exist_only_once_site_js_runs(tmp_path, timeline_root):
    html = render(timeline_root, with_oneliner(EVENT, f'"{ONELINER}"'))
    build.build(tmp_path / "site")
    built = (tmp_path / "site" / "history" / "index.html").read_text(encoding="utf-8")
    for page in (html, built):
        for js_only in ("tl-card", "tl__back", "Read entry", "Back to timeline", "Close preview"):
            assert js_only not in page


def test_a_history_page_with_oneliners_passes_every_check(tmp_path, timeline_root):
    seed = SEED.replace('summary = "Summary 1843-hamilton-quaternions."',
                        f'summary = "Summary 1843-hamilton-quaternions."\noneliner = "{ONELINER}"')
    site = _built_with(tmp_path, timeline_root, seed)
    assert "data-oneliner=" in (site / "history" / "index.html").read_text(encoding="utf-8")
    assert check.check(site) == []


# The card's public strings, approved as written. Arrows are separate aria-hidden spans, so names are the words alone.
CARD_COPY = ("Close", "Close preview", "Read entry ", " Back to timeline", "Source: ")
CARD_ARROWS = ("\\u2193", "\\u2191")


def test_the_card_copy_is_in_site_js_and_follows_the_page_rules(monkeypatch):
    js = (ROOT / "static" / "js" / "site.js").read_text(encoding="utf-8")
    for text in CARD_COPY:
        assert f'"{text}"' in js, text
    for arrow in CARD_ARROWS:
        assert f'"{arrow}"' in js, arrow
    words = " ".join(CARD_COPY)
    assert not check.PLACEHOLDER.search(words) and not check.ACRONYM.search(words)
    assert not any(t in words.lower() for t in check.forbidden_terms())
    assert "lecture" not in js.lower()


def test_site_js_has_no_two_tap_touch_branch():
    js = (ROOT / "static" / "js" / "site.js").read_text(encoding="utf-8")
    assert not re.search(r"\barmed\b", js)
    assert not re.search(r"touch\s*&&\s*ev\.detail|ev\.detail\s*&&", js)
    assert "pointerdown" not in js


def test_site_js_follows_the_card_rules():
    """The card is non-modal, built with textContent, and has no animation of its own."""
    js = (ROOT / "static" / "js" / "site.js").read_text(encoding="utf-8")
    css = (ROOT / "static" / "css" / "site.css").read_text(encoding="utf-8")
    assert "innerHTML" not in js and "dialog" not in js and "popover" not in js and "aria-live" not in js
    card_css = "\n".join(line for line in css.splitlines() if "tl-card" in line or "tl__back" in line)
    assert "transition" not in card_css and "animation" not in card_css
    assert 'role: "group"' in js and '"aria-labelledby", "tl-card-title"' in js
    assert 'setAttribute("aria-controls", card.id)' in js and "ariaExpanded: false" in js
    assert 'fold.setAttribute("aria-controls"' in js


def test_focus_leaving_the_axis_closes_the_card_without_moving_focus():
    """Above 560px the card covers the filters, so focus outside the axis must not leave it open over them."""
    js = (ROOT / "static" / "js" / "site.js").read_text(encoding="utf-8")
    handler = re.search(r'on\(axis, "focusout", \(ev\) => \{(.*?)\}\);\n', js)
    assert handler, "no focusout handler on the axis"
    body = handler.group(1)
    assert "ev.relatedTarget &&" in body and "!axis.contains(ev.relatedTarget)" in body
    assert "close()" in body and "close(true)" not in body and ".focus(" not in body
    assert "box" not in body and "chip" not in body


EINSTEIN_TITLE = 'Einstein\'s \\"On the Electrodynamics of Moving Bodies\\"'
EINSTEIN_CURLY = "Einstein\u2019s \u201cOn the Electrodynamics of Moving Bodies\u201d"


def test_titles_summaries_and_citations_get_typographic_quotes(timeline_root):
    bib_path = timeline_root / "content" / "sources.bib"
    bib_path.write_text(bib_path.read_text(encoding="utf-8").replace(
        "Fixture entry michelson1887ether", "The Ether and the Earth's Atmosphere"), encoding="utf-8")
    einstein = EVENT.replace('"Fixture title"', f'"{EINSTEIN_TITLE}"').replace(
        '"Fixture summary."', '"Albert Einstein\'s paper \\"Zur Elektrodynamik\\"."').replace(
        'era = "ether"', 'era = "ether"\nrelated = ["1887-michelson-morley"]')
    other = event("1887-michelson-morley", "1887-11", "ether", "experiment", ["ether"], "michelson1887ether",
                  extra='related = ["1843-hamilton-quaternions"]')
    html = render(timeline_root, einstein + "\n" + other)
    assert re.search(r'class="h3 tl__title"><a href="#1843-hamilton-quaternions">' + EINSTEIN_CURLY + "</a>", html)
    assert f'See also <a href="#1843-hamilton-quaternions">{EINSTEIN_CURLY}</a>' in html
    assert "Albert Einstein\u2019s paper \u201cZur Elektrodynamik\u201d." in html
    assert "<cite>The Ether and the Earth\u2019s Atmosphere</cite>" in html
    assert "Earth's" not in html and "Einstein's" not in html


@pytest.mark.parametrize("key", ["title", "summary"])
@pytest.mark.parametrize("char", ["*", "_", "`"])
def test_markup_characters_in_titles_and_summaries_are_refused(timeline_root, key, char):
    text = EVENT.replace('"Fixture title"', f'"Fixture {char}title"') if key == "title" else \
        EVENT.replace('"Fixture summary."', f'"Fixture {char}summary."')
    with pytest.raises(SystemExit, match=re.escape(f"{key} must be plain text (no *, _ or `)")):
        load(timeline_root, text)


def test_an_episode_title_with_quotes_renders_curly_everywhere(tmp_path, published_root):
    toml = published_root / "content" / "episodes.toml"
    toml.write_text(toml.read_text(encoding="utf-8").replace('title = "X"', 'title = "It\'s \\"x\\""'), encoding="utf-8")
    build.build(tmp_path / "site", root=published_root)
    curly = "It\u2019s \u201cx\u201d"
    episodes = (tmp_path / "site" / "episodes" / "index.html").read_text(encoding="utf-8")
    home = (tmp_path / "site" / "index.html").read_text(encoding="utf-8")
    page = (tmp_path / "site" / "episodes" / "001-x" / "index.html").read_text(encoding="utf-8")
    assert f'<h2 class="h2 h2--row g16">{curly}</h2>' in episodes
    assert f'<h2 class="h2 g16">{curly}</h2>' in home
    assert f'<h1 class="h1 h1--page g20">{curly}</h1>' in page
    assert f"<title>Episode 001: {curly} | The Electron Plumber</title>" in page
    assert f'<meta property="og:title" content="Episode 001: {curly} | The Electron Plumber">' in page
    for html in (episodes, home, page):
        assert "It's" not in html and "&quot;x&quot;" not in html
    assert check.check(tmp_path / "site") == []
