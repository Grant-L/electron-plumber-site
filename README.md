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
| `content/episodes/*.md` | Episode notes for **published** episodes: the same file that is published in the [notes repo](https://github.com/Grant-L/electron-plumber-notes). |
| `content/timeline.toml` | The History page's events, one `[[event]]` each. **Generated** by `tools/export_timeline.py` from the Historian's confirmed, public entries; never edited by hand. A missing file means an empty timeline. |
| `content/sources.bib` | A verbatim copy of the notes repo's `sources.bib`, with one header line naming the notes commit it was copied from. Every timeline and episode source key must be in it. |
| `content/errata.md` | A verbatim copy of the notes repo's `ERRATA.md`, with one header comment naming the notes commit it was copied from: the same commit as `content/sources.bib`. Its entries become the corrections-ledger rows on each episode page. |
| `sitegen/` | Templates (`pages.py`), shared components (`html.py`), content loading and rules (`content.py`), a small Markdown subset (`md.py`), a small BibTeX subset (`bib.py`). |
| `tools/` | `export_timeline.py`: the public-safe export from the Historian's confirmations into `content/timeline.toml` (`--check` exits 1 if the file would change). |
| `static/` | CSS, the one script, images, favicons. Copied to the site root as is. |
| `build.py`, `check.py` | Build into `_site/`; gate the result. |
| `design/` | The mark as SVG and PNG, and the script that draws it from its geometry. |

`_site/` is build output and is never committed. `_private/` is ignored by git: planning notes and unpublished handouts live there and never ship.

## Publishing an episode

1. In `content/episodes.toml`, set `status = "published"` and fill in `youtube_id`, `date`, `runtime`, `excerpt` and `orientation`, and add one `[[episode.source]]` per source the episode cites (a historical episode needs at least one).
2. Copy the published handout to `content/episodes/<slug>.md`. Re-copy `sources.bib` and `ERRATA.md` to `content/sources.bib` and `content/errata.md`, both from the same notes commit, with their header lines naming it.
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
- Every History event has a frozen, year-prefixed id, a real date that is not in the future (or open-ended bounds instead), an era whose years contain it, a class and one to three threads from fixed lists, at least one source whose key is in `content/sources.bib`, and a verification record (`verified`, `checked_by`, `checked_date`). An event marked `verified = "primary"` cites at least one primary source. Events are in date order. Claims and episode links appear only once the episode is published.
- An episode's `[[episode.source]]` tables follow the same rules as an event's, and go only with a published episode. A published historical episode needs at least one.
- `content/errata.md` must start with `<!-- Copied from Grant-L/electron-plumber-notes ERRATA.md at commit <40-character SHA>. Do not edit here. -->`, naming the same commit as `content/sources.bib`. Each entry is a `## cor-NNN — Episode NNN (epNNN-cNN) — CORRECTED | RETRACTED | CLARIFIED` heading whose episode matches the claim, followed by exactly five bullets in order (Date, As aired, Correction, How it happened, Corrected via). Ids are unique; dates are real, not in the future, and newest first; no field is empty or `?`; the text has no links; the episode is published; `Corrected via` is `description`, `pinned-comment`, `erratum-short` or `segment epNNN` naming a known episode. With no entries the file must say `*No corrections to date.*`.
- An episode page lists the claims an event or a correction names, each at its own `#epNNN-cNN` anchor, the History events that name the episode, and its corrections at `#cor-NNN`; each History claim links back to its anchor. When an episode has corrections, the ledger rows replace its notes' own Corrections text. No page has two elements with the same id.
- `content/sources.bib` must start with `% Copied from Grant-L/electron-plumber-notes sources.bib at commit <40-character SHA>.`, and an unknown TeX macro or a malformed entry is an error. The build reads the bib when `content/timeline.toml` has events, an episode has sources, or `content/errata.md` exists, and then refuses a bad one. The tests (`tests/test_bib.py`) check the committed copy on every run, events or not.
- The timeline export copies only allowlisted fields from entries the Historian marked confirmed and public. It refuses to read any `_private` path, refuses output carrying tracker-internal ids or the framework's acronym, runs the forbidden-term check before it writes, and gives byte-identical output for the same input.

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
