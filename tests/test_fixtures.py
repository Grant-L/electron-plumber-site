"""The shared fixtures stand on their own episode data, so publishing a real episode breaks none of them."""
import shutil

from conftest import ROOT, make_content_root, make_published_root, make_timeline_root

import build
import check
from sitegen import content

REAL_SLUG = "001-what-is-an-electron"


def publish_episode_one(repo):
    """A copy of content/ in repo, with Episode 001 published the way the publish step does it: status, video,
    date and excerpt in episodes.toml, and its notes in content/episodes/."""
    shutil.copytree(ROOT / "content", repo / "content")
    (repo / "content" / "episodes").mkdir(exist_ok=True)
    (repo / "content" / "episodes.toml").write_text(
        f'[[episode]]\nnumber = 1\nslug = "{REAL_SLUG}"\ntitle = "What is an Electron?"\narc = "practical"\n'
        'status = "published"\nyoutube_id = "abcdefghijk"\ndate = "2026-01-01"\nexcerpt = "An excerpt."\n',
        encoding="utf-8")
    (repo / "content" / "episodes" / f"{REAL_SLUG}.md").write_text("## Notes\n\nSimulated notes.\n", encoding="utf-8")
    _, episodes = content.load(repo)
    assert [e.slug for e in episodes if e.live] == [REAL_SLUG]
    return repo


def test_content_root_ignores_the_real_episode_state(tmp_path):
    repo = publish_episode_one(tmp_path / "repo")
    root = make_content_root(tmp_path / "fixture", src=repo)
    assert not list((root / "content" / "episodes").iterdir())
    _, episodes = content.load(root)
    assert [(e.slug, e.status) for e in episodes] == [("001-x", "in-production")]


def test_the_published_fixture_still_builds_once_a_real_episode_is_published(tmp_path):
    repo = publish_episode_one(tmp_path / "repo")
    root = make_published_root(make_timeline_root(make_content_root(tmp_path / "fixture", src=repo)))
    site = tmp_path / "site"
    build.build(site, root=root)
    assert check.check(site) == []
    assert sorted(p.parent.name for p in (site / "episodes").glob("*/index.html")) == ["001-x"]
