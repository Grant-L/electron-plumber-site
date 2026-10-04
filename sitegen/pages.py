"""Page templates. Home and Episodes are driven by episode status, so nothing here claims a video exists before it does."""
from pathlib import Path

from . import content, md
from .html import RECORDS, Ctx, arrow, badge, btn, card, esc, kicker, mono, page, row, subscribe

DECK = "We know what it <em>does</em> to a part in a trillion. Nobody knows what it <em>is</em>."
QUOTE_AUTHOR = ("&ldquo;I&rsquo;m an EE who calls myself an electron plumber. The channel is one question, pursued honestly: "
                "What is an Electron?&rdquo;")
RESEARCH_HANDOFF = ("I work on a model of the vacuum. It&rsquo;s unproven. The Research page says what would kill it, "
                    "and which of its laws already lost.")
ABOUT = ("I&rsquo;m a staff electrical engineer in grid-scale energy storage. My job is finding out why real circuits "
         "fail &mdash; megawatts on the line, root cause or nothing, no partial credit. This channel points that same "
         "discipline at a question nobody can answer: What is an Electron? We know what it <em>does</em> to a part in a "
         "trillion. Nobody knows what it <em>is</em>. I make three kinds of video &mdash; history, told faithfully from "
         "the original papers; speculation, labeled as speculation; and shop practice. You&rsquo;ll always know which one "
         "you&rsquo;re watching. And when I get something wrong, it goes on a public corrections ledger.")


# Raster masters in static/img/ and the copies tools/make_assets.py makes of them.
HERO = "img/field-bed"
PORTRAIT = "img/portrait"
PORTRAIT_WIDTHS = (200, 400, 640, 768)


def hero_preload(ctx):
    return f'<link rel="preload" as="image" href="{ctx.to(HERO + ".avif")}" type="image/avif" fetchpriority="high">\n'


def _portrait(ctx, mod="", sizes="200px", lazy=True):
    """The portrait is optional: drop static/img/portrait.jpg in, run tools/make_assets.py, and it appears.
    Lazy only where it starts below the fold; above it, it is the page's largest paint."""
    if not (Path(ctx.site["_root"]) / "static" / f"{PORTRAIT}.jpg").is_file():
        return ""
    sources = "".join(
        f'<source type="image/{ext}" sizes="{sizes}" srcset="'
        + ", ".join(f'{ctx.to(f"{PORTRAIT}-{w}.{ext}")} {w}w' for w in PORTRAIT_WIDTHS) + '">'
        for ext in ("avif", "webp"))
    loading = ' loading="lazy"' if lazy else ' fetchpriority="high"'
    return (f'<picture>{sources}<img class="portrait {mod}" src="{ctx.to(PORTRAIT + ".jpg")}" alt="{esc(ctx.site["author"])}" '
            f'width="400" height="500"{loading} decoding="async"></picture>')


def _badge(ep):
    """An episode with no arc yet (not aired) shows no badge."""
    return badge(ep.arc) if ep.arc else ""


def _next_line(ctx, ep):
    return (f'<hr class="rule rule--line g40"><div class="between g28"><div class="stack">'
            f'{kicker("Next &middot; " + ep.serial, "kicker--orange")}<div class="next__title g8">{md.plain(ep.title)}</div>'
            f'<div class="mono g8">In production</div></div>{_badge(ep)}</div>')


