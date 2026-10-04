#!/usr/bin/env python3
"""Make the site's derived assets: the subset web fonts and the WebP/AVIF copies of the raster images.

    python3 tools/make_assets.py              (needs Pillow 11.3 or later, fontTools and brotli; fonts need network)
    python3 tools/make_assets.py --images     images only, no download
    python3 tools/make_assets.py --fonts      fonts only

Fonts. Downloads IBM Plex Mono and Source Serif 4 from google/fonts at a pinned commit, checks each file's SHA-256,
subsets them to Latin, Greek, punctuation, arrows and math operators, and writes WOFF2 files to static/fonts/.
Both families are under the SIL Open Font License 1.1 with a Reserved Font Name ("Plex", "Source"), and a subset is a
Modified Version, so the copies are renamed EP Mono and EP Serif. The roman serif stays variable in weight (400-700)
and in optical size from 20 up, so headings keep their display cut (text below 20px gets the 20 cut); the italic is a
static 400 at optical size 20. static/fonts/OFL.txt carries both licenses.

Images. Reads the tracked masters static/img/field-bed.png and static/img/portrait.jpg and writes AVIF and WebP copies
next to them: the hero at full size, the portrait at each width in sitegen.pages.PORTRAIT_WIDTHS. No metadata is
written. The masters stay: they are the fallback for browsers without AVIF or WebP.

Every output here is overwritten in place. Review the diff before committing.
"""
import argparse
import hashlib
import io
import sys
import tempfile
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from sitegen.pages import HERO, PORTRAIT, PORTRAIT_WIDTHS  # noqa: E402

STATIC = ROOT / "static"
FONTS_OUT = STATIC / "fonts"

GOOGLE_FONTS = "https://raw.githubusercontent.com/google/fonts/9710da1eacb3be272583c3224dcb70f9da6eadbb/ofl/"
SOURCES = {
    "serif": ("sourceserif4/SourceSerif4%5Bopsz,wght%5D.ttf", "97b2d4da6e3cb494b5a1e66ae176914d852ccabef49e0c02c0df25f3e39aca0b"),
    "serif-italic": ("sourceserif4/SourceSerif4-Italic%5Bopsz,wght%5D.ttf",
                     "15fbc7e4679489a501998c3669272637a6646388ef7e4bd77eebb5bf967a1f42"),
    "serif-ofl": ("sourceserif4/OFL.txt", "5f94c3fd3a23131a417ab5a0c8452de57e70c3cfb9f604d88241f7065ebf9fd9"),
    "mono-400": ("ibmplexmono/IBMPlexMono-Regular.ttf", "6a3412f058c7d8dfd9170c41e85ade48e5156ecb89356110ca57a0a27734af46"),
    "mono-500": ("ibmplexmono/IBMPlexMono-Medium.ttf", "a9b4c49bb299e05b5f6c481e7fb5e78943d2793249a0c8874ab574a2d1ea6755"),
    "mono-600": ("ibmplexmono/IBMPlexMono-SemiBold.ttf", "d3c38e55c78f5b0f28009fddba4834ec503278936a5986032424c9bd2d23aa46"),
    "mono-ofl": ("ibmplexmono/OFL.txt", "7e6b2818edbd8f6a01ae80641cc8f16a51080d08fb4e532be3a0b6f74adb07da"),
}
# output file: (source, axis limits for the variable serif or None)
FONTS = {
    "ep-serif.woff2": ("serif", {"wght": (400, 700), "opsz": (20, 60)}),
    "ep-serif-italic.woff2": ("serif-italic", {"wght": 400, "opsz": 20}),
    "ep-mono-400.woff2": ("mono-400", None),
    "ep-mono-500.woff2": ("mono-500", None),
    "ep-mono-600.woff2": ("mono-600", None),
}
# Longest first, so the spaced family name is replaced before its PostScript form could match inside it.
RENAME = (("Source Serif 4", "EP Serif"), ("SourceSerif4", "EPSerif"), ("IBM Plex Mono", "EP Mono"), ("IBMPlexMono", "EPMono"))
RESERVED = ("Plex", "Source")
# name IDs that keep the upstream wording: copyright, trademark, license description, license URL.
# Every other record, the description (10) included, must be free of a Reserved Font Name.
KEEP_NAME_IDS = {0, 7, 13, 14}
DESCRIPTION = "Subset for electron-plumber.com, modified from the original under the SIL Open Font License 1.1."

UNICODES = sorted({*range(0x20, 0x7F), *range(0xA0, 0x180),  # Basic Latin, Latin-1, Latin Extended-A
                   *range(0x370, 0x400),                      # Greek
                   *range(0x2000, 0x20A0),                    # punctuation, super- and subscripts
                   0x20AC, *range(0x2100, 0x2150),            # euro, letterlike symbols
                   *range(0x2190, 0x2300),                    # arrows, math operators
                   0xFEFF, 0xFFFD})

