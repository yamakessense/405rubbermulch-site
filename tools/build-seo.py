#!/usr/bin/env python3
"""Hoist Claude Design's <helmet> block into the real <head>.

Claude Design exports every head-level tag -- title, description, canonical,
OG/Twitter, JSON-LD, gtag, fonts -- inside a <helmet> element that sits in the
<body>. support.js copies those into <head> at runtime, with JavaScript.
Crawlers that don't execute JS (Bingbot, and every social scraper) therefore
see a <head> with nothing in it but charset, viewport and favicons.

This script moves the tags into <head> statically, so they are in the served
bytes. Run it after every Claude Design export:

    python3 tools/build-seo.py            # rewrite files in place
    python3 tools/build-seo.py --check    # exit 1 if any file still needs it

It is idempotent: a file whose <helmet> is already hoisted is left alone.
Tags are MOVED, not copied -- support.js appends helmet children to <head>
without checking what is already there, so a tag left in both places renders
twice.
"""

import argparse
import glob
import os
import re
import sys

VOID = {"meta", "link", "base"}
HELMET_RE = re.compile(r"([ \t]*)<helmet(\s[^>]*)?>(.*?)</helmet>\s*?\n", re.S | re.I)
TAG_OPEN_RE = re.compile(r"<([a-zA-Z][a-zA-Z0-9-]*)((?:[^>\"']|\"[^\"]*\"|'[^']*')*)>", re.S)


def split_children(fragment):
    """Split a fragment into its top-level elements, preserving source text.

    Helmet children are always flat (title, meta, link, script, style), so a
    same-name close tag is unambiguously the matching one.
    """
    out, i = [], 0
    while i < len(fragment):
        m = TAG_OPEN_RE.search(fragment, i)
        if not m:
            break
        name = m.group(1).lower()
        if name in VOID or m.group(2).rstrip().endswith("/"):
            out.append(fragment[m.start():m.end()])
            i = m.end()
            continue
        close = re.compile(r"</%s\s*>" % re.escape(name), re.I).search(fragment, m.end())
        if not close:
            raise SystemExit("unclosed <%s> in helmet" % name)
        out.append(fragment[m.start():close.end()])
        i = close.end()
    return out


def key(tag):
    """Identity used for de-duplication: the tag with whitespace collapsed."""
    return re.sub(r"\s+", " ", tag).strip()


def hoist(src, path):
    """Return (new_source, moved_tag_count). No <helmet> means nothing to do."""
    m = HELMET_RE.search(src)
    if not m:
        return src, 0

    head_start = src.index("<head>")
    head_end = src.index("</head>")
    if not (head_start < m.start()):
        raise SystemExit("%s: <helmet> is not after <head>" % path)

    existing = {key(t) for t in split_children(src[head_start + len("<head>"):head_end])}

    moved = []
    for tag in split_children(m.group(3)):
        k = key(tag)
        if k in existing:
            continue          # already in <head> (the favicons overlap)
        existing.add(k)
        moved.append(re.sub(r"^\n?[ \t]*", "", tag, count=1))

    if not moved:
        # Helmet held nothing new; still drop the now-redundant wrapper.
        return src[:m.start()] + src[m.end():], 0

    block = "\n".join(moved) + "\n"
    out = src[:head_end] + block + src[head_end:]
    # Re-locate the helmet block: inserting into <head> shifted every offset.
    m2 = HELMET_RE.search(out)
    out = out[:m2.start()] + out[m2.end():]
    return out, len(moved)


def targets(root):
    return sorted(
        p for p in glob.glob(os.path.join(root, "**", "*.html"), recursive=True)
        if ".git" not in p.split(os.sep)
    )


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true",
                    help="report files that still need hoisting; change nothing")
    ap.add_argument("--root", default=os.path.join(os.path.dirname(__file__), ".."))
    args = ap.parse_args()

    pending = 0
    for path in targets(args.root):
        rel = os.path.relpath(path, args.root)
        src = open(path, encoding="utf-8").read()
        new, n = hoist(src, rel)
        if new == src:
            continue
        pending += 1
        if args.check:
            print("needs hoisting: %s (%d tag%s still in <helmet>)"
                  % (rel, n, "" if n == 1 else "s"))
        else:
            open(path, "w", encoding="utf-8").write(new)
            print("hoisted %d tag%s into <head>: %s" % (n, "" if n == 1 else "s", rel))

    if args.check and pending:
        print("\n%d file(s) still ship SEO tags only JavaScript can see." % pending)
        return 1
    if not pending:
        print("all pages already carry their SEO tags in <head>")
    return 0


if __name__ == "__main__":
    sys.exit(main())