# ------------------------------------------------------------------ HOME
def home(ctx: Ctx):
    s, latest, upcoming = ctx.site, (ctx.published or [None])[0], ctx.upcoming
    if latest:
        actions = (btn(f"Watch {latest.serial}", ctx.to(latest.url))
                   + arrow("Episode notes", ctx.to(latest.url) + "#learning-goals"))
        status = ""
    else:
        actions = btn("Subscribe on YouTube", ctx.sub_url, external=True) + arrow("The notes repo", s["notes_repo"], external=True)
        status = f'<div class="g28">{kicker(upcoming.serial + " is in production", "kicker--orange")}</div>' if upcoming else ""

    banner = (f"background-image: url({ctx.to(HERO + '.png')}); background-image: image-set(url({ctx.to(HERO + '.avif')}) "
              f"type('image/avif'), url({ctx.to(HERO + '.webp')}) type('image/webp'), url({ctx.to(HERO + '.png')}) type('image/png'));")
    hero = (f'<div class="band" style="{banner}">'
            f'<img src="{ctx.to("img/mark-banner-halo.svg")}" width="236" height="236" '
            f'alt="Channel logo: a Smith chart with a three-lobed closed curve inside it"></div>'
            f'<div class="plate-block">{kicker("The Electron Plumber")}<hr class="rule rule--plate g20">'
            f'<h1 class="h1 h1--hero g36">What is an Electron?</h1><p class="deck g24">{DECK}</p>'
            f'<div class="g20">{arrow(START_TITLE, ctx.to("start/"))}</div>'
            f'<div class="mono mono--sky g28">{esc(s["tagline"])}</div>{status}'
            f'<div class="cluster cluster--stack g40">{actions}</div></div>')

    def arc_col(arc, status_text, text, link=""):
        color = {"historical": "var(--sky)", "speculative": "var(--orange)", "practical": "var(--green)"}[arc]
        return (f'<div class="stack arc-col" style="--arc-c: {color};"><hr class="rule"><div class="g24">{badge(arc)}</div>'
                f'<div class="mono g20">{status_text}</div><p class="small g12">{text}</p>'
                + (f'<div class="g12">{link}</div>' if link else "") + '</div>')

    orient = row("The labels", (
        '<h2 class="h2">Three kinds of video. You&rsquo;ll always know which one you&rsquo;re watching.</h2>'
        '<div class="grid grid--3 g48">'
        + arc_col("historical", "Historical record", "History, told faithfully from the original papers. "
                  "All on-camera citations live in sources.bib.", link=arrow("The timeline", ctx.to("history/")))
        + arc_col("speculative", "Explicit speculation", "Proposed physics, not established physics. The current program and its "
                  "kill criteria are on the Research page.")
        + arc_col("practical", "Shop practice", "Bench work. Failure analysis on circuits rebuilt for the camera, "
                  "taken down to the physical mechanism.")
        + '</div><p class="small muted g40">Every episode is labeled.</p>'))

    if latest:
        meta = f'{kicker(latest.serial, "kicker--white")}{badge(latest.arc)}{mono(esc(latest.date) or "[DATE]")}'
        body = (f'<div class="latest"><div class="latest__card">{card(ctx, latest.serial, latest.title, youtube_id=latest.youtube_id)}</div>'
                f'<div class="stack"><div class="cluster cluster--tight">{meta}</div><h2 class="h2 g16">{md.plain(latest.title)}</h2>'
                f'<p class="small g16">{esc(latest.excerpt)}</p><div class="cluster g28">{btn("Watch", ctx.to(latest.url))}'
                f'{arrow("Episode notes", ctx.to(latest.url) + "#learning-goals")}</div></div></div>'
                + (_next_line(ctx, upcoming) if upcoming else ""))
        episode_row = row("Latest episode", body)
    elif upcoming:
        body = (f'<div class="latest"><div class="latest__card">{card(ctx, upcoming.serial, upcoming.title, dim=True, nxt=True)}</div>'
                f'<div class="stack"><div class="cluster cluster--tight">{kicker("Next &middot; " + upcoming.serial, "kicker--orange")}'
                f'{_badge(upcoming)}</div><h2 class="h2 g16" style="color: var(--orange);">{md.plain(upcoming.title)}</h2>'
                f'<div class="mono g16">In production</div>'
                f'<div class="g28">{arrow("Subscribe on YouTube", ctx.sub_url, external=True)}</div></div></div>')
        episode_row = row("Next episode", body)
    else:
        episode_row = ""

    author_row = row("About the author", (
        f'<div class="author">{_portrait(ctx)}<div class="stack"><div class="quote">{QUOTE_AUTHOR}</div>'
        f'<div class="name g28">{esc(s["author"])}</div>'
        f'<div class="mono">Staff electrical engineer, grid-scale energy storage. Views my own.</div>'
        f'<div class="g12">{arrow("About", ctx.to("about/"))}</div></div></div>'), heading=True)

    def record(label, text):
        return f'<div class="stack">{kicker(label, "kicker--sm")}<p class="small g12">{text}</p></div>'

    records_row = row(RECORDS[0], (
        '<h2 class="h2">Spotted an error? Open an issue.</h2><div class="grid grid--3 g40">'
        + record("Sources", "Every citation made on camera lives in one public BibTeX file.")
        + record("Corrections", "When I get something wrong it goes on a public ledger. Standing corrections for all episodes are tracked in ERRATA.md.")
        + record("Notes", "Learning goals, episode notes, readings, and standing corrections for each episode.")
        + f'</div><div class="g36">{arrow("See the " + RECORDS[0].lower(), ctx.to(RECORDS[1]))}</div>'))

    disclosure = row("", (f'<div class="quote quote--lg">{RESEARCH_HANDOFF}</div>'
                          f'<div class="g28">{arrow("The speculative program", ctx.to("research/"), "arrow--orange")}</div>'),
                     "row--tighter", rail=badge("speculative"), heading=True)

    return page(ctx, title=s["title"], active=None, preload=hero_preload(ctx),
                description="One question, pursued honestly: What is an Electron? History told from the original papers, "
                            "speculation labeled as speculation, and shop practice.",
                body=hero + orient + episode_row + author_row + records_row + disclosure + subscribe(ctx))


# ------------------------------------------------------------------ EPISODES
EPISODES_DESCRIPTION = "Every episode of The Electron Plumber, with its notes, sources and corrections."


def episodes(ctx: Ctx):
    published, upcoming = ctx.published, ctx.upcoming
    head = ('<div class="page-head"><h1 class="h1 h1--page">Episodes</h1>'
            '<p class="deck deck--sm g20">Every episode is labeled &mdash; historical record, established physics, explicit speculation, or shop practice.</p></div>')

    filt = ""
    if len(published) > 1:
        chips = '<button class="chip" type="button" data-value="all" aria-pressed="true">All</button>' + "".join(
            f'<button class="chip" type="button" data-value="{a}" aria-pressed="false" style="--c: var(--{c});"><i></i>{n}</button>'
            for a, n, c in (("historical", "Historical", "sky"), ("speculative", "Speculative", "orange"),
                            ("practical", "Practical", "green")))
        # An upcoming episode with no arc yet has no data-arc, so the filter never hides it.
        filt = (f'<div class="filter" data-filters data-items=".ep-row[data-arc]" data-empty="Nothing in this arc yet." hidden><div class="inner">'
                f'<div class="filter__chips" role="group" aria-label="Filter by arc" data-filter="arc">{chips}</div>'
                f'<div class="mono" role="status" data-total="{len(published)}" data-noun="published">{len(published)} published</div></div></div>')

    rows = ""
    for ep in published:
        meta = f'{kicker(ep.serial, "kicker--white")}{badge(ep.arc)}{mono(" &middot; ".join((esc(ep.date) or "[DATE]", esc(ep.runtime) or "[RUNTIME]")))}'
        rows += (f'<article class="ep-row" data-arc="{ep.arc}"><div class="inner"><div class="ep-row__card">'
                 f'<a href="{ctx.to(ep.url)}" aria-label="{esc(ep.serial)}: {md.plain(ep.title)}">{card(ctx, ep.serial, ep.title)}</a></div>'
                 f'<div class="stack"><div class="cluster cluster--tight">{meta}</div><h2 class="h2 h2--row g16">{md.plain(ep.title)}</h2>'
                 f'<p class="small g12">{esc(ep.excerpt)}</p><div class="cluster g24">{btn("Watch", ctx.to(ep.url))}'
                 f'{arrow("Episode notes", ctx.to(ep.url) + "#learning-goals")}</div></div></div></article>')
    if upcoming:
        arc_attr = f' data-arc="{upcoming.arc}"' if upcoming.arc else ""
        rows += (f'<article class="ep-row"{arc_attr}><div class="inner"><div class="ep-row__card">{card(ctx, upcoming.serial, upcoming.title, dim=True, nxt=True)}</div>'
                 f'<div class="stack"><div class="cluster cluster--tight">{kicker("Next &middot; " + upcoming.serial, "kicker--orange")}{_badge(upcoming)}</div>'
                 f'<h2 class="h2 h2--row g16" style="color: var(--orange);">{md.plain(upcoming.title)}</h2>'
                 + (f'<p class="small g12">{esc(upcoming.excerpt)}</p>' if upcoming.excerpt else "")
                 + '<div class="mono g20">In production</div></div></div></article>')
    if not rows:
        rows = '<div class="empty"><p class="prose">Nothing published yet.</p></div>'

    title, description = PAGE_TEXT["episodes/"]
    return page(ctx, title=title, active=title, description=description, body=head + filt + rows + subscribe(ctx))