AVIF_QUALITY, WEBP_QUALITY = 60, 80


def fetch(key: str, cache: Path) -> Path:
    name, sha = SOURCES[key]
    path = cache / key
    if not path.is_file():
        with urllib.request.urlopen(GOOGLE_FONTS + name, timeout=60) as response:
            path.write_bytes(response.read())
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    if digest != sha:
        sys.exit(f"{name}: SHA-256 {digest} does not match the pinned {sha}")
    return path


def rename(font):
    table = font["name"]
    table.removeNames(nameID=10)
    for record in table.names:
        if record.nameID in KEEP_NAME_IDS:
            continue
        text = record.toUnicode()
        for old, new in RENAME:
            text = text.replace(old, new)
        record.string = text
    table.setName(DESCRIPTION, 10, 3, 1, 0x409)
    left = [(r.nameID, r.toUnicode()) for r in table.names
            if r.nameID not in KEEP_NAME_IDS and any(word in r.toUnicode() for word in RESERVED)]
    if left:
        sys.exit(f"a Reserved Font Name survived the rename: {left}")


def make_font(source: Path, limits) -> bytes:
    from fontTools import subset
    from fontTools.ttLib import TTFont
    from fontTools.varLib import instancer

    font = TTFont(source, recalcTimestamp=False)
    options = subset.Options()
    options.notdef_outline = True
    options.hinting = False
    options.desubroutinize = True
    options.name_IDs = ["*"]
    subsetter = subset.Subsetter(options)
    subsetter.populate(unicodes=UNICODES)
    subsetter.subset(font)
    if limits:
        font = instancer.instantiateVariableFont(font, limits)
    rename(font)
    font.flavor = "woff2"
    out = io.BytesIO()
    font.save(out)
    return out.getvalue()


def fonts():
    FONTS_OUT.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        cache = Path(tmp)
        for out, (key, limits) in FONTS.items():
            data = make_font(fetch(key, cache), limits)
            (FONTS_OUT / out).write_bytes(data)
            print(f"static/fonts/{out}: {len(data):,} bytes")
        notice = ("EP Serif and EP Mono are Modified Versions of Source Serif 4 and IBM Plex Mono: subset and renamed,\n"
                  "as the SIL Open Font License 1.1 requires for a font with a Reserved Font Name. Both are licensed\n"
                  "under the SIL Open Font License 1.1, reproduced below with each upstream copyright notice.\n"
                  "Made by tools/make_assets.py from github.com/google/fonts at a pinned commit.\n")
        licenses = ["\n".join(line.rstrip() for line in fetch(key, cache).read_text(encoding="utf-8").strip().splitlines())
                    for key in ("serif-ofl", "mono-ofl")]
        sections = [f"{'=' * 72}\n{title}\n{'=' * 72}\n\n{text}\n"
                    for title, text in zip(("EP Serif, from Source Serif 4", "EP Mono, from IBM Plex Mono"), licenses, strict=True)]
        (FONTS_OUT / "OFL.txt").write_text(notice + "\n" + "\n".join(sections), encoding="utf-8")
        print("static/fonts/OFL.txt")


def images():
    from PIL import Image, features

    if not features.check("avif"):
        sys.exit("this Pillow has no AVIF support: install Pillow 11.3 or later")

    def save(im, stem):
        for ext, opts in (("avif", {"quality": AVIF_QUALITY, "speed": 0}), ("webp", {"quality": WEBP_QUALITY, "method": 6})):
            target = STATIC / f"{stem}.{ext}"
            im.save(target, exif=b"", **opts)
            print(f"static/{target.relative_to(STATIC).as_posix()}: {target.stat().st_size:,} bytes")

    with Image.open(STATIC / f"{HERO}.png") as hero:
        save(hero.convert("RGB"), HERO)
    with Image.open(STATIC / f"{PORTRAIT}.jpg") as portrait:
        portrait = portrait.convert("RGB")
        for width in PORTRAIT_WIDTHS:
            if width > portrait.width:
                sys.exit(f"{PORTRAIT}.jpg is {portrait.width}px wide: it cannot make a {width}px copy")
            height = round(portrait.height * width / portrait.width)
            save(portrait.resize((width, height), Image.LANCZOS), f"{PORTRAIT}-{width}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--images", action="store_true", help="images only")
    parser.add_argument("--fonts", action="store_true", help="fonts only")
    args = parser.parse_args()
    both = not (args.images or args.fonts)
    if both or args.fonts:
        fonts()
    if both or args.images:
        images()
