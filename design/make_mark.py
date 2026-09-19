"""Web cuts of the channel mark (Smith chart + flat (2,3) trefoil).

    python3 design/make_mark.py     (needs matplotlib)

Writes the SVG and PNG sources into design/mark/, and the favicons into static/.

Geometry:
rim |G|=1, real axis, r=1 circle (centre 1/2, radius 1/2), x=+-1 arcs
(centres 1+-j, radius 1), torus shadow |G|=(R-r)/(R+r)=1/3, and the trefoil
rho(t) = (R + r cos 3t)/(R + r), theta = 2t with R=2/3, r=1/3.
Stroke widths are given as stroke / radius, so every cut scales cleanly.
"""
import math
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Arc, Circle

SKY, ORANGE, DARK = "#56B4E9", "#E69F00", "#0e1116"
OUT = Path(__file__).resolve().parent / "mark"
STATIC = Path(__file__).resolve().parent.parent / "static"
R_MAJ, R_MIN = 2.0 / 3.0, 1.0 / 3.0

# name: (rim, axis, inner, hole, trefoil) as stroke / radius
CUTS = {
    "hero":  (0.01946, 0.01362, 0.01654, 0.01946, 0.02627),  # MARK_HERO 3.6 @ 1.85
    "plate": (0.03889, 0.02722, 0.03306, 0.03889, 0.05250),  # MARK 2.8 @ 0.72
    "small": (0.06500, 0.04800, 0.05600, 0.06500, 0.08200),  # web header, 36-48 px
}


def trefoil(n=480):
    pts = []
    for i in range(n):
        t = 2 * math.pi * i / n
        rho = (R_MAJ + R_MIN * math.cos(3 * t)) / (R_MAJ + R_MIN)
        pts.append((rho * math.cos(2 * t), rho * math.sin(2 * t)))
    return pts


def svg(name, strokes, simple=False):
    rim, axis, inner, hole, tre = strokes
    pad = 1 + tre
    d = "M" + " L".join(f"{x:.4f} {-y:.4f}" for x, y in trefoil(360)) + " Z"
    chart = [f'<circle cx="0" cy="0" r="1" stroke="{SKY}" stroke-width="{rim}"></circle>']
    if not simple:
        chart += [
            f'<line x1="-1" y1="0" x2="1" y2="0" stroke="{SKY}" stroke-width="{axis}"></line>',
            f'<circle cx="0.5" cy="0" r="0.5" stroke="{SKY}" stroke-width="{inner}"></circle>',
            f'<path d="M 1 0 A 1 1 0 0 1 0 -1" stroke="{SKY}" stroke-width="{inner}"></path>',
            f'<path d="M 1 0 A 1 1 0 0 0 0 1" stroke="{SKY}" stroke-width="{inner}"></path>',
        ]
    chart.append(f'<circle cx="0" cy="0" r="{1/3:.5f}" stroke="{SKY}" stroke-width="{hole}"></circle>')
    body = "\n  ".join(chart + [
        f'<path d="{d}" stroke="{ORANGE}" stroke-width="{tre}" stroke-linejoin="round"></path>'
    ])
    text = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{-pad:.4f} {-pad:.4f} {2*pad:.4f} {2*pad:.4f}" '
            f'fill="none" role="img" aria-label="The Electron Plumber mark">\n  {body}\n</svg>\n')
    (OUT / f"mark-{name}.svg").write_text(text)


def png(name, strokes, px, simple=False, bg=None, inset=1.0):
    rim, axis, inner, hole, tre = strokes
    pad = (1 + tre) / inset
    fig = plt.figure(figsize=(px / 100, px / 100), dpi=100)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(-pad, pad); ax.set_ylim(-pad, pad); ax.set_aspect("equal"); ax.axis("off")
    if bg:
        fig.patch.set_facecolor(bg)
    k = (px / (2 * pad)) * 72 / 100  # stroke ratio -> points
    ax.add_patch(Circle((0, 0), 1, fill=False, ec=SKY, lw=rim * k))
    if not simple:
        ax.plot([-1, 1], [0, 0], color=SKY, lw=axis * k, solid_capstyle="butt")
        ax.add_patch(Circle((0.5, 0), 0.5, fill=False, ec=SKY, lw=inner * k))
        ax.add_patch(Arc((1, 1), 2, 2, theta1=180, theta2=270, ec=SKY, lw=inner * k))
        ax.add_patch(Arc((1, -1), 2, 2, theta1=90, theta2=180, ec=SKY, lw=inner * k))
    ax.add_patch(Circle((0, 0), 1 / 3, fill=False, ec=SKY, lw=hole * k))
    pts = trefoil(720); pts.append(pts[0])
    ax.plot([p[0] for p in pts], [p[1] for p in pts], color=ORANGE, lw=tre * k,
            solid_joinstyle="round", solid_capstyle="round")
    fig.savefig(OUT / "png" / f"{name}.png", transparent=bg is None, facecolor=bg or "none")
    plt.close(fig)


for cut, s in CUTS.items():
    svg(cut, s)
svg("favicon-simple", (0.085, 0, 0, 0.085, 0.11), simple=True)

png("mark-hero-1600", CUTS["hero"], 1600)
png("mark-plate-800", CUTS["plate"], 800)
png("logo-header-mark-240", CUTS["small"], 240)
png("favicon-candidate-A-full-512", CUTS["small"], 512, bg=DARK, inset=0.86)
png("favicon-candidate-B-simple-512", (0.085, 0, 0, 0.085, 0.11), 512, simple=True, bg=DARK, inset=0.86)
print("ok")