# ------------------------------------------------------------------ EPISODE
CORRECTIONS_FALLBACK = ('<p>Standing corrections for all episodes are tracked in ERRATA.md. Spotted an error? Open an issue &mdash; '
                        'corrections are part of the product here, not an embarrassment.</p>')
CLAIMS_INTRO = "Tracked claims from this episode that the History page or the corrections ledger points to."
VEHICLES = {"description": "Description edit", "pinned-comment": "Pinned comment", "erratum-short": "Erratum short"}
LEDGER_COLUMNS = ("Claim", "What I said", "What&rsquo;s right", "Fixed in")
# The column heads are hidden on phones by site.css, and from assistive technology here: each cell carries its own label.
LEDGER_HEAD = '<div class="ledger__head" aria-hidden="true">' + "".join(f"<div>{c}</div>" for c in LEDGER_COLUMNS) + "</div>"


def _claim_note(claims, href=""):
    links = ", ".join(f'<a href="{href}#{esc(c)}">{esc(c)}</a>' for c in claims)
    return f" ({'claims' if len(claims) > 1 else 'claim'} {links})" if claims else ""


def _episode_sources(ep):
    if not ep.sources:
        return ""
    items = "".join(_citation(s.entry, s) for s in ep.sources)
    return f'<section class="block" id="ep-sources"><h2>Sources</h2><ol class="tl__sources">{items}</ol></section>'


def _episode_claims(ctx, ep):
    if not ep.claims:
        return ""
    items = ""
    for claim in ep.claims:
        cors = [c for c in ep.corrections if c.claim == claim]  # newest first, so cors[0] sets the status
        parts = [f"<code>{esc(claim)}</code>", content.CORRECTION_KINDS[cors[0].kind] if cors else "As aired"]
        events = [ev for ev in ep.events if claim in ev.claims]
        if events:
            parts.append("On the History page: " + ", ".join(
                f'<a href="{ctx.to("history/")}#{esc(ev.id)}">{md.plain(ev.title)}</a>' for ev in events))
        if cors:
            parts.append(", ".join(f'<a href="#{esc(c.id)}">{esc(c.id)}</a>' for c in cors))
        items += f'<li id="{esc(claim)}">{" &middot; ".join(parts)}</li>'
    return (f'<section class="block" id="ep-claims"><h2>Claims</h2><p>{CLAIMS_INTRO}</p>'
            f'<ul class="ep-claims">{items}</ul></section>')


def _episode_history(ctx, ep):
    if not ep.events:
        return ""
    prefix = f"ep{ep.number:03d}-"
    items = "".join(
        f'<li>{_when(ev)} <a href="{ctx.to("history/")}#{esc(ev.id)}">{md.plain(ev.title)}</a>'
        f'{_claim_note([c for c in ev.claims if c.startswith(prefix)])}</li>' for ev in ep.events)
    return f'<section class="block" id="ep-history"><h2>On the History page</h2><ul class="ep-history">{items}</ul></section>'


def _ledger_row(ctx, cor, *, link_episode=False):
    """One corrections-ledger row. On the episode page the claim links within the page; elsewhere, to the episode."""
    by_number = {e.number: e for e in ctx.episodes}
    href = (ctx.to(by_number[cor.episode].url) if link_episode else "") + "#" + cor.claim
    segment = content.VEHICLE.fullmatch(cor.vehicle).group(1)
    if segment:
        seg = by_number[int(segment)]
        vehicle = "Segment in " + (f'<a href="{ctx.to(seg.url)}">{esc(seg.serial)}</a>' if seg.live else esc(seg.serial))
    else:
        vehicle = VEHICLES[cor.vehicle]
    fixed = f"{vehicle} &middot; {_time(cor.date)} &middot; {content.CORRECTION_KINDS[cor.kind]}"
    cells = zip(LEDGER_COLUMNS, (f'<a href="{esc(href)}">{esc(cor.claim)}</a>', cor.was, cor.now, fixed), strict=True)
    return (f'<div class="ledger__row" id="{esc(cor.id)}">'
            + "".join(f'<div><span class="vh">{label}</span> {text}</div>' for label, text in cells) + "</div>")


