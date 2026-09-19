import shutil
from pathlib import Path

import pytest

import build
import check
from sitegen import content

ROOT = Path(build.__file__).resolve().parent


def test_public_build_passes_every_check(tmp_path):
    build.build(tmp_path / "site")
    assert check.check(tmp_path / "site") == []


def test_nothing_is_claimed_before_it_exists(tmp_path):
    """With no published episode, the home page must not offer a video to watch."""
    _, episodes = content.load(ROOT)
    build.build(tmp_path / "site")
    home = (tmp_path / "site" / "index.html").read_text(encoding="utf-8")
    if not any(e.status == "published" for e in episodes):
        assert "Watch Episode" not in home and "in production" in home
        assert not list((tmp_path / "site" / "episodes").glob("*/index.html"))


def _copy_content(tmp_path):
    shutil.copytree(ROOT / "content", tmp_path / "content")
    (tmp_path / "content" / "episodes").mkdir(exist_ok=True)  # git does not track an empty folder
    return tmp_path


PUBLISHED = ('[[episode]]\nnumber = 1\nslug = "001-x"\ntitle = "X & <Y>"\narc = "historical"\nstatus = "published"\n'
             'youtube_id = "abcdefghijk"\ndate = "2026-01-01"\nexcerpt = "An excerpt."\n')


def test_published_episode_without_a_handout_is_refused(tmp_path):
    root = _copy_content(tmp_path)
    (root / "content" / "episodes.toml").write_text(PUBLISHED, encoding="utf-8")
    with pytest.raises(SystemExit, match="does not exist"):
        content.load(root)


def test_unpublished_handout_in_the_public_tree_is_refused(tmp_path):
    root = _copy_content(tmp_path)
    (root / "content" / "episodes.toml").write_text(
        '[[episode]]\nnumber = 1\nslug = "001-x"\ntitle = "X"\narc = "historical"\nstatus = "in-production"\n', encoding="utf-8")
    (root / "content" / "episodes" / "001-x.md").write_text("## Learning goals\n\n- a\n", encoding="utf-8")
    with pytest.raises(SystemExit, match="not published"):
        content.load(root)


def test_checker_catches_a_broken_link_and_a_placeholder(tmp_path):
    build.build(tmp_path / "site")
    page = tmp_path / "site" / "about" / "index.html"
    page.write_text(page.read_text(encoding="utf-8").replace("</main>", '<a href="../nope/">x</a><p>[EPISODE NOTES: to come.]</p></main>'), encoding="utf-8")
    problems = " ".join(check.check(tmp_path / "site"))
    assert "broken link" in problems and "placeholder" in problems


@pytest.mark.parametrize("change, message", [
    (("2026-01-01", "2026-13-45"), "real date"),
    (('slug = "001-x"', 'slug = "002-x"'), "must start with 001-"),
    (('number = 1', 'number = "1"'), "must be an integer"),
    (('status = "published"', 'status = "published"\ndraft = true'), "not a content field"),
])
def test_bad_episode_data_is_refused_with_a_message(tmp_path, change, message):
    root = _copy_content(tmp_path)
    (root / "content" / "episodes.toml").write_text(PUBLISHED.replace(*change), encoding="utf-8")
    with pytest.raises(SystemExit, match=message):
        content.load(root)


def test_handout_without_an_episode_is_refused(tmp_path):
    root = _copy_content(tmp_path)
    (root / "content" / "episodes" / "009-orphan.md").write_text("## Learning goals\n\n- a\n", encoding="utf-8")
    with pytest.raises(SystemExit, match="no episode"):
        content.load(root)


def test_toml_text_is_escaped_in_page_bodies():
    from sitegen import pages
    from sitegen.html import Ctx
    site, _ = content.load(ROOT)
    site["_root"] = str(ROOT)
    ep = content.Episode(number=1, slug="001-x", title="X & <Y>", arc="historical", status="published",
                         excerpt="a < b", youtube_id="abcdefghijk", date="2026-01-01", sections=[("Notes", "<p>n</p>")])
    html = pages.episode(Ctx(site, [ep], ep.url, "v"), ep) + pages.home(Ctx(site, [ep], "", "v"))
    assert "X &amp; &lt;Y&gt;" in html and "<Y>" not in html and "a &lt; b" in html


def test_build_refuses_to_delete_a_folder_it_did_not_make(tmp_path):
    precious = tmp_path / "precious"
    precious.mkdir()
    (precious / "keep.txt").write_text("x")
    with pytest.raises(SystemExit, match="refusing"):
        build.build(precious)
    assert (precious / "keep.txt").exists()
    with pytest.raises(SystemExit, match="refusing"):
        build.build(ROOT)


def test_private_terms_are_caught_anywhere_in_the_output(tmp_path, monkeypatch):
    monkeypatch.setenv("FORBIDDEN_TERMS", "zzqx-corp")
    build.build(tmp_path / "site")
    page = tmp_path / "site" / "about" / "index.html"
    page.write_text(page.read_text(encoding="utf-8").replace("<title>", "<title>ZZQX-Corp "), encoding="utf-8")
    assert any("must never appear" in p for p in check.check(tmp_path / "site"))


def test_acronym_is_caught_in_titles_and_attributes(tmp_path):
    build.build(tmp_path / "site")
    page = tmp_path / "site" / "about" / "index.html"
    page.write_text(page.read_text(encoding="utf-8").replace('alt=""', 'alt="the AVE mark"', 1), encoding="utf-8")
    assert any("spelled out" in p for p in check.check(tmp_path / "site"))


def test_images_with_metadata_are_refused(tmp_path):
    build.build(tmp_path / "site")
    (tmp_path / "site" / "img" / "leak.jpg").write_bytes(b"\xff\xd8\xff\xe1\x00\x10Exif\x00\x00rest")
    assert any("metadata" in p for p in check.check(tmp_path / "site"))
