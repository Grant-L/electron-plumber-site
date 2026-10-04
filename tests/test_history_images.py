"""One image per History event: the [event.image] table, its file checks, its export and its rendering."""
import re
import struct
import tomllib

import pytest
from conftest import ROOT
from test_timeline import EVENT, SEED, _built_with, load, parse, render

import build
import check
from sitegen import content
from tools import export_timeline as ex

EVENT_ID = "1843-hamilton-quaternions"
FILE = f"static/img/history/{EVENT_ID}.webp"
COMMONS = "https://commons.wikimedia.org/wiki/File:Fixture_portrait.jpg"
IMAGE = {"file": FILE, "alt": "A fixture portrait, head and shoulders.", "author": "Fixture Author", "title": "Fixture portrait",
         "source_url": COMMONS, "license": "public-domain", "width": 320, "height": 400, "caption": "A fixture caption."}


def webp(width, height, kind="VP8 ", pad=0):
    """Just enough of a WebP file for its header to be read: RIFF, WEBP and the first chunk."""
    if kind == "VP8 ":
        body = b"\x00\x00\x00\x9d\x01\x2a" + struct.pack("<HH", width, height)
    elif kind == "VP8L":
        body = b"\x2f" + ((width - 1) | (height - 1) << 14).to_bytes(4, "little")
    else:
        body = b"\x00" * 4 + (width - 1).to_bytes(3, "little") + (height - 1).to_bytes(3, "little")
    chunk = kind.encode() + struct.pack("<I", len(body)) + body + b"\x00" * pad
    return b"RIFF" + struct.pack("<I", 4 + len(chunk)) + b"WEBP" + chunk


def jpeg(width, height, marker=0xC0):
    app0 = b"\xff\xe0" + struct.pack(">H", 16) + b"JFIF\x00" + b"\x00" * 9
    sof = bytes([0xFF, marker]) + struct.pack(">HBHH", 17, 8, height, width) + b"\x03" + b"\x00" * 9
    return b"\xff\xd8" + app0 + sof + b"\xff\xd9"


def svg(width, height):
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}"><rect width="1" height="1"/></svg>'.encode()


def table(image):
    def value(v):
        return str(v) if isinstance(v, int) else '"' + v.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n") + '"'
    return "\n  [event.image]\n" + "".join(f"  {k} = {value(v)}\n" for k, v in image.items())


def with_image(text=EVENT, **change):
    image = {k: v for k, v in {**IMAGE, **change}.items() if v is not None}
    return text.replace("\n  [[event.source]]", table(image) + "\n  [[event.source]]", 1)


def put(root, name, data):
    folder = root / "static" / "img" / "history"
    folder.mkdir(parents=True, exist_ok=True)
    (folder / name).write_bytes(data)


@pytest.fixture
def image_root(timeline_root):
    put(timeline_root, f"{EVENT_ID}.webp", webp(320, 400))
    return timeline_root


# ------------------------------------------------------------------ loading
def test_an_event_with_an_image_loads(image_root):
    [ev] = load(image_root, with_image())
    assert ev.image == content.Image(**IMAGE)


def test_an_event_without_an_image_has_none(timeline_root):
    assert load(timeline_root, EVENT)[0].image is None