def episode(ctx: Ctx, ep):
    meta = " &middot; ".join((esc(ep.date) or "[DATE]", esc(ep.runtime) or "[RUNTIME]"))
    head = (f'<div class="post-head">{arrow("All episodes", ctx.to("episodes/"), back=True)}'
            f'<div class="cluster cluster--tight g28">{kicker(ep.serial, "kicker--white")}{badge(ep.arc)}{mono(meta)}</div>'
            f'<h1 class="h1 h1--page g20">{md.plain(ep.title)}</h1>'
            + (f'<p class="deck deck--sm g20">{esc(ep.orientation)}</p>' if ep.orientation else "") + '</div>')
    video = f'<div class="post-video">{card(ctx, ep.serial, ep.title, youtube_id=ep.youtube_id)}</div>'

    blocks, corrections = "", ("Corrections", CORRECTIONS_FALLBACK)
    for title, body in ep.sections:
        anchor = "-".join(title.lower().split())
        if anchor == "corrections":
            corrections = (title, body)
            continue
        blocks += f'<section class="block" id="{esc(anchor)}"><h2>{esc(title)}</h2>{body}</section>'
    blocks += _episode_sources(ep) + _episode_claims(ctx, ep) + _episode_history(ctx, ep)
    # Ledger rows, when there are any, stand in for the notes' own corrections text: the ledger is the record.
    rows = "".join(_ledger_row(ctx, cor) for cor in ep.corrections)
    title, body = corrections
    blocks += (f'<section class="block" id="corrections"><h2>{esc(title)}</h2>'
               f'{LEDGER_HEAD + rows if rows else body}</section>')
    report = f'<div class="g8">{arrow("Report an error", ctx.site["notes_repo"] + "/issues", external=True)}</div>'
    article = f'<article class="article">{blocks}{report}<div class="g48"></div></article>'

    nxt = ""
    if ctx.upcoming:
        up = ctx.upcoming
        nxt = (f'<div class="next-band"><a href="{ctx.to("episodes/")}"><div class="stack">{kicker("Next &middot; " + up.serial, "kicker--orange")}'
               f'<div class="next-band__title g12">{md.plain(up.title)}</div></div>{_badge(up)}</a></div>')

    return page(ctx, title=f"{ep.serial}: {ep.title}", active="Episodes", arc=ep.arc or None, noindex=ep.draft,
                description=ep.excerpt or f"{ep.serial} of The Electron Plumber.", body=head + video + article + nxt)


# ------------------------------------------------------------------ HISTORY
HISTORY_INTRO = ("History, told from the original papers. Each entry is a dated step in the long argument over what an electron is, "
                 "with the papers it rests on. Every source is listed in sources.bib, and when I get one wrong, it goes on the "
                 "corrections ledger. A date marked c. is an estimate; the record gives no exact day.")
HISTORY_LEGEND = "Each entry says whether it was checked against the original paper or letter, or against secondary sources only."
HISTORY_DESCRIPTION = ("A dated timeline of the search for what an electron is, told from the original papers. "
                       "Every entry cites its sources.")
MONTHS = ("January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December")
DATE_BASIS_PREFIX = {"read": "Read", "received": "Received", "published": "Published"}


def _date_text(value):
    parts = [int(p) for p in value.split("-")]
    if len(parts) == 3:
        return f"{parts[2]} {MONTHS[parts[1] - 1]} {parts[0]}"
    if len(parts) == 2:
        return f"{MONTHS[parts[1] - 1]} {parts[0]}"
    return str(parts[0])


def _time(value):
    return f'<time datetime="{esc(value)}">{_date_text(value)}</time>'


def _when(ev):
    """The date line: date_basis prefix, then a date (circa, range) or open-ended bounds."""
    if ev.date:
        text = ('<abbr title="circa">c.</abbr> ' if ev.circa else "") + _time(ev.date)
        if ev.end:
            text += "&ndash;" + _time(ev.end)
    elif ev.not_before and ev.not_after:
        text = f"between {_time(ev.not_before)} and {_time(ev.not_after)}"
    elif ev.not_before:
        text = f"after {_time(ev.not_before)}"
    else:
        text = f"before {_time(ev.not_after)}"
    prefix = DATE_BASIS_PREFIX.get(ev.date_basis)
    if prefix:
        return f"{prefix} {text}"
    return text[0].upper() + text[1:] if text[0].islower() else text


def _authors(names):
    if len(names) > 3:
        return f"{names[0]} et al."
    return names[0] if len(names) == 1 else ", ".join(names[:-1]) + " and " + names[-1]


def _reading_links(entry, src):
    """A timeline entry's primary source: the original, by DOI or url, then a free full text if there is one."""
    f = entry.fields
    doi, url, links = src.doi or f.get("doi", ""), src.url or f.get("url", ""), []
    if doi:
        links.append(f'<a class="tl__read" href="https://doi.org/{esc(doi)}">Original paper</a> <span class="mono">doi:{esc(doi)}</span>')
    elif url:
        label = "Original letter" if f["title"].lower().startswith("letter ") else "Original"
        links.append(f'<a class="tl__read" href="{esc(url)}">{label}</a>')
    if src.fulltext_url:
        links.append(f'<a href="{esc(src.fulltext_url)}">Free full text</a>')
    return " &middot; ".join(links)


def _citation(entry, src, *, read=False):
    """One source line. The citation text comes from sources.bib; the timeline adds kind, locator, link and note.
    With read, the links are a timeline entry's reading links instead of the small DOI or url link."""
    f = entry.fields
    venue = next((f[k] for k in ("journal", "booktitle", "howpublished", "publisher", "institution", "school") if f.get(k)), "")
    where = venue + (f" {f['volume']}" if f.get("volume") else "") + (f" ({f['number']})" if f.get("number") else "")
    where += (f", {f['pages']}" if f.get("pages") else "")
    where = (f"{where} ({f['year']})" if where else f["year"]) + (f", {src.locator}" if src.locator else "")
    def stop(text):
        return "" if text.endswith((".", "?", "!")) else "."

    title, rest = f["title"], ([_authors(entry.authors)] if entry.authors else []) + [where]
    text = f"<cite>{md.plain(title)}</cite>{stop(title)} " + " ".join(md.plain(p) + stop(p) for p in rest)
    doi, url = src.doi or f.get("doi", ""), src.url or f.get("url", "")
    if read:
        links = _reading_links(entry, src)
        text += f" {links}" if links else ""
    elif doi:
        text += f' <a href="https://doi.org/{esc(doi)}" rel="noopener">doi:{esc(doi)}</a>'
    elif url:
        text += f' <a href="{esc(url)}" rel="noopener">{esc(url.removeprefix("https://"))}</a>'
    if src.note:
        text += f" {md.plain(src.note)}"
    return f'<li>{text} <span class="mono">{src.kind.capitalize()}</span></li>'


