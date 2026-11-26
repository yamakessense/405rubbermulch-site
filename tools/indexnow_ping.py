#!/usr/bin/env python3
"""Tell Bing (and other IndexNow search engines) which pages changed.

Usage:
  python3 tools/indexnow_ping.py --all            # every page in sitemap.xml
  python3 tools/indexnow_ping.py FILE [FILE ...]  # changed repo files

A changed page file (index.html or <page>/index.html) sends that page.
A changed sitemap.xml or this script sends every page.
Only pages listed in sitemap.xml are sent.
"""
import json
import re
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HOST = "405rubbermulch.com"
KEY = "96f1c2389c0f4235b603e3557763fb27"
ENDPOINT = "https://api.indexnow.org/indexnow"


def sitemap_urls():
    text = (ROOT / "sitemap.xml").read_text()
    return re.findall(r"<loc>\s*([^<\s]+)\s*</loc>", text)


def urls_for(files, all_urls):
    if "--all" in files:
        return all_urls
    wanted = set()
    for f in files:
        if f in ("sitemap.xml", "tools/indexnow_ping.py", ".github/workflows/indexnow.yml"):
            return all_urls
        if f == "index.html":
            wanted.add(f"https://{HOST}/")
        elif f.endswith("/index.html") and f.count("/") == 1:
            wanted.add(f"https://{HOST}/{f.split('/')[0]}/")
    return [u for u in all_urls if u in wanted]


def main():
    urls = urls_for(sys.argv[1:], sitemap_urls())
    if not urls:
        print("No pages changed. Nothing sent.")
        return
    body = json.dumps({
        "host": HOST,
        "key": KEY,
        "keyLocation": f"https://{HOST}/{KEY}.txt",
        "urlList": urls,
    }).encode()
    req = urllib.request.Request(
        ENDPOINT, data=body, method="POST",
        headers={"Content-Type": "application/json; charset=utf-8"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        status = resp.status
    print(f"IndexNow answered {status} for {len(urls)} page(s):")
    for u in urls:
        print("  " + u)
    if status not in (200, 202):
        sys.exit(1)


if __name__ == "__main__":
    main()