@pytest.mark.parametrize("change, message", [
    ({"alt": None}, "missing 1 required positional argument: 'alt'"),
    ({"alt": "x" * 151}, "alt must be one line of 1 to 150 characters"),
    ({"alt": ""}, "alt must be one line of 1 to 150 characters"),
    ({"alt": "Two\nlines."}, "alt must be one line of 1 to 150 characters"),
    ({"alt": "A <b> portrait."}, "alt must be one line of 1 to 150 characters"),
    ({"alt": "Fixture portrait"}, "alt must describe the picture, not repeat a title"),
    ({"alt": "Fixture title"}, "alt must describe the picture, not repeat a title"),
    ({"alt": "Photo of a man."}, "must not start with 'Image of', 'Picture of' or 'Photo of'"),
    ({"alt": "image of a man."}, "must not start with 'Image of', 'Picture of' or 'Photo of'"),
    ({"license": "cc-by-sa-4.0"}, "unknown image license 'cc-by-sa-4.0'"),
    ({"license": "no known restrictions"}, "unknown image license"),
    ({"source_url": COMMONS.replace("https://", "http://")}, "source_url must be an https://commons.wikimedia.org/wiki/File: page"),
    ({"source_url": "https://www.loc.gov/item/90713420/"}, "source_url must be an https://commons.wikimedia.org/wiki/File: page"),
    ({"source_url": None}, "source_url must be an https://commons.wikimedia.org/wiki/File: page"),
    ({"file": "static/img/1843-hamilton-quaternions.webp"}, "image file must look like"),
    ({"file": "static/img/history/1843-Hamilton.webp"}, "image file must look like"),
    ({"file": "static/img/history/1843-hamilton-quaternions.png"}, "image file must look like"),
    ({"file": "static/img/history/1843-hamilton-quaternions.svg"}, "an .svg image must be own-work"),
    ({"width": 0}, "width must be a positive integer"),
    ({"height": "400"}, "height must be a positive integer"),
    ({"caption": "x" * 141}, "caption must be one line of at most 140 characters"),
    ({"caption": "Two\nlines."}, "caption must be one line of at most 140 characters"),
    ({"caption": "An AVE figure."}, "caption must spell out the framework's name"),
    ({"title": "Portrait [TODO]"}, "title has a capitalised bracket placeholder"),
    ({"author": ""}, "author must be one line of text"),
    ({"image_checked_by": "Fixture"}, "unexpected keyword argument 'image_checked_by'"),
    ({"photographer": "Fixture"}, "unexpected keyword argument 'photographer'"),
])
def test_bad_image_data_is_refused_naming_the_event(image_root, change, message):
    with pytest.raises(SystemExit, match=rf"event {EVENT_ID}.*" + re.escape(message)):
        load(image_root, with_image(**change))


def test_a_private_term_in_the_alt_is_refused_without_repeating_it(image_root, monkeypatch):
    monkeypatch.setenv("FORBIDDEN_TERMS", "zzqx-corp")
    with pytest.raises(SystemExit) as exc:
        load(image_root, with_image(alt="A portrait for ZZQX-Corp."))
    assert EVENT_ID in str(exc.value) and "zzqx" not in str(exc.value).lower()


def test_own_work_needs_no_source_url(image_root):
    [ev] = load(image_root, with_image(license="own-work", source_url=None))
    assert ev.image.source_url == ""


def test_a_missing_file_is_refused(timeline_root):
    with pytest.raises(SystemExit, match=f"event {EVENT_ID}: image file {FILE} does not exist"):
        load(timeline_root, with_image())


def test_a_file_over_40960_bytes_is_refused(timeline_root):
    put(timeline_root, f"{EVENT_ID}.webp", webp(320, 400, pad=40_960 - len(webp(320, 400))))
    assert len((timeline_root / FILE).read_bytes()) == 40_960
    load(timeline_root, with_image())
    put(timeline_root, f"{EVENT_ID}.webp", webp(320, 400, pad=40_961 - len(webp(320, 400))))
    with pytest.raises(SystemExit, match="image file is 40961 bytes, at most 40960"):
        load(timeline_root, with_image())


@pytest.mark.parametrize("name, data, license", [
    ("1843-hamilton-quaternions.webp", webp(320, 401), "public-domain"),
    ("1843-hamilton-quaternions.webp", webp(320, 401, "VP8L"), "public-domain"),
    ("1843-hamilton-quaternions.webp", webp(320, 401, "VP8X"), "public-domain"),
    ("1843-hamilton-quaternions.jpg", jpeg(320, 401), "public-domain"),
    ("1843-hamilton-quaternions.jpg", jpeg(320, 401, 0xC2), "public-domain"),
    ("1843-hamilton-quaternions.svg", svg(320, 401), "own-work"),
])
def test_width_and_height_must_match_the_file(timeline_root, name, data, license):
    put(timeline_root, name, data)
    with pytest.raises(SystemExit, match="image width and height say 320x400, the file is 320x401"):
        load(timeline_root, with_image(file=f"static/img/history/{name}", license=license))


