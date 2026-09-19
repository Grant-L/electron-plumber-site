"""Page shell and the shared components: header, footer (the spec plate), badges, buttons, the title card."""
import html as _html

from .content import ARCS

FONTS = ("https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600"
         "&amp;family=Source+Serif+4:ital,opsz,wght@0,8..60,400;0,8..60,600;0,8..60,700;1,8..60,400&amp;display=swap")
RECORDS = ("Corrections", "corrections/")  # the page with the labels, the claim format, the ledger, sources and licenses
NAV = [("Episodes", "episodes/"), ("Research", "research/"), RECORDS, ("About", "about/")]
ARROW = ('<svg width="16" height="12" viewBox="0 0 16 12" fill="none" aria-hidden="true">'
         '<path d="M0 6h14M9 1l5 5-5 5" stroke="currentColor" stroke-width="1.6"/></svg>')
BACK = ('<svg width="16" height="12" viewBox="0 0 16 12" fill="none" aria-hidden="true">'
        '<path d="M16 6H2M7 1L2 6l5 5" stroke="currentColor" stroke-width="1.6"/></svg>')


def esc(text):
    return _html.escape(str(text), quote=True)


class Ctx:
    """Everything a template needs, plus link helpers that stay relative so the site works from any base path."""

    def __init__(self, site, episodes, path, version, absolute=False):
        self.site, self.episodes, self.path, self.version = site, episodes, path, version
        depth = path.count("/")
        self.root = "/" if absolute else ("../" * depth if depth else "./")

    def to(self, target=""):
        return self.root + target

    def asset(self, target):
        return f"{self.root}{target}?v={self.version}"

    @property
    def published(self):
        return sorted((e for e in self.episodes if e.live), key=lambda e: -e.number)

    @property
    def upcoming(self):
        return next((e for e in self.episodes if not e.live and e.announce), None)

    @property
    def sub_url(self):
        return self.site["youtube"] + "?sub_confirmation=1"


# ---------------------------------------------------------------- atoms
def kicker(text, mod=""):
    return f'<div class="kicker {mod}">{text}</div>'


def mono(text, mod=""):
    return f'<div class="mono {mod}">{text}</div>'


def badge(arc):
    return f'<span class="badge badge--{arc}">{ARCS[arc]}</span>'


def btn(text, href, mod="", external=False):
    rel = ' rel="noopener"' if external else ""
    return f'<a class="btn {mod}" href="{esc(href)}"{rel}>{text}</a>'


def arrow(text, href, mod="", external=False, back=False):
    rel = ' rel="noopener"' if external else ""
    inner = f"{BACK}<span>{text}</span>" if back else f"<span>{text}</span>{ARROW}"
    return f'<a class="arrow {mod}" href="{esc(href)}"{rel}>{inner}</a>'


def card(ctx, serial, title, *, youtube_id="", dim=False, nxt=False):
    """The video title card: mark, wordmark, hairline, the job, serial. With a video id it becomes a click-to-load player;
    without one it is decoration beside a real heading, so it is hidden from assistive technology."""
    serial, title, video = esc(serial), esc(title), esc(youtube_id)
    mods = (" card--dim" if dim else "") + (" card--next" if nxt else "")
    data = f' data-youtube="{video}" data-title="{serial}: {title}"' if youtube_id else ""
    hidden = "" if youtube_id else ' aria-hidden="true"'
    play = ""
    if youtube_id:
        play = (f'<a class="card__play" href="https://www.youtube.com/watch?v={video}" rel="noopener" '
                f'aria-label="Play {serial}: {title}"><svg width="18" height="20" viewBox="0 0 18 20" aria-hidden="true">'
                f'<path d="M2 1l15 9-15 9z" fill="#0e1116"/></svg></a>')
    return (f'<div class="card{mods}"{data}><div class="card__in"{hidden}><img src="{ctx.to("img/mark-plate.svg")}" alt="" width="150" height="150">'
            f'<div class="card__word">The Electron Plumber</div><div class="card__rule"></div>'
            f'<div class="card__title">{title}</div><div class="card__serial">{serial}</div></div>{play}</div>')


def row(label, body, mod="", rail=None):
    """A spec-sheet row: mono label in the left rail, content to its right."""
    rail_html = rail if rail is not None else (kicker(label) if label else "")
    return (f'<section class="row {mod}"><div class="inner"><div class="row__rail">{rail_html}</div>'
            f'<div class="row__body">{body}</div></div></section>')


