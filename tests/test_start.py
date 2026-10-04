import re
import subprocess
import sys
from pathlib import Path

import pytest

import build
import check
from sitegen import content, pages
from sitegen.html import NAV, Ctx

ROOT = Path(build.__file__).resolve().parent
SUFFIX = " | The Electron Plumber"


def _ep1(**kw):
    fields = dict(number=1, slug="001-x", title="What is an Electron?", arc="historical", status="published",
                  excerpt="An excerpt.", youtube_id="abcdefghijk", date="2026-01-01", sections=[("Notes", "<p>n</p>")])
    return content.Episode(**{**fields, **kw})


def _render(episodes, root=ROOT):
    site, _ = content.load(ROOT)
    site["_root"] = str(ROOT)
    return pages.start(Ctx(site, episodes, "start/", "v", start=content.load_start(root, episodes)))


def _steps(html):
    ol = re.search(r'<ol class="start-steps">(.*?)</ol>', html, re.S).group(1)
    return re.findall(r'<li class="trow">(.*?)</li>', ol, re.S)


def _write_start(root, text):
    (root / "content" / "start.toml").write_text(text, encoding="utf-8")


# ------------------------------------------------------------------ the built page
def test_the_build_writes_start_and_passes_the_gate(tmp_path):
    _, episodes = content.load(ROOT)
    build.build(tmp_path / "site")
    assert (tmp_path / "site" / "start" / "index.html").is_file()
    assert check.check(tmp_path / "site") == []
    # Each published episode adds its page and its /NNN short link.
    assert len(list((tmp_path / "site").rglob("*.html"))) == 13 + 2 * sum(e.live for e in episodes)


def test_one_h1_and_three_steps_in_file_order(tmp_path):
    _, episodes = content.load(ROOT)
    ep1 = next(e for e in episodes if e.number == 1)
    build.build(tmp_path / "site")
    html = (tmp_path / "site" / "start" / "index.html").read_text(encoding="utf-8")
    assert re.findall(r"<h1[^>]*>(.*?)</h1>", html) == ["Start here"]
    steps = _steps(html)
    assert len(steps) == 3
    assert (f'href="../episodes/{ep1.slug}/"' if ep1.live else "Episode 001") in steps[0]
    assert 'href="../history/"' in steps[1] and 'href="../episodes/"' in steps[2]
    assert all('<div class="trow__n" aria-hidden="true">' in s for s in steps)


def test_before_anything_is_published_step_one_is_the_question_and_deck():
    _, episodes = content.load(ROOT)
    if any(e.live for e in episodes):
        pytest.skip("an episode is published; the published state is tested with a fixture")
    first, _, third = _steps(_render(episodes))
    assert re.search(r'<h2 class="h3">(.*?)</h2>', first).group(1) == "What is an Electron?"
    assert pages.DECK in first and "Episode 001 is in production" in first and "episodes/001" not in first
    assert '<hr class="rule rule--line g40">' in third and "Next &middot; Episode 001" in third


def test_once_published_step_one_links_the_episode_and_step_three_offers_it():
    first, _, third = _steps(_render([_ep1()]))
    assert '<a href="../episodes/001-x/">What is an Electron?</a>' in first
    assert "An excerpt." in first and "badge--historical" in first and "in production" not in first
    assert pages.DECK not in first
    assert "<span>Watch Episode 001</span>" in third and 'href="../episodes/001-x/"' in third


def test_route_steps_use_the_target_pages_own_title_and_description(tmp_path):
    build.build(tmp_path / "site")
    html = (tmp_path / "site" / "start" / "index.html").read_text(encoding="utf-8")
    routes = 0
    for step in _steps(html):
        m = re.search(r'<h2 class="h3"><a href="\.\./([a-z]+/)">(.*?)</a></h2>', step)
        if not m:
            continue
        routes += 1
        target = (tmp_path / "site" / m.group(1) / "index.html").read_text(encoding="utf-8")
        assert m.group(2) + SUFFIX == re.search(r"<title>(.*?)</title>", target).group(1)
        text = re.search(r'<p class="small g12">(.*?)</p>', step).group(1)
        assert text == re.search(r'<meta name="description" content="(.*?)">', target).group(1)
    assert routes == 2