@pytest.mark.parametrize("data, suffix, size", [
    (webp(320, 427), ".webp", (320, 427)), (webp(320, 240, "VP8L"), ".webp", (320, 240)),
    (webp(4000, 3000, "VP8X"), ".webp", (4000, 3000)), (jpeg(320, 418), ".jpg", (320, 418)),
    (jpeg(640, 480, 0xC2), ".jpg", (640, 480)), (svg(320, 240), ".svg", (320, 240)),
    (b"not an image", ".webp", None), (b"\xff\xd8\xff\xd9", ".jpg", None), (b"<svg/>", ".svg", None),
])
def test_the_standard_library_size_readers(tmp_path, data, suffix, size):
    path = tmp_path / f"x{suffix}"
    path.write_bytes(data)
    assert content.image_size(path) == size


def test_an_unreferenced_file_in_the_folder_is_refused(image_root):
    put(image_root, "1999-unpublished.webp", webp(320, 400))
    with pytest.raises(SystemExit, match="static/img/history/1999-unpublished.webp: no event in timeline.toml uses this file"):
        load(image_root, with_image())


def test_an_unreferenced_file_is_refused_even_with_no_timeline(timeline_root):
    put(timeline_root, "1999-unpublished.webp", webp(320, 400))
    with pytest.raises(SystemExit, match="no event in timeline.toml uses this file"):
        content.load_timeline(timeline_root, [])


def test_two_events_sharing_a_file_are_refused(image_root):
    second = EVENT.replace(EVENT_ID, "1843-hamilton-second")
    with pytest.raises(SystemExit, match=f"event 1843-hamilton-second: image file {FILE} is also used by {EVENT_ID}"):
        load(image_root, with_image() + "\n" + with_image(second))


def test_the_page_cap_is_200_kb(timeline_root):
    events = re.split(r"\n(?=\[\[event\]\])", SEED)
    ids = [re.search(r'id = "([^"]+)"', e).group(1) for e in events]
    text = ""
    for i, (block, id) in enumerate(zip(events, ids, strict=True)):
        size = 40_000 if i < 5 else 2_400 + (i == 6)
        put(timeline_root, f"{id}.webp", webp(320, 400, pad=size - len(webp(320, 400))))
        text += with_image(block + "\n", file=f"static/img/history/{id}.webp", alt=f"A fixture picture for {id}.") + "\n"
    assert sum(p.stat().st_size for p in (timeline_root / "static" / "img" / "history").iterdir()) == 204_801
    with pytest.raises(SystemExit, match="images total 204801 bytes, at most 204800"):
        load(timeline_root, text)
    put(timeline_root, f"{ids[-1]}.webp", webp(320, 400, pad=2_400 - len(webp(320, 400))))
    assert len(load(timeline_root, text)) == len(ids)


def test_without_files_only_the_data_is_checked(timeline_root):
    (timeline_root / "content" / "timeline.toml").write_text(with_image(), encoding="utf-8")
    _, episodes = content.load(timeline_root)
    [ev] = content.load_timeline(timeline_root, episodes, files=False)
    assert ev.image.file == FILE
    (timeline_root / "content" / "timeline.toml").write_text(with_image(license="cc-by-sa-4.0"), encoding="utf-8")
    with pytest.raises(SystemExit, match="unknown image license"):
        content.load_timeline(timeline_root, episodes, files=False)


# ------------------------------------------------------------------ export
LINKS = "| ID | Name |\n|---|---|\n| HL-001 | fixture |\n"
GATE = {"image_checked_by": "Fixture Checker", "image_checked_date": "2026-10-03"}