def _episode_links(ctx, ev):
    """Claims and episode links, for published episodes only: nothing is named before it exists."""
    by_number = {e.number: e for e in ctx.episodes}
    linked = {}
    for claim in ev.claims:
        number = int(claim[2:5])
        if by_number[number].live:
            linked.setdefault(number, []).append(claim)
    for number in ev.episodes:
        if by_number[number].live:
            linked.setdefault(number, [])
    out = []
    for number, claims in linked.items():
        ep = by_number[number]
        out.append(f'<a href="{ctx.to(ep.url)}">{esc(ep.serial)}</a>{_claim_note(claims, ctx.to(ep.url))}')
    return f'<p class="small tl__episodes">In {"; ".join(out)}</p>' if out else ""


def _credit(img):
    """The approved credit line for each licence. It is always shown, public domain included."""
    commons = f'<a href="{esc(img.source_url)}">Wikimedia Commons</a>'
    if img.license == "own-work":
        return "Diagram: The Electron Plumber."
    if img.license == "public-domain":
        return f"Image: {esc(img.author)}. Public domain, via {commons}."
    if img.license == "cc0":
        return f"Image: {esc(img.author)}. Dedicated to the public domain (CC0), via {commons}."
    return (f"Image: {esc(img.title)}, by {esc(img.author)}. Cropped and resized. Licensed under "
            f'<a href="https://creativecommons.org/licenses/by/4.0/">Creative Commons Attribution 4.0</a>, via {commons}.')


def _figure(ctx, img):
    """Self-hosted and lazy; width and height are the file's pixels, so the space is reserved before it loads."""
    if img is None:
        return ""
    caption = f"{esc(img.caption)} " if img.caption else ""
    return (f'<figure class="tl__figure"><img src="{ctx.to(img.file.removeprefix("static/"))}" width="{img.width}" '
            f'height="{img.height}" alt="{esc(img.alt)}" loading="lazy" decoding="async">'
            f'<figcaption class="mono small">{caption}<span class="tl__credit">{_credit(img)}</span></figcaption></figure>')


def _era_bounds(slug):
    """data-from/data-to on an era chip, for the axis site.js draws; an empty data-to is an open end."""
    _, first, last = content.ERAS[slug]
    return f' data-from="{first}" data-to="{last or ""}"'


def _history_filters(events):
    def group(name, label_all, aria, vocab, used):
        chips = f'<button class="chip" type="button" data-value="all" aria-pressed="true">{label_all}</button>' + "".join(
            f'<button class="chip" type="button" data-value="{slug}"{_era_bounds(slug) if name == "era" else ""} '
            f'aria-pressed="false">{esc(label)}</button>'
            for slug, label in vocab.items() if slug in used)
        return f'<div class="filter__chips" role="group" aria-label="{aria}" data-filter="{name}">{chips}</div>'

    total = len(events)
    noun = "event" if total == 1 else "events"
    return ('<div class="filter filter--multi" data-filters data-items=".tl" data-empty="Nothing matches." hidden><div class="inner">'
            + group("era", "All eras", "Filter by era", {k: v[0] for k, v in content.ERAS.items()}, {e.era for e in events})
            + group("thread", "All subjects", "Filter by subject", content.THREADS, {t for e in events for t in e.thread})
            + group("class", "All kinds", "Filter by kind of event", content.CLASSES, {e.cls for e in events})
            + f'<div class="mono" role="status" data-total="{total}" data-noun="{noun}">{total} {noun}</div></div></div>')


HISTORY_YEARS_LABEL = "Jump to a year"


def _history_years(events):
    """Phones only (site.css hides it above 560px): one plain link per entry, by its year. Works without JavaScript."""
    links = "".join(f'<a href="#{esc(ev.id)}">{ev.sort_key[0]}</a>' for ev in events)
    return f'<nav class="tl-years" aria-label="{HISTORY_YEARS_LABEL}">{links}</nav>'


def history(ctx: Ctx):
    title, description = PAGE_TEXT["history/"]
    events = list(ctx.timeline)
    head = (f'<div class="page-head"><div class="notice">{badge("historical")}<div class="mono mono--body">Historical record.</div></div>'
            f'<h1 class="h1 h1--page g20">History</h1><p class="deck deck--sm g20">{HISTORY_INTRO}</p>'
            f'<p class="small muted g16">{HISTORY_LEGEND}</p></div>')
    if not events:
        body = '<div class="empty"><p class="prose">Nothing published yet.</p></div>'
        return page(ctx, title=title, active=title, description=description, body=head + body + subscribe(ctx))

    titles = {e.id: e.title for e in events}
    items = ""
    for ev in events:
        era_label, era_first, era_last = content.ERAS[ev.era]
        meta = " &middot; ".join([esc(f"{era_label}, {era_first}\u2013{era_last or 'present'}"), esc(content.CLASSES[ev.cls]),
                                  esc(", ".join(content.THREADS[t] for t in ev.thread)), content.VERIFIED[ev.verified]])
        people = f'<p class="mono tl__people">{esc(", ".join(ev.people))}</p>' if ev.people else ""
        sources = "".join(_citation(s.entry, s, read=s.kind == "primary") for s in ev.sources)
        further = ('<p class="small tl__further">Further reading: ' + "; ".join(
            f'<a href="{esc(x.url)}">{md.plain(x.title)}</a> ({md.plain(x.publisher)})' for x in ev.further) + ".</p>"
                   if ev.further else "")
        related = ('<p class="small tl__related">See also ' + ", ".join(f'<a href="#{esc(r)}">{md.plain(titles[r])}</a>' for r in ev.related)
                   + "</p>") if ev.related else ""
        oneliner = f' data-oneliner="{esc(ev.oneliner)}"' if ev.oneliner else ""
        items += (f'<li class="tl" id="{esc(ev.id)}" data-era="{esc(ev.era)}" data-thread="{esc(" ".join(ev.thread))}" '
                  f'data-class="{esc(ev.cls)}" data-verified="{esc(ev.verified)}" data-year="{ev.sort_key[0]}"{oneliner}><article>'
                  f'<p class="mono tl__date">{_when(ev)}</p>'
                  f'<h3 class="h3 tl__title"><a href="#{esc(ev.id)}">{md.plain(ev.title)}</a></h3>'
                  f'<p class="mono tl__meta">{meta}</p>{_figure(ctx, ev.image)}'
                  f'<p class="small tl__summary">{md.plain(ev.summary)}</p>{people}'
                  f'<ol class="tl__sources">{sources}</ol>{further}'
                  f'<p class="mono tl__checked">Checked {_time(ev.checked_date)}</p>'
                  f'{_episode_links(ctx, ev)}{related}</article></li>')
    timeline = row("Timeline", f'<ol class="timeline">{items}</ol>', "row--tight", heading=True)
    return page(ctx, title=title, active=title, description=description,
                body=head + _history_years(events) + _history_filters(events) + timeline + subscribe(ctx))


