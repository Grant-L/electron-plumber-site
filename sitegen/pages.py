"""Page templates. Home and Episodes are driven by episode status, so nothing here claims a video exists before it does."""
from pathlib import Path

from .html import RECORDS, Ctx, arrow, badge, btn, card, esc, kicker, mono, page, row, subscribe

DECK = "We know what it <em>does</em> to a part in a trillion. Nobody knows what it <em>is</em>."
QUOTE_AUTHOR = ("&ldquo;I&rsquo;m an EE who calls myself an electron plumber. The channel is one question, pursued honestly: "
                "what is an electron?&rdquo;")
RESEARCH_HANDOFF = ("I work on a model of the vacuum. It&rsquo;s unproven. The Research page says what would kill it, "
                    "and which of its laws already lost.")
ABOUT = ("I&rsquo;m a staff electrical engineer in grid-scale energy storage. My job is finding out why real circuits "
         "fail &mdash; megawatts on the line, root cause or nothing, no partial credit. This channel points that same "
         "discipline at a question nobody can answer: what is an electron? We know what it <em>does</em> to a part in a "
         "trillion. Nobody knows what it <em>is</em>. I make three kinds of video &mdash; history, told faithfully from "
         "the original papers; speculation, labeled as speculation; and shop practice. You&rsquo;ll always know which one "
         "you&rsquo;re watching. And when I get something wrong, it goes on a public corrections ledger.")


def _portrait(ctx, mod=""):
    """The portrait is optional: drop static/img/portrait.jpg in and it appears."""
    if not (Path(ctx.site["_root"]) / "static" / "img" / "portrait.jpg").is_file():
        return ""
    return f'<img class="portrait {mod}" src="{ctx.to("img/portrait.jpg")}" alt="{esc(ctx.site["author"])}" width="400" height="500">'


def _badge(ep):
    """An episode with no arc yet (not aired) shows no badge."""
    return badge(ep.arc) if ep.arc else ""