# --- Banner cut: uniform stroke + house-dark halo (infill : extra = 2 : 1) ---
def halo_svg(name="banner-halo", s=0.055, ratio=0.5):
    pad = 1 + s * (1 + ratio)
    d = "M" + " L".join(f"{x:.4f} {-y:.4f}" for x, y in trefoil(360)) + " Z"
    shapes = [
        ('<circle cx="0" cy="0" r="1" {a}></circle>', SKY),
        ('<line x1="-1" y1="0" x2="1" y2="0" {a}></line>', SKY),
        ('<circle cx="0.5" cy="0" r="0.5" {a}></circle>', SKY),
        ('<path d="M 1 0 A 1 1 0 0 1 0 -1" {a}></path>', SKY),
        ('<path d="M 1 0 A 1 1 0 0 0 0 1" {a}></path>', SKY),
        (f'<circle cx="0" cy="0" r="{1/3:.5f}" {{a}}></circle>', SKY),
        (f'<path d="{d}" stroke-linejoin="round" {{a}}></path>', ORANGE),
    ]
    rows = []
    for tpl, col in shapes:  # each stroke: dark underlay first, then the ink (Manim background stroke order)
        rows.append(tpl.format(a=f'stroke="{DARK}" stroke-width="{s * (1 + ratio):.4f}"'))
        rows.append(tpl.format(a=f'stroke="{col}" stroke-width="{s}"'))
    text = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{-pad:.4f} {-pad:.4f} {2*pad:.4f} {2*pad:.4f}" '
            f'fill="none" role="img" aria-label="The Electron Plumber mark">\n  ' + "\n  ".join(rows) + "\n</svg>\n")
    (OUT / f"mark-{name}.svg").write_text(text)


def halo_png(name="mark-banner-halo-1200", px=1200, s=0.055, ratio=0.5):
    pad = 1 + s * (1 + ratio)
    fig = plt.figure(figsize=(px / 100, px / 100), dpi=100)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(-pad, pad); ax.set_ylim(-pad, pad); ax.set_aspect("equal"); ax.axis("off")
    k = (px / (2 * pad)) * 72 / 100
    pts = trefoil(720); pts.append(pts[0])
    z = 0
    def both(draw):
        nonlocal z
        for col, w in ((DARK, s * (1 + ratio)), (None, s)):
            z += 1
            draw(col, w * k, z)
    both(lambda c, w, z: ax.add_patch(Circle((0, 0), 1, fill=False, ec=c or SKY, lw=w, zorder=z)))
    both(lambda c, w, z: ax.plot([-1, 1], [0, 0], color=c or SKY, lw=w, solid_capstyle="butt", zorder=z))
    both(lambda c, w, z: ax.add_patch(Circle((0.5, 0), 0.5, fill=False, ec=c or SKY, lw=w, zorder=z)))
    both(lambda c, w, z: ax.add_patch(Arc((1, 1), 2, 2, theta1=180, theta2=270, ec=c or SKY, lw=w, zorder=z)))
    both(lambda c, w, z: ax.add_patch(Arc((1, -1), 2, 2, theta1=90, theta2=180, ec=c or SKY, lw=w, zorder=z)))
    both(lambda c, w, z: ax.add_patch(Circle((0, 0), 1 / 3, fill=False, ec=c or SKY, lw=w, zorder=z)))
    both(lambda c, w, z: ax.plot([p[0] for p in pts], [p[1] for p in pts], color=c or ORANGE, lw=w,
                                 solid_joinstyle="round", solid_capstyle="round", zorder=z))
    fig.savefig(OUT / "png" / f"{name}.png", transparent=True, facecolor="none")
    plt.close(fig)


halo_svg()
halo_png()
print("halo ok")


# --- Small PNG exports of the favicon candidates ---
png("favicon-candidate-A-full-144", CUTS["small"], 144, bg=DARK, inset=0.86)
png("favicon-candidate-B-simple-144", (0.085, 0, 0, 0.085, 0.11), 144, simple=True, bg=DARK, inset=0.86)
print("favicons ok")


# --- Site favicons: the simplified cut on a house-dark tile, so it survives 16 px and light browser chrome ---
def favicon_svg():
    rim, _, _, hole, tre = (0.085, 0, 0, 0.085, 0.11)
    d = "M" + " L".join(f"{x:.4f} {-y:.4f}" for x, y in trefoil(240)) + " Z"
    (STATIC / "favicon.svg").write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="-1.32 -1.32 2.64 2.64" fill="none">\n'
        f'  <rect x="-1.32" y="-1.32" width="2.64" height="2.64" rx="0.5" fill="{DARK}"/>\n'
        f'  <circle cx="0" cy="0" r="1" stroke="{SKY}" stroke-width="{rim}"/>\n'
        f'  <circle cx="0" cy="0" r="{1/3:.5f}" stroke="{SKY}" stroke-width="{hole}"/>\n'
        f'  <path d="{d}" stroke="{ORANGE}" stroke-width="{tre}" stroke-linejoin="round"/>\n</svg>\n')


def static_png(name, px):
    png(name, (0.085, 0, 0, 0.085, 0.11), px, simple=True, bg=DARK, inset=0.84)
    (OUT / "png" / f"{name}.png").replace(STATIC / f"{name}.png")


favicon_svg()
static_png("favicon", 144)
static_png("apple-touch-icon", 180)
for cut in ("hero", "plate", "small", "banner-halo"):
    (STATIC / "img" / f"mark-{cut}.svg").write_text((OUT / f"mark-{cut}.svg").read_text())
print("site icons ok")
