"""Every section has a heading of its own, each page has one h1, and no heading level is skipped."""
from html.parser import HTMLParser

import pytest

import build

VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr"}
PAGES = ("index.html", "episodes/index.html", "history/index.html", "start/index.html", "research/index.html",
         "corrections/index.html", "about/index.html", "404.html")
# The rows whose body has no heading, so their rail label is the section's h2. The text is the label as before.
RAIL_HEADINGS = {
    "index.html": ['<h2 class="kicker">About the author</h2>',
                   '<h2 class="row__h"><span class="badge badge--speculative">Speculative</span></h2>'],
    "research/index.html": ['<h2 class="kicker">The wager</h2>', '<h2 class="kicker">Four axioms</h2>',
                            '<h2 class="kicker">Read it</h2>'],
    "corrections/index.html": ['<h2 class="kicker">Sources and licenses</h2>'],
    "history/index.html": ['<h2 class="kicker">Timeline</h2>'],
}


class Outline(HTMLParser):
    def __init__(self):
        super().__init__()
        self.stack, self.sections, self.levels = [], [], []

    def handle_starttag(self, tag, attrs):
        if tag in VOID:
            return
        if tag == "section":
            self.sections.append({"heading": False})
        if tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
            self.levels.append(int(tag[1]))
            if tag in ("h2", "h3"):
                for open_tag, section in reversed(self.stack):
                    if open_tag == "article":
                        break  # an article's heading titles the article, not the section around it
                    if open_tag == "section":
                        section["heading"] = True
                        break
        self.stack.append((tag, self.sections[-1] if tag == "section" else None))

    def handle_endtag(self, tag):
        if tag in VOID:
            return
        while self.stack and self.stack.pop()[0] != tag:
            pass


@pytest.fixture(scope="module")
def site(tmp_path_factory):
    out = tmp_path_factory.mktemp("headings") / "site"
    build.build(out)
    return out


def outline(path):
    o = Outline()
    o.feed(path.read_text(encoding="utf-8"))
    return o


@pytest.mark.parametrize("page", PAGES)
def test_every_section_has_a_heading_of_its_own(site, page):
    o = outline(site / page)
    assert all(s["heading"] for s in o.sections), page


@pytest.mark.parametrize("page", PAGES)
def test_one_h1_and_no_skipped_level(site, page):
    levels = outline(site / page).levels
    assert levels.count(1) == 1 and levels[0] == 1, page
    for before, level in zip(levels, levels[1:], strict=False):
        assert level <= before + 1, f"{page}: h{before} then h{level}"


@pytest.mark.parametrize("page", RAIL_HEADINGS)
def test_rail_labels_that_became_headings_keep_their_text(site, page):
    html = (site / page).read_text(encoding="utf-8")
    for heading in RAIL_HEADINGS[page]:
        assert html.count(heading) == 1, (page, heading)


def test_a_published_episode_page_keeps_its_outline(tmp_path, published_root):
    build.build(tmp_path / "site", root=published_root)
    o = outline(tmp_path / "site" / "episodes" / "001-x" / "index.html")
    assert o.sections and all(s["heading"] for s in o.sections)
    assert o.levels.count(1) == 1
    assert all(b + 1 >= a for b, a in zip(o.levels, o.levels[1:], strict=False))
