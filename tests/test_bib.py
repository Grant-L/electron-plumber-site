import pytest
from conftest import FIXTURE_SHA, ROOT, fixture_bib

from sitegen import bib

HEAD = f"% Copied from Grant-L/electron-plumber-notes sources.bib at commit {FIXTURE_SHA}. Do not edit here.\n"


def test_fixture_bib_parses_with_its_header():
    parsed = bib.parse(fixture_bib())
    assert parsed.sha == FIXTURE_SHA
    entry = parsed["hamilton1865letter"]
    assert entry.kind == "article" and entry.fields["pages"] == "1\u20132"
    assert entry.authors == ("Ann Author", "Will Writer")


def test_tex_accents_math_and_specials():
    parsed = bib.parse(HEAD + '@article{x2000,\n  author = {M{\\"u}ller, J{\\"U}rgen and {\\\'E}mile Zola and \\c{C}elik, Ay\\c{s}e},\n'
                       "  title = {{\\\"U}ber die $g-2$ Anomalie des {QED} Elektrons, \\& mehr --- {\\ss}},\n"
                       '  journal = "Ann. Phys.",\n  year = 1905,\n  doi = {10.1002/andp.x\\_1}\n}\n')
    entry = parsed["x2000"]
    assert entry.fields["title"] == "\u00dcber die g-2 Anomalie des QED Elektrons, & mehr \u2014 \u00df"
    assert entry.fields["year"] == "1905" and entry.fields["journal"] == "Ann. Phys."
    assert entry.fields["doi"] == "10.1002/andp.x_1"
    assert entry.authors == ("J\u00dcrgen M\u00fcller", "\u00c9mile Zola", "Ay\u015fe \u00c7elik")


def test_math_greek_and_accent_on_dotless_i():
    entry = bib.parse(HEAD + "@misc{y, title = {On $\\alpha/2\\pi$ and Mart{\\'\\i}nez}, year = {1948}}\n")["y"]
    assert entry.fields["title"] == "On \u03b1/2\u03c0 and Mart\u00ednez"


@pytest.mark.parametrize("body, message", [
    ("@article{a, title = {A}, year = {1}}\n@article{A, title = {B}, year = {2}}\n", "duplicate key"),
    ("@article{a, title = {\\foo A}, year = {1}}\n", "unknown TeX macro"),
    ("@article{a, title = {A {b}, year = {1}}\n", "unbalanced"),
    ("@article{a, title = {A}}\n", "no year"),
    ("@article{a, year = {1}}\n", "no title"),
    ("@article{a, title = {A}, title = {B}, year = {1}}\n", "duplicate field"),
    ("@string{j = {Journal}}\n", "not supported"),
    ("@article{a, title = j # {A}, year = {1}}\n", "braced"),
    ("@article{a, title = {$x^2$}, year = {1}}\n", "superscripts"),
    ("stray\n", "stray text"),
])
def test_bad_bib_is_refused(body, message):
    with pytest.raises(bib.BibError, match=message):
        bib.parse(HEAD + body)


@pytest.mark.parametrize("head", [
    "",
    "% Copied from Grant-L/electron-plumber-notes sources.bib at commit a3b61e3. Do not edit here.\n",
    "% sources.bib\n" + HEAD,
    HEAD.replace("Grant-L/electron-plumber-notes", "someone/else"),
])
def test_missing_or_malformed_sha_header_is_refused(head):
    with pytest.raises(bib.BibError, match="first line"):
        bib.parse(head + "@article{a, title = {A}, year = {1}}\n")


def test_the_copied_sources_bib_parses():
    """content/sources.bib is the notes repo's sources.bib, copied with its SHA header.
    Expected to fail until the copy lands: it waits on hanneke2008electron reaching the notes repo."""
    path = ROOT / "content" / "sources.bib"
    assert path.is_file(), "content/sources.bib has not been copied from Grant-L/electron-plumber-notes yet"
    parsed = bib.load(path)
    assert len(parsed.sha) == 40 and parsed.entries