def _next_line(ctx, ep):
    return (f'<hr class="rule rule--line g40"><div class="between g28"><div class="stack">'
            f'{kicker("Next &middot; " + ep.serial, "kicker--orange")}<div class="next__title g8">{esc(ep.title)}</div>'
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

    hero = (f'<div class="band" style="background-image: url({ctx.to("img/field-bed.png")});">'
            f'<img src="{ctx.to("img/mark-banner-halo.svg")}" width="236" height="236" '
            f'alt="The Electron Plumber mark: a Smith chart holding a trefoil curve"></div>'
            f'<div class="plate-block">{kicker("The Electron Plumber")}<hr class="rule rule--plate g20">'
            f'<h1 class="h1 h1--hero g36">What is an electron?</h1><p class="deck g24">{DECK}</p>'
            f'<div class="mono mono--sky g28">{esc(s["tagline"])}</div>{status}'
            f'<div class="cluster cluster--stack g40">{actions}</div></div>')

    def arc_col(arc, status_text, text):
        color = {"historical": "var(--sky)", "speculative": "var(--orange)", "practical": "var(--green)"}[arc]
        return (f'<div class="stack arc-col" style="--arc-c: {color};"><hr class="rule"><div class="g24">{badge(arc)}</div>'
                f'<div class="mono g20">{status_text}</div><p class="small g12">{text}</p></div>')

    orient = row("Orientation", (
        '<h2 class="h2">Three kinds of video. You&rsquo;ll always know which one you&rsquo;re watching.</h2>'
        '<div class="grid grid--3 g48">'
        + arc_col("historical", "Established record", "History, told faithfully from the original papers. "
                  "All on-camera citations live in sources.bib.")
        + arc_col("speculative", "Explicitly speculative", "Proposed physics, not established physics. The current program and its "
                  "kill criteria are on the Research page.")
        + arc_col("practical", "Demonstrated practice", "Bench work. Failure analysis on circuits rebuilt for the camera, "
                  "taken down to the physical mechanism.")
        + '</div><p class="small muted g40">Every video opens by saying which one it is.</p>'))

    if latest:
        meta = f'{kicker(latest.serial, "kicker--white")}{badge(latest.arc)}{mono(esc(latest.date) or "[DATE]")}'
        body = (f'<div class="latest"><div class="latest__card">{card(ctx, latest.serial, latest.title, youtube_id=latest.youtube_id)}</div>'
                f'<div class="stack"><div class="cluster cluster--tight">{meta}</div><h2 class="h2 g16">{esc(latest.title)}</h2>'
                f'<p class="small g16">{esc(latest.excerpt)}</p><div class="cluster g28">{btn("Watch", ctx.to(latest.url))}'
                f'{arrow("Episode notes", ctx.to(latest.url) + "#learning-goals")}</div></div></div>'
                + (_next_line(ctx, upcoming) if upcoming else ""))
        episode_row = row("Latest episode", body)
    elif upcoming:
        body = (f'<div class="latest"><div class="latest__card">{card(ctx, upcoming.serial, upcoming.title, dim=True, nxt=True)}</div>'
                f'<div class="stack"><div class="cluster cluster--tight">{kicker("Next &middot; " + upcoming.serial, "kicker--orange")}'
                f'{_badge(upcoming)}</div><h2 class="h2 g16" style="color: var(--orange);">{esc(upcoming.title)}</h2>'
                f'<div class="mono g16">In production</div>'
                f'<div class="g28">{arrow("Subscribe on YouTube", ctx.sub_url, external=True)}</div></div></div>')
        episode_row = row("Next episode", body)
    else:
        episode_row = ""

    author_row = row("About the author", (
        f'<div class="author">{_portrait(ctx)}<div class="stack"><div class="quote">{QUOTE_AUTHOR}</div>'
        f'<div class="name g28">{esc(s["author"])}</div>'
        f'<div class="mono">Staff electrical engineer, grid-scale energy storage. Views my own.</div>'
        f'<div class="g12">{arrow("About", ctx.to("about/"))}</div></div></div>'))

    def record(label, text):
        return f'<div class="stack">{kicker(label, "kicker--sm")}<p class="small g12">{text}</p></div>'

    records_row = row(RECORDS[0], (
        '<h2 class="h2">Spotted an error? Open an issue.</h2><div class="grid grid--4 g40">'
        + record("Claims", "Every on-camera commitment gets an ID and a class. Once an episode airs, its claims are frozen.")
        + record("Sources", "Every citation made on camera lives in one public BibTeX file.")
        + record("Corrections", "When I get something wrong it goes on a public ledger. Nothing is stealth-deleted.")
        + record("Notes", "A free handout for every episode: learning goals, readings, check-yourself questions.")
        + f'</div><div class="g36">{arrow("See the " + RECORDS[0].lower(), ctx.to(RECORDS[1]))}</div>'))

    disclosure = row("", (f'<div class="quote quote--lg">{RESEARCH_HANDOFF}</div>'
                          f'<div class="g28">{arrow("The speculative program", ctx.to("research/"), "arrow--orange")}</div>'),
                     "row--tighter", rail=badge("speculative"))

    return page(ctx, title=s["title"], active=None,
                description="One question, pursued honestly: what is an electron? History told from the original papers, "
                            "speculation labeled as speculation, and shop practice.",
                body=hero + orient + episode_row + author_row + records_row + disclosure + subscribe(ctx))


# ------------------------------------------------------------------ EPISODES
def episodes(ctx: Ctx):
    published, upcoming = ctx.published, ctx.upcoming
    head = ('<div class="page-head"><h1 class="h1 h1--page">Episodes</h1>'
            '<p class="deck deck--sm g20">Every episode is labeled &mdash; historical record, established physics, explicit speculation, or shop practice.</p></div>')

    filt = ""
    if len(published) > 1:
        chips = '<button class="chip" type="button" data-arc="all" aria-pressed="true">All</button>' + "".join(
            f'<button class="chip" type="button" data-arc="{a}" aria-pressed="false" style="--c: var(--{c});"><i></i>{n}</button>'
            for a, n, c in (("historical", "Historical", "sky"), ("speculative", "Speculative", "orange"),
                            ("practical", "Practical", "green")))
        filt = (f'<div class="filter"><div class="inner"><div class="filter__chips" role="group" aria-label="Filter by arc">{chips}</div>'
                f'<div class="mono" role="status" data-total="{len(published)}">{len(published)} published</div></div></div>')

    rows = ""
    for ep in published:
        meta = f'{kicker(ep.serial, "kicker--white")}{badge(ep.arc)}{mono(" &middot; ".join((esc(ep.date) or "[DATE]", esc(ep.runtime) or "[RUNTIME]")))}'
        rows += (f'<article class="ep-row" data-arc="{ep.arc}"><div class="inner"><div class="ep-row__card">'
                 f'<a href="{ctx.to(ep.url)}" aria-label="{esc(ep.serial)}: {esc(ep.title)}">{card(ctx, ep.serial, ep.title)}</a></div>'
                 f'<div class="stack"><div class="cluster cluster--tight">{meta}</div><h2 class="h2 h2--row g16">{esc(ep.title)}</h2>'
                 f'<p class="small g12">{esc(ep.excerpt)}</p><div class="cluster g24">{btn("Watch", ctx.to(ep.url))}'
                 f'{arrow("Episode notes", ctx.to(ep.url) + "#learning-goals")}</div></div></div></article>')
    if upcoming:
        arc_attr = f' data-arc="{upcoming.arc}"' if upcoming.arc else ""
        rows += (f'<article class="ep-row"{arc_attr}><div class="inner"><div class="ep-row__card">{card(ctx, upcoming.serial, upcoming.title, dim=True, nxt=True)}</div>'
                 f'<div class="stack"><div class="cluster cluster--tight">{kicker("Next &middot; " + upcoming.serial, "kicker--orange")}{_badge(upcoming)}</div>'
                 f'<h2 class="h2 h2--row g16" style="color: var(--orange);">{esc(upcoming.title)}</h2>'
                 + (f'<p class="small g12">{esc(upcoming.excerpt)}</p>' if upcoming.excerpt else "")
                 + '<div class="mono g20">In production</div></div></div></article>')
    if not rows:
        rows = '<div class="empty"><p class="prose">Nothing published yet.</p></div>'

    return page(ctx, title="Episodes", active="Episodes",
                description="Every episode of The Electron Plumber, with its notes, sources and corrections.",
                body=head + filt + rows + subscribe(ctx))


# ------------------------------------------------------------------ EPISODE
def episode(ctx: Ctx, ep):
    meta = " &middot; ".join((esc(ep.date) or "[DATE]", esc(ep.runtime) or "[RUNTIME]"))
    head = (f'<div class="post-head">{arrow("All episodes", ctx.to("episodes/"), back=True)}'
            f'<div class="cluster cluster--tight g28">{kicker(ep.serial, "kicker--white")}{badge(ep.arc)}{mono(meta)}</div>'
            f'<h1 class="h1 h1--page g20">{esc(ep.title)}</h1>'
            + (f'<p class="deck deck--sm g20">{esc(ep.orientation)}</p>' if ep.orientation else "") + '</div>')
    video = f'<div class="post-video">{card(ctx, ep.serial, ep.title, youtube_id=ep.youtube_id)}</div>'

    blocks, have = "", set()
    for title, body in ep.sections:
        anchor = "-".join(title.lower().split())
        have.add(anchor)
        blocks += f'<section class="block" id="{esc(anchor)}"><h2>{esc(title)}</h2>{body}</section>'
    if "corrections" not in have:
        blocks += ('<section class="block" id="corrections"><h2>Corrections</h2><p class="white">None to date.</p>'
                   '<p>Standing corrections for all episodes live on the errata ledger. Spotted an error? Open an issue.</p></section>')
    report = f'<div class="g8">{arrow("Report an error", ctx.site["notes_repo"] + "/issues", external=True)}</div>'
    article = f'<article class="article">{blocks}{report}<div class="g48"></div></article>'

    nxt = ""
    if ctx.upcoming:
        up = ctx.upcoming
        nxt = (f'<div class="next-band"><a href="{ctx.to("episodes/")}"><div class="stack">{kicker("Next &middot; " + up.serial, "kicker--orange")}'
               f'<div class="next-band__title g12">{esc(up.title)}</div></div>{_badge(up)}</a></div>')

    return page(ctx, title=f"{ep.serial}: {ep.title}", active="Episodes", arc=ep.arc or None, noindex=ep.draft,
                description=ep.excerpt or f"{ep.serial} of The Electron Plumber.", body=head + video + article + nxt)


# ------------------------------------------------------------------ RESEARCH
def research(ctx: Ctx):
    core = ctx.site["core_repo"]
    letter = core + "/blob/main/papers/2026_birefringence_letter/sve_vacuum_birefringence_letter.pdf"
    head = (f'<div class="page-head" style="padding-top: 80px; padding-bottom: 72px;"><div class="notice">{badge("speculative")}'
            f'<div class="mono mono--body">Explicitly speculative. New, unproven propositions.</div></div>'
            f'<h1 class="h1 g28">Applied Vacuum Engineering</h1>'
            f'<p class="deck g16" style="font-size: clamp(19px, 1.8vw, 26px);">A falsifiable impedance model of the vacuum.</p>'
            f'<div class="mono g28">Apache-2.0 &nbsp;&middot;&nbsp; 1 armed forward falsifier &nbsp;&middot;&nbsp; '
            f'44 consistency-class entries</div></div>')

    wager = row("The wager", (
        '<p class="prose prose--lg">Applied Vacuum Engineering is a falsification-first <em>engineering</em> model of the vacuum. '
        'It treats empty space not as a geometric abstraction but as a real, saturable LC lattice: a transmission-line medium with a '
        'finite inductive density (&mu;&#8320;), a finite capacitive density (&epsilon;&#8320;), a characteristic impedance '
        'Z&#8320; = &radic;(&mu;&#8320;/&epsilon;&#8320;) &asymp; 377 &Omega;, and a hard yield ceiling above which it snaps.</p>'
        '<p class="prose prose--lg g24">The wager is that the electron-plumber habit, reading electrical phenomena as mechanical '
        'stress in one medium, is the correct disciplinary frame. The point of the work is to find out where that wager breaks.</p>'),
        "row--tight")

    def fcard(color, status, title, text, link_text, href, mod):
        return (f'<div class="fcard" style="--c: var(--{color});"><div class="fcard__top"></div><div class="fcard__body">'
                f'{kicker(status, "kicker--" + color)}<h3 class="h3 g16">{title}</h3><p class="small g16">{text}</p>'
                f'{arrow(link_text, href, mod, external=True)}</div></div>')

    die = row("Experimental falsification", (
        '<h2 class="h2">What kills the framework.</h2><div class="grid grid--2 g40">'
        + fcard("vermillion", "Excluded by data", "The electrostatic gauntlet",
                "The framework put its own continuum static-field law on trial against muonic hydrogen, the sharpest available "
                "probe of the atom&rsquo;s near-nucleus field. The law lost. Extrapolated into the atom&rsquo;s static sector, it "
                "overshoots the measured Lamb-shift window, 202.3706(23) meV, by about 2&times;10<sup>4</sup>. A completed "
                "falsification, banked on the record.", "Read the adjudication", core + "#experimental-falsification", "arrow--vermillion")
        + fcard("orange", "Armed &middot; pre-registered", "Vacuum birefringence",
                "A tree-level X-ray vacuum birefringence, a field-independent factor 3.75&pi;/&alpha;<sup>2</sup> &asymp; "
                "2.2&times;10<sup>5</sup> above one-loop QED. The kill criterion was committed before any data and timestamped on "
                "the Bitcoin blockchain: a 5&sigma; pump-on null, P<sub>flip</sub> &lt; 10<sup>&minus;8</sup> at a pump intensity of "
                "10<sup>18</sup> W/cm<sup>2</sup> or more, falsifies the model&rsquo;s electric sector. No rescue.",
                "Read the Letter (PDF)", letter, "arrow--orange")
        + '</div>'), "row--tight")

    def axiom(n, name, text):
        return f'<div class="trow"><div class="trow__n">{n}</div><div class="trow__name">{name}</div><div class="trow__text">{text}</div></div>'

    axioms = row("Four axioms", (
        axiom("01", "Impedance", "The vacuum is an LC resonant network with Z&#8320; = &radic;(&mu;&#8320;/&epsilon;&#8320;).")
        + axiom("02", "Topo-kinematic isomorphism", "Charge is a geometric dislocation: [Q] &equiv; [L]. Topology encodes electromagnetism.")
        + axiom("03", "Gravity", "G sets the Machian boundary impedance.")
        + axiom("04", "Saturation", "S(A) = &radic;(1 &minus; (A/A<sub>yield</sub>)<sup>2</sup>): a universal yield kernel bounding all LC modes.")),
        "row--tight")

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
              core + "/tree/main/claim-prereg-ots")), "row--tight")

    return page(ctx, title="Research", active="Research", arc="speculative",
                description="Applied Vacuum Engineering: a falsifiable impedance model of the vacuum. Explicitly speculative, "
                            "with its kill criteria stated up front.",
                body=head + wager + die + axioms + formval + read)