# ------------------------------------------------------------------ RESEARCH
RESEARCH_DESCRIPTION = ("Applied Vacuum Engineering: a falsifiable impedance model of the vacuum. Explicitly speculative, "
                        "with its kill criteria stated up front.")


FALSIFIER_KICKERS = {"excluded": "Excluded by data", "armed": "Armed &middot; pre-registered"}


def research(ctx: Ctx):
    core, counts = ctx.site["core_repo"], ctx.research
    armed = counts.armed
    letter = core + "/blob/main/papers/2026_birefringence_letter/sve_vacuum_birefringence_letter.pdf"
    head = (f'<div class="page-head" style="padding-top: 80px; padding-bottom: 72px;"><div class="notice">{badge("speculative")}'
            f'<div class="mono mono--body">Explicit speculation.</div></div>'
            f'<h1 class="h1 g28">Applied Vacuum Engineering</h1>'
            f'<p class="deck g16" style="font-size: clamp(19px, 1.8vw, 26px);">A falsifiable impedance model of the vacuum.</p>'
            f'<div class="mono g28">Apache-2.0 &nbsp;&middot;&nbsp; {armed} armed forward falsifier{"s" if armed != 1 else ""} '
            f'&nbsp;&middot;&nbsp; {counts.consistency_entries} consistency-class entries</div></div>')

    wager = row("The wager", (
        '<p class="prose prose--lg">Applied Vacuum Engineering is a falsification-first <em>engineering</em> model of the vacuum. '
        'It treats empty space not as a geometric abstraction but as a real, saturable LC lattice: a transmission-line medium with a '
        'finite inductive density (&mu;&#8320;), a finite capacitive density (&epsilon;&#8320;), a characteristic impedance '
        'Z&#8320; = &radic;(&mu;&#8320;/&epsilon;&#8320;) &asymp; 377 &Omega;, and a hard yield ceiling above which it snaps.</p>'
        '<p class="prose prose--lg g24">The wager is that the electron-plumber habit, reading electrical phenomena as mechanical '
        'stress in one medium, is the correct disciplinary frame. The point of the work is to find out where that wager breaks.</p>'),
        "row--tight", heading=True)

    cards = []

    def fcard(fid, color, title, text, link_text, href, mod):
        cards.append(fid)
        if fid not in counts.falsifiers:
            raise content.ContentError(f"research.toml: no [[falsifier]] with id {fid!r} for the Research page's card")
        status = FALSIFIER_KICKERS[counts.falsifiers[fid]]
        return (f'<div class="fcard" style="--c: var(--{color});"><div class="fcard__top"></div><div class="fcard__body">'
                f'{kicker(status, "kicker--" + color)}<h3 class="h3 g16">{title}</h3><p class="small g16">{text}</p>'
                f'{arrow(link_text, href, mod, external=True)}</div></div>')

    die = row("Experimental falsification", (
        '<h2 class="h2">What kills the framework.</h2><div class="grid grid--2 g40">'
        + fcard("electrostatic-gauntlet", "vermillion", "The electrostatic gauntlet",
                "The framework put its own continuum static-field law on trial against muonic hydrogen, the sharpest available "
                "probe of the atom&rsquo;s near-nucleus field. The law lost. Extrapolated into the atom&rsquo;s static sector, it "
                "overshoots the measured Lamb-shift window, 202.3706(23) meV, by about 2&times;10<sup>4</sup>. A completed "
                "falsification, banked on the record.", "Read the adjudication", core + "#experimental-falsification", "arrow--vermillion")
        + fcard("vacuum-birefringence", "orange", "Vacuum birefringence",
                "A tree-level X-ray vacuum birefringence, a field-independent factor 3.75&pi;/&alpha;<sup>2</sup> &asymp; "
                "2.2&times;10<sup>5</sup> above one-loop QED. The kill criterion was committed before any data and timestamped on "
                "the Bitcoin blockchain: a 5&sigma; pump-on null, P<sub>flip</sub> &lt; 10<sup>&minus;8</sup> at a pump intensity of "
                "10<sup>18</sup> W/cm<sup>2</sup> or more, falsifies the model&rsquo;s electric sector. No rescue.",
                "Read the Letter (PDF)", letter, "arrow--orange")
        + '</div>'), "row--tight")
    extra = [fid for fid in counts.falsifiers if fid not in cards]
    if extra:
        raise content.ContentError(f"research.toml: falsifier {extra[0]!r} has no card on the Research page")

    def axiom(n, name, text):
        return f'<div class="trow"><div class="trow__n">{n}</div><div class="trow__name">{name}</div><div class="trow__text">{text}</div></div>'

    axioms = row("Four axioms", (
        axiom("01", "Impedance", "The vacuum is an LC resonant network with Z&#8320; = &radic;(&mu;&#8320;/&epsilon;&#8320;).")
        + axiom("02", "Topo-kinematic isomorphism", "Charge is a geometric dislocation: [Q] &equiv; [L]. Topology encodes electromagnetism.")
        + axiom("03", "Gravity", "G sets the Machian boundary impedance.")
        + axiom("04", "Saturation", "S(A) = &radic;(1 &minus; (A/A<sub>yield</sub>)<sup>2</sup>): a universal yield kernel bounding all LC modes.")),
        "row--tight", heading=True)

    formval = row("Organizing principle", (
        '<h2 class="h2">Form is derived. Value is imported.</h2>'
        '<p class="prose prose--lg g28">The geometry and topology of the substrate force the dimensionless <em>forms</em> of the '
        'constants: the structure. The numerical <em>values</em> of a small marked set, &#123;m<sub>e</sub>, &alpha;, G&#125;, are '
        'calibration inputs the substrate is fed and does not independently select. Forcing the skeleton from topology alone is the '
        'claim. Selecting the numerical values of its own calibration constants is not.</p>'), "row--tight")

    def doc(title, text, kind, href):
        return (f'<a class="trow" href="{esc(href)}" rel="noopener"><div class="trow__name">{title}</div>'
                f'<div class="trow__text">{text}</div><div class="trow__kind">{kind}</div></a>')

    read = row("Read it", (
        doc("The Letter", "Saturable Vacuum Electrodynamics: a tree-level vacuum-birefringence prediction for a pump&ndash;probe "
            "X-ray polarimeter.", "PDF", letter)
        + doc("The manuscript", "Eight volumes, from foundations and the subatomic lattice to applied impedance engineering and "
              "the vacuum-cell datasheet.", "GitHub", core + "/tree/main/manuscript")
        + doc("The trampoline framework", "The picture-first entry point: a six-step, ground-up build of the whole picture.",
              "Knowledge base", core + "/blob/main/manuscript/ave-kb/common/trampoline-framework.md")
        + doc("The code", "Solvers, tests and the verification gate.", "GitHub", core)
        + doc("The pre-registration ledger", "The birefringence prediction and its kill criterion, hashed and Bitcoin-timestamped "
              "before any pump-on data exists.", "GitHub",
              core + "/tree/main/claim-prereg-ots")), "row--tight", heading=True)

    title, description = PAGE_TEXT["research/"]
    return page(ctx, title=title, active=title, arc="speculative", description=description,
                body=head + wager + die + axioms + formval + read)


