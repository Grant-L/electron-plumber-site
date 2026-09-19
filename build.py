#!/usr/bin/env python3
"""Build electron-plumber.com into _site/. Standard library only.

    python3 build.py            the public site
    python3 build.py --drafts   also render unpublished handouts from _private/drafts/ (never deploy this)
"""
import argparse
import hashlib
import shutil
from pathlib import Path
from urllib.parse import urlparse

from sitegen import content, pages
from sitegen.html import RECORDS, Ctx

ROOT = Path(__file__).resolve().parent


def build(out: Path, drafts: bool = False):
    out = out.resolve()
    if out == ROOT or out in ROOT.parents:
        raise SystemExit(f"refusing to build into {out}: it contains the source tree")
    if out.exists() and any(out.iterdir()) and not (out / ".nojekyll").is_file():
        raise SystemExit(f"refusing to delete {out}: it is not a previous build (no .nojekyll marker)")

    site, episodes = content.load(ROOT, drafts=drafts)
    site["_root"] = str(ROOT)

    if out.exists():
        shutil.rmtree(out)
    shutil.copytree(ROOT / "static", out)
    version = hashlib.sha256(b"".join((ROOT / "static" / p).read_bytes() for p in ("css/site.css", "js/site.js"))).hexdigest()[:10]

    written = []

    def write(path, text, listed=True):
        target = out / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
        if listed:
            written.append(path)

    def ctx(path, **kw):
        return Ctx(site, episodes, path, version, **kw)

    write("index.html", pages.home(ctx("")))
    write("episodes/index.html", pages.episodes(ctx("episodes/")))
    write("research/index.html", pages.research(ctx("research/")))
    write(f"{RECORDS[1]}index.html", pages.records(ctx(RECORDS[1])))
    write("about/index.html", pages.about(ctx("about/")))
    write("404.html", pages.not_found(ctx("404.html", absolute=True)), listed=False)

    redirects = {
        "notes": site["notes_repo"],
        "errata": site["notes_repo"] + "#corrections",  # switch to /blob/main/ERRATA.md once the notes repo has that file
        "code": site["core_repo"],
        "letter": site["core_repo"] + "/blob/main/papers/2026_birefringence_letter/sve_vacuum_birefringence_letter.pdf",
        "yt": site["youtube"],
    }
    for ep in episodes:
        if ep.live:
            write(f"{ep.url}index.html", pages.episode(ctx(ep.url), ep), listed=not ep.draft)
            redirects[f"{ep.number:03d}"] = f"../{ep.url}"  # relative, so it also works from a project path
    base = site["url"].rstrip("/")
    for short, target in redirects.items():
        canonical = f"{base}/{target.removeprefix('../')}" if target.startswith("../") else target
        write(f"{short}/index.html", pages.redirect(target, canonical), listed=False)

    urls = "".join(f"<url><loc>{base}/{p.removesuffix('index.html')}</loc></url>" for p in written)
    write("sitemap.xml", f'<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{urls}</urlset>\n', listed=False)
    write("robots.txt", f"User-agent: *\nAllow: /\nSitemap: {base}/sitemap.xml\n", listed=False)
    # GitHub ignores CNAME for Actions-based deploys (the domain is set in the repo's Pages settings); it is kept
    # so a branch-based deploy or another static host would still pick the domain up.
    write("CNAME", urlparse(site["url"]).hostname + "\n", listed=False)
    write(".nojekyll", "", listed=False)
    return written


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--drafts", action="store_true", help="render unpublished handouts from _private/drafts/")
    parser.add_argument("--out", default="_site", help="output folder (default: _site)")
    args = parser.parse_args()
    pages_written = build(ROOT / args.out, drafts=args.drafts)
    print(f"built {len(pages_written)} pages into {args.out}/" + ("  [DRAFTS INCLUDED: do not deploy]" if args.drafts else ""))