def export(tmp_path, root, image):
    tracker = tmp_path / "tracker"
    tracker.mkdir(exist_ok=True)
    (tracker / "HISTORY-LINKS.md").write_text(LINKS, encoding="utf-8")
    record = 'link = "HL-001"\nhistorian = "confirmed"\npublic = true\n' + EVENT.split("\n", 1)[1]
    record = record.replace("\n  [[event.source]]", table(image).replace("[event.image]", "[confirmed.image]") + "\n  [[event.source]]")
    (tracker / "HISTORY-CONFIRMED.toml").write_text("[[confirmed]]\n" + record.replace("[[event.source]]", "[[confirmed.source]]"),
                                                     encoding="utf-8")
    out = tmp_path / "timeline.toml"
    ex.export(tracker / "HISTORY-CONFIRMED.toml", tracker / "HISTORY-LINKS.md", out, root=root)
    return out


def test_the_image_exports_through_the_allowlist_and_round_trips(tmp_path, image_root):
    out = export(tmp_path, image_root, {**GATE, **IMAGE})
    text = out.read_text(encoding="utf-8")
    assert "image_checked" not in text and "Fixture Checker" not in text and "#" not in text.split("\n", 2)[2]
    block = text[text.index("  [event.image]"):text.index("  [[event.source]]")]
    assert [line.split(" = ")[0].strip() for line in block.strip().splitlines()[1:]] == list(ex.IMAGE_FIELDS)
    assert text.index("[event.image]") < text.index("[[event.source]]")
    assert tomllib.loads(text)["event"][0]["image"] == IMAGE
    [ev] = load(image_root, text)
    assert ev.image == content.Image(**IMAGE)


def test_the_exporter_does_not_read_the_image_files(tmp_path, timeline_root):
    assert not (timeline_root / "static").exists()
    assert export(tmp_path, timeline_root, {**GATE, **IMAGE}).is_file()


def test_an_unknown_image_key_is_refused_by_the_export(tmp_path, timeline_root):
    with pytest.raises(SystemExit, match="image: unknown field 'photographer'"):
        export(tmp_path, timeline_root, {**GATE, **IMAGE, "photographer": "Fixture"})
    assert not (tmp_path / "timeline.toml").exists()


@pytest.mark.parametrize("gate", [{}, {"image_checked_by": "Fixture Checker"}, {"image_checked_date": "2026-10-03"},
                                  {"image_checked_by": "", "image_checked_date": "2026-10-03"},
                                  {"image_checked_by": "Fixture Checker", "image_checked_date": "soon"}])
def test_an_image_without_its_fact_check_is_refused_by_the_export(tmp_path, timeline_root, gate):
    with pytest.raises(SystemExit, match="image: not fact-checked"):
        export(tmp_path, timeline_root, {**gate, **IMAGE})
    assert not (tmp_path / "timeline.toml").exists()


def test_the_export_refuses_a_bad_image_through_load_timeline(tmp_path, timeline_root):
    with pytest.raises(SystemExit, match="does not pass load_timeline.*unknown image license"):
        export(tmp_path, timeline_root, {**GATE, **IMAGE, "license": "cc-by-sa-4.0"})


# ------------------------------------------------------------------ rendering
def figure(html):
    return re.search(r'<figure class="tl__figure">.*?</figure>', html).group(0)


def test_the_figure_sits_between_the_meta_line_and_the_summary(image_root):
    html = render(image_root, with_image())
    assert re.search(r'<p class="mono tl__meta">[^<]*</p><figure class="tl__figure">.*?</figure><p class="small tl__summary">', html)


def test_the_img_is_lazy_sized_and_described(image_root):
    img = re.search(r"<img [^>]*>", figure(render(image_root, with_image()))).group(0)
    assert f'src="../img/history/{EVENT_ID}.webp"' in img and 'width="320" height="400"' in img
    assert f'alt="{IMAGE["alt"]}"' in img and 'loading="lazy" decoding="async"' in img
    assert "srcset" not in img and "http" not in img


def test_the_caption_comes_before_a_visible_public_domain_credit(image_root):
    fig = figure(render(image_root, with_image()))
    assert ('<figcaption class="mono small">A fixture caption. <span class="tl__credit">Image: Fixture Author. Public domain, via '
            f'<a href="{COMMONS}">Wikimedia Commons</a>.</span></figcaption>') in fig