# ---------------------------------------------------------------- shell
def header(ctx, active):
    links = "".join(
        f'<a href="{ctx.to(href)}"{" aria-current=" + chr(34) + "page" + chr(34) if name == active else ""}>{name}</a>'
        for name, href in NAV)
    return (f'<header class="site-header"><div class="inner">'
            f'<a class="brand" href="{ctx.to()}"><img src="{ctx.to("img/mark-small.svg")}" alt="" width="40" height="40">'
            f'<span>The Electron Plumber</span></a>'
            f'<button class="nav-toggle" type="button" aria-expanded="false" aria-controls="nav" aria-label="Menu">'
            f'<svg width="22" height="16" viewBox="0 0 22 16" fill="none" aria-hidden="true"><path d="M0 1h22M0 8h22M0 15h22" stroke="currentColor" stroke-width="1.6"/></svg></button>'
            f'<nav class="nav" id="nav" aria-label="Main">{links}{btn("Subscribe", ctx.sub_url, "btn--sm", external=True)}</nav>'
            f'</div></header>')


def footer(ctx):
    s = ctx.site

    def column(label, text, href, external=True):
        rel = ' rel="noopener"' if external else ""
        return f'<div class="footer__col">{kicker(label, "kicker--sm")}<a href="{esc(href)}"{rel}>{text}</a></div>'

    strip = lambda u: u.replace("https://", "").replace("www.", "")  # noqa: E731
    cols = (column("Notes", strip(s["notes_repo"]), s["notes_repo"]) + column("Watch", strip(s["youtube"]), s["youtube"])
            + column("Code", strip(s["core_repo"]), s["core_repo"])
            + column("Contact", "Report an error, or get in touch", ctx.to("about/") + "#contact", external=False))
    legal = "".join(mono(t) for t in ("Views my own.", "Episode notes: CC BY-NC-ND 4.0", "Research code: Apache-2.0",
                                      f"&copy; 2026 {esc(s['author'])}"))
    return (f'<footer class="site-footer"><div class="inner"><div class="footer__plate">'
            f'<img src="{ctx.to("img/mark-plate.svg")}" alt="" width="104" height="104">'
            f'<div><div class="footer__title">The Electron Plumber</div><div class="footer__tag">{esc(s["tagline"])}</div></div></div>'
            f'<hr class="rule"><div class="grid grid--4">{cols}</div><div class="footer__legal">{legal}</div></div></footer>')


def subscribe(ctx):
    s = ctx.site
    if s.get("newsletter_action"):
        body = (f'<h2 class="h2 h2--sm">New episodes, notes, and corrections.</h2>'
                f'<p class="small g12">One email when an episode publishes. Nothing else.</p>'
                f'<form class="subscribe-form g32" action="{esc(s["newsletter_action"])}" method="post">'
                f'<div class="field"><label for="sub-email">Email address</label>'
                f'<input id="sub-email" name="email" type="email" autocomplete="email" placeholder="you@example.com" required></div>'
                f'<button class="btn" type="submit">Subscribe</button></form>'
                f'<div class="g16">{arrow("Or subscribe on YouTube", ctx.sub_url, external=True)}</div>')
    else:
        body = (f'<h2 class="h2 h2--sm">New episodes, notes, and corrections.</h2>'
                f'<p class="small g12">Episodes publish on YouTube. Notes and standing corrections publish on GitHub.</p>'
                f'<div class="cluster cluster--stack g32">{btn("Subscribe on YouTube", ctx.sub_url, external=True)}'
                f'{arrow("Watch the notes repo", s["notes_repo"], external=True)}</div>')
    return row("Subscribe", body, "row--panel row--tight")


def page(ctx, *, title, description, body, active=None, arc=None, noindex=False):
    s = ctx.site
    url = s["url"].rstrip("/") + "/" + ctx.path
    full_title = title if title == s["title"] else f"{title} | {s['title']}"
    robots = '<meta name="robots" content="noindex">' if noindex else ""
    arc_attr = f' data-arc="{arc}"' if arc else ""
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(full_title)}</title>
<meta name="description" content="{esc(description)}">
{robots}<link rel="canonical" href="{esc(url)}">
<meta name="theme-color" content="#0e1116">
<meta name="color-scheme" content="dark">
<meta property="og:type" content="website">
<meta property="og:site_name" content="{esc(s['title'])}">
<meta property="og:title" content="{esc(full_title)}">
<meta property="og:description" content="{esc(description)}">
<meta property="og:url" content="{esc(url)}">
<meta property="og:image" content="{esc(s['url'].rstrip('/'))}/img/social-share.png">
<meta name="twitter:card" content="summary_large_image">
<link rel="icon" href="{ctx.to('favicon.svg')}" type="image/svg+xml">
<link rel="icon" href="{ctx.to('favicon.png')}" sizes="144x144" type="image/png">
<link rel="apple-touch-icon" href="{ctx.to('apple-touch-icon.png')}">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="{FONTS}">
<link rel="stylesheet" href="{ctx.asset('css/site.css')}">
</head>
<body{arc_attr}>
<a class="skip" href="#main">Skip to content</a>
{header(ctx, active)}
<main id="main">
{body}
</main>
{footer(ctx)}
<script src="{ctx.asset('js/site.js')}" defer></script>
</body>
</html>
"""
