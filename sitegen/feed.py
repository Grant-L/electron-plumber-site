"""The Atom feed of published episodes (/feed.atom). Standard library only, and no build clock: the same data
always gives the same bytes."""
import datetime
import xml.etree.ElementTree as ET

from .content import ARCS

ATOM_NS = "http://www.w3.org/2005/Atom"
FEED_EPOCH = "2026-09-19T00:00:00Z"  # the feed's <updated> while no episode is published
TAG_AUTHORITY = "tag:electron-plumber.com,2026:"
INLINE = {"author"}  # kept on one line: <author><name>...</name></author>

ET.register_namespace("", ATOM_NS)


def _el(parent, tag, text=None, **attrs):
    el = ET.SubElement(parent, f"{{{ATOM_NS}}}{tag}", attrs)
    if text is not None:
        el.text = text
    return el


def atom_date(yyyy_mm_dd):
    """An episodes.toml date as an RFC 3339 timestamp at midnight UTC."""
    return datetime.date.fromisoformat(yyyy_mm_dd).isoformat() + "T00:00:00Z"


def episode_entry(site, ep):
    base = site["url"].rstrip("/")
    entry = ET.Element(f"{{{ATOM_NS}}}entry")
    _el(entry, "id", f"{TAG_AUTHORITY}episode-{ep.number:03d}")
    _el(entry, "title", ep.title)
    _el(entry, "link", rel="alternate", type="text/html", href=f"{base}/{ep.url}")
    _el(entry, "published", atom_date(ep.date))
    _el(entry, "updated", atom_date(ep.date))
    _el(entry, "category", term=ep.arc, label=ARCS[ep.arc])
    _el(entry, "summary", ep.excerpt, type="text")
    return entry


def _indent(el, level=0):
    children = list(el)
    if not children or el.tag.rpartition("}")[2] in INLINE:
        return
    el.text = "\n" + "  " * (level + 1)
    for child in children:
        _indent(child, level + 1)
        child.tail = "\n" + "  " * (level + 1)
    children[-1].tail = "\n" + "  " * level


def episodes_feed(site, episodes):
    base = site["url"].rstrip("/")
    published = sorted((e for e in episodes if e.status == "published" and not e.draft),
                       key=lambda e: (e.date, e.number), reverse=True)
    feed = ET.Element(f"{{{ATOM_NS}}}feed")
    _el(feed, "id", f"{TAG_AUTHORITY}feed")
    _el(feed, "title", site["title"])
    _el(feed, "subtitle", site["tagline"])
    _el(feed, "link", rel="self", type="application/atom+xml", href=f"{base}/feed.atom")
    _el(feed, "link", rel="alternate", type="text/html", href=f"{base}/")
    _el(feed, "updated", atom_date(published[0].date) if published else FEED_EPOCH)
    _el(_el(feed, "author"), "name", site["author"])
    feed.extend(episode_entry(site, ep) for ep in published)
    _indent(feed)
    body = ET.tostring(feed, encoding="unicode", short_empty_elements=True)
    # ElementTree escapes ">" in text and attribute values, so " />" can only be the end of an empty element.
    return '<?xml version="1.0" encoding="utf-8"?>\n' + body.replace(" />", "/>") + "\n"
