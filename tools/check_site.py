#!/usr/bin/env python3
"""Static health check for 405rubbermulch.com. Runs in GitHub Actions on every push.

Fails (exit 1) if any page:
  - has JSON-LD that does not parse
  - has more or fewer than one <h1> in the raw HTML crawlers read
  - shows {{ }} template text in the crawler-readable body (outside <template>/<script>/<style>)
  - is missing <html lang="en">, a <title>, a meta description or a canonical link
  - links to an internal page or asset that does not exist in the repo
Also checks that sitemap.xml and llms.txt URLs exist, and that the IndexNow key file is present.
No third-party packages needed.
"""
import json, re, sys
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE = "https://405rubbermulch.com"
INDEXNOW_KEY = "96f1c2389c0f4235b603e3557763fb27"


class Page(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.skip = 0          # depth inside template/script/style
        self.h1 = 0
        self.text = []
        self.links = []
        self.lang = None
        self.title = False
        self.desc = False
        self.canonical = False
        self.ld = []
        self._ld = None

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "html":
            self.lang = a.get("lang")
        if tag == "script" and a.get("type") == "application/ld+json":
            self._ld = []
        if tag in ("template", "script", "style"):
            self.skip += 1
            return
        if self.skip:
            return
        if tag == "h1":
            self.h1 += 1
        if tag == "title":
            self.title = True
        if tag == "meta" and a.get("name") == "description" and a.get("content"):
            self.desc = True
        if tag == "link" and a.get("rel") == "canonical":
            self.canonical = True
        for k in ("href", "src"):
            v = a.get(k)
            if v:
                self.links.append(v)

    def handle_endtag(self, tag):
        if tag == "script" and self._ld is not None:
            self.ld.append("".join(self._ld))
            self._ld = None
        if tag in ("template", "script", "style") and self.skip:
            self.skip -= 1

    def handle_data(self, data):
        if self._ld is not None:
            self._ld.append(data)
        elif not self.skip:
            self.text.append(data)


def local_path(url):
    """Map an internal URL to a file in the repo, or None if external."""
    if url.startswith(SITE):
        url = url[len(SITE):] or "/"
    if not url.startswith("/") or url.startswith("//"):
        return None
    url = url.split("#")[0].split("?")[0]
    p = ROOT / url.lstrip("/")
    return p / "index.html" if url.endswith("/") else p


def main():
    errors = []
    pages = sorted(p for p in ROOT.rglob("index.html") if ".git" not in p.parts and "node_modules" not in p.parts)
    for f in pages:
        rel = f.relative_to(ROOT).as_posix()
        raw = f.read_text(encoding="utf-8")
        pg = Page()
        pg.feed(raw)
        # Some crawlers (Bing's SEO checker) count <h1 as text, even inside <template>.
        # Template headings are written <dc-h1> and mapped back to <h1> by support.js.
        literal_h1 = len(re.findall(r"<h1\b", raw, re.I))
        if rel != "thank-you/index.html" and literal_h1 != 1:
            errors.append(f"{rel}: {literal_h1} literal '<h1' strings in raw HTML (want 1; use <dc-h1> in the template)")
        if pg.lang != "en":
            errors.append(f"{rel}: <html lang> is {pg.lang!r}, expected 'en'")
        if not pg.title:
            errors.append(f"{rel}: missing <title>")
        if rel != "thank-you/index.html":
            if not pg.desc:
                errors.append(f"{rel}: missing meta description")
            if not pg.canonical:
                errors.append(f"{rel}: missing canonical link")
            if pg.h1 != 1:
                errors.append(f"{rel}: {pg.h1} <h1> tags in raw HTML (want exactly 1)")
        if "{{" in "".join(pg.text):
            errors.append(f"{rel}: '{{{{' template text visible to crawlers")
        for i, block in enumerate(pg.ld):
            try:
                json.loads(block)
            except Exception as e:
                errors.append(f"{rel}: JSON-LD block {i + 1} does not parse ({e})")
        for link in set(pg.links):
            lp = local_path(link)
            if lp is not None and not lp.exists():
                errors.append(f"{rel}: broken internal link {link}")

    sm = (ROOT / "sitemap.xml").read_text(encoding="utf-8")
    for loc in re.findall(r"<loc>(.*?)</loc>", sm):
        lp = local_path(loc)
        if lp is None or not lp.exists():
            errors.append(f"sitemap.xml: {loc} has no matching file")
    llms = (ROOT / "llms.txt").read_text(encoding="utf-8")
    for url in re.findall(r"\((https://405rubbermulch\.com[^)\s]*)\)", llms):
        lp = local_path(url)
        if lp is None or not lp.exists():
            errors.append(f"llms.txt: {url} has no matching file")
    key = ROOT / f"{INDEXNOW_KEY}.txt"
    if not key.exists() or key.read_text().strip() != INDEXNOW_KEY:
        errors.append("IndexNow key file missing or wrong")

    if errors:
        print("Site check FAILED:")
        for e in errors:
            print("  -", e)
        sys.exit(1)
    print(f"Site check passed: {len(pages)} pages, sitemap, llms.txt, IndexNow key.")


if __name__ == "__main__":
    main()