# ------------------------------------------------------------------ RECORDS (labels, claim format, ledger, sources)
RECORDS_DESCRIPTION = ("Corrections are part of the product here, not an embarrassment. "
                       "Labels, claim format, the ledger, sources and licenses.")


def records(ctx: Ctx):
    notes = ctx.site["notes_repo"]
    head = (f'<div class="page-head" style="padding-bottom: 72px;">{kicker(RECORDS[0])}<h1 class="h1 g16">Spotted an error? Open an issue.</h1>'
            f'<p class="deck g20">Corrections are part of the product here, not an embarrassment.</p></div>')

    def label_row(arc, status, text):
        return (f'<div class="trow trow--center"><div class="trow__badge">{badge(arc)}</div>'
                f'<div class="trow__status mono">{status}</div><div class="trow__text">{text}</div></div>')

    labels = row("The labels", (
        '<h2 class="h2">Every episode is labeled.</h2><div class="g36">'
        + label_row("historical", "Historical record", "Physics as it was published at the time. Every source is listed in sources.bib.")
        + label_row("speculative", "Explicit speculation", "Not established physics. The kill criteria are on the Research page.")
        + label_row("practical", "Shop practice", "Failure analysis at the bench, on circuits rebuilt for the camera.")
        + '</div><p class="prose g36">A label here is a field in a file, and the build reads it. Each thing I commit to on camera is one tagged line in '
          'that episode&rsquo;s outline. A speculative line in a historical episode stops the build. So does a fact that reaches '
          'recording without a source.</p>'), "row--tight")

    def legend(term, text):
        return f'<div class="legend"><div class="legend__term">{term}</div><p>{text}</p></div>'

    claim = row("A claim, tracked", (
        '<h2 class="h2">This is what a tracked claim looks like.</h2>'
        '<div class="claim g28"><i>CLAIM</i> <b>ep0NN-c0N</b> FACT topic=example-topic src=author1900word</div>'
        '<div class="grid grid--4 g24">'
        + legend("ep0NN-c0N", "Episode number, then claim number. A later episode that reuses the claim points back to this ID.")
        + legend("FACT", "One of four classes. The build checks it against the episode&rsquo;s label.")
        + legend("topic=", "What the claim is about. If two claims share a topic, I check them against each other by hand.")
        + legend("src=", "The entry in sources.bib that backs it.")
        + '</div><p class="prose g32">Once an episode is out, its claims stay as aired. The register keeps moving as I learn more, '
          'so sooner or later the two disagree. Each disagreement becomes a row in the corrections ledger.</p>'), "row--tight")

    ledger = row("Corrections", (
        '<h2 class="h2">What I got wrong.</h2><div class="g28"><div class="ledger__head"><div>Claim</div><div>What I said</div>'
        '<div>What&rsquo;s right</div><div>Fixed in</div></div><div class="ledger__empty">Nothing yet.</div></div>'
        '<p class="prose g32">A small error gets a description edit or a pinned comment. A big one gets time in a later '
        'episode, or a short of its own, and either way it gets a row above.</p>'
        f'<p class="prose g16">Entries on the <a href="{ctx.to("history/")}">History</a> page follow the same rules: each cites its '
        'sources in sources.bib, and a factual error in one gets a row in this ledger.</p>'
        f'<div class="g28">{btn("Report an error", notes + "/issues", "btn--secondary", external=True)}</div>'), "row--tight")

    def lic(label, text, link_text, href):
        return (f'<div class="stack">{kicker(label, "kicker--sm")}<p class="small g12">{text}</p>'
                f'<div class="g12">{arrow(link_text, href, external=True)}</div></div>')

    sources = row("Sources and licenses", (
        '<div class="grid grid--3">'
        + lic("Sources", "All on-camera citations live in one BibTeX file, free to reuse.", "sources.bib", notes + "/blob/main/sources.bib")
        + lic("Episode notes", "CC BY-NC-ND 4.0: share with attribution; no commercial use; no derivatives.", "The notes repo", notes)
        + lic("Research code", "Apache-2.0.", "AVE-Core on GitHub", ctx.site["core_repo"]) + '</div>'), "row--tight", heading=True)

    title, description = PAGE_TEXT[RECORDS[1]]
    return page(ctx, title=title, active=title, description=description, body=head + labels + claim + ledger + sources)


