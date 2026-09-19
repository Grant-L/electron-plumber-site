# electron-plumber-site

Source of **[electron-plumber.com](https://electron-plumber.com)**, the home of [The Electron Plumber](https://www.youtube.com/@TheElectronPlumber).

A small static site: Python builds plain HTML from the templates in `sitegen/` and the data in `content/`. No dependencies beyond Python 3.11. A push to `main` builds, checks and deploys it to GitHub Pages (one-time setup: [Hosting](#hosting)).

```bash
make serve      # build, then http://localhost:4173
make check      # build, then gate: links, anchors, titles, placeholders, standing rules
make test       # unit tests (pytest)
```

## Layout

| Path | What it is |
|---|---|
| `content/site.toml` | Site-wide settings: links, tagline, contact address, newsletter endpoint. |
| `content/episodes.toml` | One entry per announced episode. Status drives everything the site says about it. |
| `content/episodes/*.md` | Handouts for **published** episodes: the same file as `lectures/epNNN.md` in the [notes repo](https://github.com/Grant-L/electron-plumber-notes). |
| `sitegen/` | Templates (`pages.py`), shared components (`html.py`), content loading and rules (`content.py`), a small Markdown subset (`md.py`). |
| `static/` | CSS, the one script, images, favicons. Copied to the site root as is. |
| `build.py`, `check.py` | Build into `_site/`; gate the result. |
| `design/` | The mark as SVG and PNG, and the script that draws it from its geometry. |

`_site/` is build output and is never committed. `_private/` is ignored by git: planning notes and unpublished handouts live there and never ship.

## Publishing an episode

1. In `content/episodes.toml`, set `status = "published"` and fill in `youtube_id`, `date`, `runtime`, `excerpt` and `orientation`.
2. Copy the published handout to `content/episodes/<slug>.md`.
3. Add the next episode as `status = "in-production"` if its title may be public.
4. Open a pull request. CI builds and checks it; merging deploys it.

The home page, the episode list and the short link (`/001`) follow from that data. Until an episode is published the site says "in production" and offers nothing to watch.

## Rules the build enforces

- A published episode without a handout is refused. So is a handout for an episode that is not published.
- Every page has a title, a description and exactly one `h1`. Every internal link and anchor resolves. No `[PLACEHOLDER]` text ships.
- The framework's name is spelled out on the site, in page text, titles and attributes alike.
- Images carry no embedded metadata. TOML text is escaped wherever it lands in a page.
- The owner's private list of terms that must never ship is checked against every built file and every tracked file. The list is not in this repo: it comes from `_private/forbidden.txt` locally and from the `FORBIDDEN_TERMS` repository secret in CI. Without it (a fork, for example) that one rule is skipped with a warning.
- Unsupported Markdown (tables, nested lists) is a build error, not a silent mis-render.

## Working on the site

Branch, change, `make check`, pull request. `main` is what is live. To preview an unpublished handout locally, put it in `_private/drafts/<slug>.md` and run `make serve-drafts`; that build is never deployed.

Colors follow the channel's animation theme (Okabe-Ito accents on a dark ground). The mark is a Smith chart holding the flat (2,3) trefoil; `make mark` redraws every cut.

## Hosting

GitHub Pages, deployed by `.github/workflows/pages.yml`. The domain is registered elsewhere and only its DNS points here. One-time setup, in this order:

1. Verify the domain for the GitHub account (account Settings > Pages > Add a domain) and keep the `_github-pages-challenge-...` TXT record forever. It is what stops someone else from claiming the domain if Pages is ever switched off.
2. Set the Pages source to GitHub Actions: `gh api -X POST repos/OWNER/REPO/pages -f build_type=workflow`. Until then the deploy job fails with a 404.
3. Set the custom domain on the repo (`gh api -X PUT repos/OWNER/REPO/pages -f cname=electron-plumber.com`) **before** touching DNS.
4. At the DNS host, remove any default website records for `@` and `www`, then add A records for `@` to `185.199.108.153`, `185.199.109.153`, `185.199.110.153`, `185.199.111.153`, the matching AAAA records `2606:50c0:8000::153` to `2606:50c0:8003::153`, and a CNAME for `www` to `OWNER.github.io`. Leave mail records alone.
5. When the certificate is issued (up to an hour after DNS is right), enforce HTTPS: `gh api -X PUT repos/OWNER/REPO/pages -F https_enforced=true`.

The `CNAME` file in the build output is ignored by Actions-based deploys; step 3 is what binds the domain.

## Licenses

Code is MIT. The writing is CC BY-NC-ND 4.0, as in the notes repo. The name, the mark and the other brand files are all rights reserved. Details and the exact paths: [LICENSING.md](LICENSING.md).
