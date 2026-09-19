import pytest

from sitegen import md


def test_inline_emphasis_links_and_code():
    out = md.inline("A **bold** and *italic* [link](https://example.org/a) with `x < 1`.")
    assert "<strong>bold</strong>" in out and "<em>italic</em>" in out
    assert '<a href="https://example.org/a">link</a>' in out
    assert "<code>x &lt; 1</code>" in out


def test_raw_html_is_escaped_never_passed_through():
    assert "<script>" not in md.inline("<script>alert(1)</script>")


def test_relative_links_point_at_the_notes_repo():
    out = md.inline("[sim](ep001-sims/net.asc) and [abs](https://a.b/c) and [anchor](#x)", link_base="https://h/lectures")
    assert 'href="https://h/lectures/ep001-sims/net.asc"' in out
    assert 'href="https://a.b/c"' in out and 'href="#x"' in out


def test_smart_quotes_leave_code_alone():
    out = md.inline('The label said "12 V, fused" and it\'s `"raw"`.')
    assert "\u201c12 V, fused\u201d" in out and "it\u2019s" in out
    assert '<code>"raw"</code>' in out


def test_lists_with_wrapped_items():
    out = md.render("- one\n  continues\n- two\n\n1. first\n2. second\n")
    assert out.count("<li>") == 4
    assert "<li>one continues</li>" in out and "<ol>" in out and "<ul>" in out


def test_sections_split_on_h2_and_drop_the_preamble():
    parts = md.sections("# Title\n\nintro\n\n## Learning goals\n\n- a\n\n## Readings\n\ntext\n")
    assert [t for t, _ in parts] == ["Learning goals", "Readings"]


def test_comments_are_dropped():
    assert "DRAFT" not in md.render("<!-- DRAFT -->\n\nText.")


@pytest.mark.parametrize("source", ["| a | b |\n|---|---|\n", "- a\n    - nested\n", "```\nnever closed\n"])
def test_unsupported_markdown_fails_loudly(source):
    with pytest.raises(md.MarkdownError):
        md.render(source)


def test_urls_survive_the_text_passes():
    out = md.inline("[spin](https://en.wikipedia.org/wiki/Spin_(physics)) and [mx](https://x.org/Maxwell's_equations) and [a](https://x.org/_a_b_)")
    assert 'href="https://en.wikipedia.org/wiki/Spin_(physics)"' in out
    assert "Maxwell&#x27;s_equations" in out and "\u2019" not in out
    assert 'href="https://x.org/_a_b_"' in out and "<em>" not in out


def test_dot_slash_is_a_prefix_not_a_character_set():
    out = md.inline("[a](./.hidden/file) and [b](../sources.bib)", link_base="https://h/lectures")
    assert 'href="https://h/lectures/.hidden/file"' in out and 'href="https://h/lectures/../sources.bib"' in out


def test_ordered_lists_keep_their_first_number_and_lists_may_interrupt_a_paragraph():
    assert '<ol start="3">' in md.render("3. third\n4. fourth\n")
    out = md.render("Readings:\n- one\n- two\n")
    assert "<p>Readings:</p>" in out and out.count("<li>") == 2


def test_quotes_after_emphasis_markers_open_correctly():
    assert md.inline('*"hello"*') == "<em>\u201chello\u201d</em>"


@pytest.mark.parametrize("source", ["---\n", "~~~\ncode\n~~~\n", "##### five\n", "+ item\n", "1) item\n", "![alt](img.png)\n", "a | b\n--|--\n"])
def test_more_unsupported_markdown_fails_loudly(source):
    with pytest.raises(md.MarkdownError):
        md.render(source)