# ------------------------------------------------------------------ ABOUT
ABOUT_DESCRIPTION = "{author} is a staff electrical engineer in grid-scale energy storage, asking what an electron is. Views my own."


def about(ctx: Ctx):
    s = ctx.site
    portrait = _portrait(ctx, "portrait--lg", sizes="(max-width: 860px) min(400px, 88vw), min(400px, 32vw)", lazy=False)
    head = (f'<div class="about-head">{portrait}<div class="stack">{kicker("About")}'
            f'<h1 class="h1 h1--page g16">{esc(s["author"])}</h1><div class="tagline g20">{esc(s["tagline"])}</div>'
            f'<p class="prose g32">{ABOUT}</p><div class="mono g24">Views my own.</div>'
            f'<div class="g24">{arrow(START_TITLE, ctx.to("start/"))}</div></div></div>')

    def route(name, text, kind, href):
        return (f'<a class="trow" href="{esc(href)}" rel="noopener"><div class="trow__name trow__name--sm">{name}</div>'
                f'<div class="trow__text">{text}</div><div class="trow__kind">{kind}</div></a>')

    email = s.get("contact_email", "")
    routes = route("Report an error", "A factual error in a video goes straight onto the corrections ledger.", "GitHub issues",
                   s["notes_repo"] + "/issues")
    if email:
        routes += route("Everything else", "Collaboration, press, or a question about an episode.", "Email", "mailto:" + email)
    routes += route("The channel", "Comments are open on every episode.", "YouTube", s["youtube"])
    contact = row("Contact", (f'<h2 class="h2">{"Get in touch." if email else "Found an error?"}</h2><div class="g36">{routes}</div>'),
                  "row--panel row--tight")
    contact = contact.replace('<section class="row ', '<section id="contact" class="row ', 1)

    title, description = PAGE_TEXT["about/"]
    return page(ctx, title=title, active=title, description=description.format(author=s["author"]), body=head + contact)


# ------------------------------------------------------------------ START HERE
# The title and meta description of each page a Start here step can point at. Descriptions are format
# strings: {author} is the site author.
PAGE_TEXT = {"episodes/": ("Episodes", EPISODES_DESCRIPTION), "history/": ("History", HISTORY_DESCRIPTION),
             "research/": ("Research", RESEARCH_DESCRIPTION), RECORDS[1]: (RECORDS[0], RECORDS_DESCRIPTION),
             "about/": ("About", ABOUT_DESCRIPTION)}
ROUTE_ARCS = {"history/": "historical", "research/": "speculative"}
START_TITLE = "Start here"
START_DESCRIPTION = "Where to begin: the question, the history, then the episodes."
START_DECK = "Three stops for a first visit."


def _start_step(ctx, n, step):
    if step.kind == "episode":
        ep = step.episode
        if ep.live:
            heading = f'<a href="{ctx.to(ep.url)}">{md.plain(ep.title)}</a>'
            text, arc = f'<p class="small g12">{esc(ep.excerpt)}</p>', ep.arc
        else:
            heading = md.plain(ep.title)
            text, arc = f'<p class="small g12">{DECK}</p>{mono(ep.serial + " is in production", "g12")}', None
    else:
        title, description = PAGE_TEXT[step.route]
        href = ctx.to(step.route) + (f"#{step.anchor}" if step.anchor else "")
        heading = f'<a href="{esc(href)}">{esc(title)}</a>'
        text = f'<p class="small g12">{esc(description.format(author=ctx.site["author"]))}</p>'
        arc = ROUTE_ARCS.get(step.route)
        if step.route == "episodes/":
            latest = (ctx.published or [None])[0]
            if latest:
                text += f'<div class="g20">{arrow(f"Watch {latest.serial}", ctx.to(latest.url))}</div>'
            if ctx.upcoming:
                text += _next_line(ctx, ctx.upcoming)
    head = f'<h2 class="h3">{heading}</h2>' + (badge(arc) if arc else "")
    return (f'<li class="trow"><div class="trow__n" aria-hidden="true">{n:02d}</div>'
            f'<div class="stack"><div class="cluster cluster--tight">{head}</div>{text}</div></li>')


def start(ctx: Ctx):
    head = (f'<div class="page-head"><h1 class="h1 h1--page">{START_TITLE}</h1>'
            f'<p class="deck deck--sm g20">{START_DECK}</p></div>')
    steps = "".join(_start_step(ctx, n, step) for n, step in enumerate(ctx.start, 1))
    return page(ctx, title=START_TITLE, active=None, description=START_DESCRIPTION,
                body=head + row("", f'<ol class="start-steps">{steps}</ol>') + subscribe(ctx))


# ------------------------------------------------------------------ 404 + redirects
def not_found(ctx: Ctx):
    body = (f'<div class="lost">{kicker("404")}<h1 class="h1 h1--page g16">Nothing at this address.</h1>'
            f'<div class="cluster g40">{btn("Home", ctx.to())}{arrow("Episodes", ctx.to("episodes/"))}</div></div>')
    return page(ctx, title="Not found", description="Nothing at this address.", body=body, noindex=True)


def redirect(target, canonical=None):
    t, c = esc(target), esc(canonical or target)
    return (f'<!doctype html>\n<html lang="en"><head><meta charset="utf-8"><title>Redirecting</title>'
            f'<meta http-equiv="refresh" content="0; url={t}"><meta name="robots" content="noindex">'
            f'<link rel="canonical" href="{c}"></head><body><p><a href="{t}">{c}</a></p></body></html>\n')