# ------------------------------------------------------------------ RECORDS (labels, claim format, ledger, sources)
def records(ctx: Ctx):
    notes = ctx.site["notes_repo"]
    head = (f'<div class="page-head" style="padding-bottom: 72px;">{kicker(RECORDS[0])}<h1 class="h1 g16">Spotted an error? Open an issue.</h1>'
            f'<p class="deck g20">Corrections are part of the product here, not an embarrassment.</p></div>')

    def label_row(arc, status, text):
        return (f'<div class="trow trow--center"><div class="trow__badge">{badge(arc)}</div>'
                f'<div class="trow__status mono">{status}</div><div class="trow__text">{text}</div></div>')

    labels = row("The labels", (
        '<h2 class="h2">Every episode is labeled.</h2><div class="g36">'
        + label_row("historical", "Established record", "Physics as it was published at the time. Every source is listed in sources.bib.")
        + label_row("speculative", "Explicitly speculative", "Not established physics. The kill criteria are on the Research page.")
        + label_row("practical", "Demonstrated practice", "Troubleshooting method and the physics of failure, on recreated circuits.")
        + '</div><p class="prose g36">A label here is a field in a file, and the build reads it. Every on-camera commitment is a tagged line in the '
          'episode outline, and the build fails if a speculative claim appears in a historical episode, or if a factual claim reaches '
          'air without a resolved source.</p>'), "row--tight")

    def legend(term, text):
        return f'<div class="legend"><div class="legend__term">{term}</div><p>{text}</p></div>'

    claim = row("A claim, tracked", (
        '<h2 class="h2">Every on-camera commitment has an ID.</h2>'
        '<div class="claim g28"><i>CLAIM</i> <b>ep0NN-c03</b> FACT topic=example-topic src=author1900key</div>'
        '<div class="grid grid--4 g24">'
        + legend("ep0NN-c03", "The ID says where the claim first aired. Later episodes reference it; they never re-mint it.")
        + legend("FACT", "The class of claim, checked against the episode&rsquo;s label by the build.")
        + legend("topic=", "A collision key. Two live claims on one topic get looked at by a human.")
        + legend("src=", "A key into the public sources file.")
        + '</div><p class="prose g32">A published episode is immutable. The register is the living truth; each episode is an '
          'as-aired freeze of what was committed to on camera. Drift between them is the product, not a bug to hide: it drives '
          'the corrections ledger.</p>'), "row--tight")

    ledger = row("Corrections", (
        '<h2 class="h2">The ledger.</h2><div class="g28"><div class="ledger__head"><div>Claim</div><div>As aired</div>'
        '<div>What is true now</div><div>Vehicle</div></div><div class="ledger__empty">None to date.</div></div>'
        '<p class="prose g32">Correction vehicles, cheapest first: a description edit, a pinned comment, a corrections corner in a '
        'later episode, an erratum short. Never a stealth delete.</p>'
        f'<div class="g28">{btn("Report an error", notes + "/issues", "btn--secondary", external=True)}</div>'), "row--tight")

    def lic(label, text, link_text, href):
        return (f'<div class="stack">{kicker(label, "kicker--sm")}<p class="small g12">{text}</p>'
                f'<div class="g12">{arrow(link_text, href, external=True)}</div></div>')

    sources = row("Sources and licenses", (
        '<div class="grid grid--3">'
        + lic("Sources", "All on-camera citations live in one BibTeX file, free to reuse.", "sources.bib", notes + "/blob/main/sources.bib")
        + lic("Episode notes", "CC BY-NC-ND 4.0: share with attribution; no commercial use; no derivatives.", "The notes repo", notes)
        + lic("Research code", "Apache-2.0.", "AVE-Core on GitHub", ctx.site["core_repo"]) + '</div>'), "row--tight")

    return page(ctx, title=RECORDS[0], active=RECORDS[0],
                description="Corrections are part of the product here, not an embarrassment. Labels, claim format, the ledger, sources and licenses.",
                body=head + labels + claim + ledger + sources)


# ------------------------------------------------------------------ ABOUT
def about(ctx: Ctx):
    s = ctx.site
    head = (f'<div class="about-head">{_portrait(ctx, "portrait--lg")}<div class="stack">{kicker("About")}'
            f'<h1 class="h1 h1--page g16">{esc(s["author"])}</h1><div class="tagline g20">{esc(s["tagline"])}</div>'
            f'<p class="prose g32">{ABOUT}</p><div class="mono g24">Views my own.</div></div></div>')

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

    return page(ctx, title="About", active="About",
                description=f"{s['author']} is a staff electrical engineer in grid-scale energy storage, asking what an electron is. Views my own.",
                body=head + contact)


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