def _merge_base():
    try:
        return subprocess.run(["git", "merge-base", "HEAD", "origin/main"], cwd=ROOT, capture_output=True,
                              text=True, check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return ""


def test_the_page_text_refactor_leaves_the_other_pages_byte_identical(tmp_path):
    """Against a build of the merge base with main. Skipped where main is not fetched (a shallow CI checkout)."""
    base = _merge_base()
    if not base:
        pytest.skip("origin/main is not available to compare against")
    src = tmp_path / "main"
    src.mkdir()
    archive = subprocess.run(["git", "archive", base], cwd=ROOT, capture_output=True, check=True).stdout
    subprocess.run(["tar", "-x", "-C", str(src)], input=archive, check=True)
    if (src / "content" / "start.toml").is_file():
        pytest.skip("the merge base already has the Start here page")
    subprocess.run([sys.executable, "build.py", "--out", "_site"], cwd=src, check=True, capture_output=True)
    build.build(tmp_path / "site")

    def read(root, path):
        return re.sub(r"\?v=[0-9a-f]{10}", "?v=", (root / path).read_text(encoding="utf-8"))

    for path in ("episodes/index.html", "history/index.html", "research/index.html", "corrections/index.html", "404.html"):
        assert read(src / "_site", path) == read(tmp_path / "site", path), path
    for path, prefix in (("index.html", "./"), ("about/index.html", "../")):
        arrow = re.search(rf'<div class="g2[04]"><a class="arrow " href="{re.escape(prefix)}start/">.*?</a></div>',
                          read(tmp_path / "site", path)).group(0)
        assert read(tmp_path / "site", path).replace(arrow, "", 1) == read(src / "_site", path), path


# ------------------------------------------------------------------ the validator
@pytest.mark.parametrize("text, message", [
    (None, "does not exist"),
    ("", "no \\[\\[step\\]\\] entries"),
    ("".join(f'[[step]]\ntarget = "{t}"\n' for t in ("episode:1", "episodes/", "history/", "research/", "corrections/", "about/")),
     "at most 5"),
    ('[[step]]\ntarget = "history/"\ntitle = "History"\n', "unknown key 'title'"),
    ("[[step]]\ntarget = 1\n", "must be a string"),
    ('[[step]]\ntarget = "history/"\n[[step]]\ntarget = "history/"\n', "duplicate"),
    ('[[step]]\ntarget = "episode:9"\n', "no episode 9"),
    ('[[step]]\ntarget = "start/"\n', "must be episode:N"),
    ('[[step]]\ntarget = ""\n', "must be episode:N"),
    ('[[step]]\ntarget = "https://x"\n', "must be episode:N"),
    ('[[step]]\ntarget = "nowhere/"\n', "must be episode:N"),
])
def test_bad_start_data_is_refused_with_a_message(content_root, text, message):
    if text is None:
        (content_root / "content" / "start.toml").unlink()
    else:
        _write_start(content_root, text)
    _, episodes = content.load(content_root)
    with pytest.raises(content.ContentError, match=message):
        content.load_start(content_root, episodes)


def test_a_bad_anchor_passes_the_loader_but_not_the_gate(tmp_path, content_root):
    _write_start(content_root, '[[step]]\ntarget = "history/#1843-nope"\n')
    _, episodes = content.load(ROOT)
    steps = content.load_start(content_root, episodes)
    assert steps[0].route == "history/" and steps[0].anchor == "1843-nope"
    build.build(tmp_path / "site")
    (tmp_path / "site" / "start" / "index.html").write_text(_render(episodes, content_root), encoding="utf-8")
    assert any("missing anchor" in p for p in check.check(tmp_path / "site"))


# ------------------------------------------------------------------ shell, arcs, escaping, the private list
def test_start_is_not_in_the_nav(tmp_path):
    assert NAV == [("Episodes", "episodes/"), ("History", "history/"), ("Research", "research/"),
                   ("Corrections", "corrections/"), ("About", "about/")]
    build.build(tmp_path / "site")
    html = (tmp_path / "site" / "start" / "index.html").read_text(encoding="utf-8")
    assert 'aria-current="page"' not in html


def test_the_page_has_no_page_arc():
    assert "\n<body>\n" in _render([_ep1()])


def test_episode_text_is_escaped():
    html = _render([_ep1(title="X & <Y>", excerpt="a < b")])
    assert "X &amp; &lt;Y&gt;" in html and "<Y>" not in html and "a &lt; b" in html


def test_private_terms_are_caught_on_the_start_page(tmp_path, monkeypatch):
    monkeypatch.setenv("FORBIDDEN_TERMS", "zzqx-corp")
    build.build(tmp_path / "site")
    page = tmp_path / "site" / "start" / "index.html"
    _, episodes = content.load(ROOT)
    page.write_text(_render([_ep1(excerpt="Made at ZZQX-Corp.")] + [e for e in episodes if e.number != 1]),
                    encoding="utf-8")
    assert any("must never appear" in p and "start/index.html" in p for p in check.check(tmp_path / "site"))


def test_home_and_about_each_link_start_once(tmp_path):
    build.build(tmp_path / "site")
    for path, prefix in (("index.html", "./"), ("about/index.html", "../")):
        html = (tmp_path / "site" / path).read_text(encoding="utf-8")
        links = re.findall(r'<a [^>]*href="([^"]*start/)"[^>]*>(.*?)</a>', html)
        assert links == [(prefix + "start/", "<span>Start here</span>" + re.search(r"<svg.*?</svg>", links[0][1]).group(0))]
    home = (tmp_path / "site" / "index.html").read_text(encoding="utf-8")
    assert re.search(r'<p class="deck g24">.*?</p><div class="g20"><a class="arrow " href="\./start/">', home)


def test_home_keeps_the_link_under_the_deck_once_an_episode_is_published():
    site, _ = content.load(ROOT)
    site["_root"] = str(ROOT)
    home = pages.home(Ctx(site, [_ep1()], "", "v"))
    assert re.search(r'<p class="deck g24">.*?</p><div class="g20"><a class="arrow " href="\./start/">', home)
    assert home.count('href="./start/"') == 1