@pytest.mark.parametrize("license, credit", [
    ("cc0", f'Image: Fixture Author. Dedicated to the public domain (CC0), via <a href="{COMMONS}">Wikimedia Commons</a>.'),
    ("cc-by-4.0", 'Image: Fixture portrait, by Fixture Author. Cropped and resized. Licensed under '
                  '<a href="https://creativecommons.org/licenses/by/4.0/">Creative Commons Attribution 4.0</a>, via '
                  f'<a href="{COMMONS}">Wikimedia Commons</a>.'),
    ("own-work", "Diagram: The Electron Plumber."),
])
def test_each_licence_has_its_approved_credit(image_root, license, credit):
    assert f'<span class="tl__credit">{credit}</span>' in figure(render(image_root, with_image(license=license)))


def test_an_image_without_a_caption_still_shows_its_credit(image_root):
    fig = figure(render(image_root, with_image(caption=None)))
    assert '<figcaption class="mono small"><span class="tl__credit">Image: Fixture Author.' in fig


def test_image_text_is_escaped(image_root):
    fig = figure(render(image_root, with_image(alt='A "quoted" & plain portrait.', author="A & B")))
    assert 'alt="A &quot;quoted&quot; &amp; plain portrait."' in fig and "Image: A &amp; B." in fig


def test_an_event_without_an_image_renders_no_figure(timeline_root):
    html = render(timeline_root, EVENT)
    assert "tl__figure" not in html and "<figure" not in html


def test_the_axis_and_the_card_never_show_an_image():
    js = (ROOT / "static" / "js" / "site.js").read_text(encoding="utf-8")
    assert not re.search(r"\bimg\b|new Image|tl__figure|figure", js)


def test_the_figure_css_is_160px_floated_and_unfloated_at_560px():
    css = (ROOT / "static" / "css" / "site.css").read_text(encoding="utf-8")
    assert ".tl__figure { float: right; width: 160px; margin: 0 0 10px 1rem; }" in css
    phone = css[css.rindex("@media (max-width: 560px) {"):]
    assert ".tl__figure { float: none; margin: 0; }" in phone[:phone.index("}\n}")]
    assert "img { height: auto; }" in css


def test_a_history_page_with_images_passes_every_check(tmp_path, image_root):
    site = _built_with(tmp_path, image_root, with_image())
    assert (site / FILE.removeprefix("static/")).is_file()
    assert parse((site / "history" / "index.html").read_text(encoding="utf-8")).items
    assert check.check(site) == []


# ------------------------------------------------------------------ the real data
HANNEKE_CAPTION = "Schematic, not to scale: a cylindrical Penning trap holding one electron, the kind used at Harvard in 2008."


def test_every_real_event_has_its_image_and_the_folder_has_nothing_else():
    _, episodes = content.load(ROOT)
    events = content.load_timeline(ROOT, episodes)
    assert events and all(ev.image and ev.image.file == f"static/img/history/{ev.id}.webp" for ev in events)
    folder = ROOT / "static" / "img" / "history"
    assert sorted(p.name for p in folder.iterdir()) == sorted(f"{ev.id}.webp" for ev in events)
    assert sum(p.stat().st_size for p in folder.iterdir()) <= content.HISTORY_IMAGES_MAX_BYTES
    assert not any(check._has_metadata(".webp", p.read_bytes()) for p in folder.iterdir())
    by_id = {ev.id: ev.image for ev in events}
    assert by_id["2008-hanneke-electron-moment"].caption == HANNEKE_CAPTION
    assert {ev.image.license for ev in events} <= {"public-domain", "own-work"}


def test_the_built_history_page_credits_every_image(tmp_path):
    _, episodes = content.load(ROOT)
    events = content.load_timeline(ROOT, episodes)
    build.build(tmp_path / "site")
    text = (tmp_path / "site" / "history" / "index.html").read_text(encoding="utf-8")
    assert text.count('<figure class="tl__figure">') == len(events) == text.count('class="tl__credit"')
    for ev in events:
        if ev.image.license == "own-work":
            continue
        assert f'<a href="{ev.image.source_url}">Wikimedia Commons</a>' in text
