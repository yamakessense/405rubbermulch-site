#!/usr/bin/env python3
"""Bake a plain-HTML copy of each page's rendered body into the page.

Why: the page body lives inside <x-dc> as a template full of {{ }} bindings.
support.js turns it into the real page in the browser with React. Crawlers that
don't run JavaScript (Bing, most AI crawlers, social previews) only ever see the
raw template, so they read "{{ yourCost }}" instead of "$3,826".

What this does, per page:
  1. Serves the repo on localhost and opens the page in headless Chrome.
  2. Waits for support.js to render #dc-root, then copies its HTML.
  3. Cleans the copy: drops ids (no duplicate anchors), forms, scripts,
     and event attributes.
  4. Writes it into the page between <!--dc-static--> markers, just before
     <x-dc>, plus a tiny head script that hides it the instant JavaScript runs
     and removes it once the live page has rendered.

Visitors with JavaScript never see the copy. Crawlers without it see the real
words and prices. Idempotent: re-running replaces the previous copy.

Usage:
  python3 tools/prerender.py            # rewrite pages in place
  python3 tools/prerender.py --check    # exit 1 if any page lacks a copy
React is served from a local npm copy (same files, same SRI hashes as unpkg).
Set REACT_DIR to the folder holding react-18.3.1/ and react-dom-18.3.1/ from
`npm pack react@18.3.1 react-dom@18.3.1` (each extracted to <name>/package).
"""
import functools, http.server, os, re, socketserver, sys, threading
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
START, END = "<!--dc-static-->", "<!--/dc-static-->"
HEAD_START, HEAD_END = "<!--dc-static-head-->", "<!--/dc-static-head-->"
HEAD_SNIPPET = (
    HEAD_START
    + "<style>.dc-js #dc-root{display:none!important}</style>"
    + "<script>document.documentElement.classList.add('dc-js');"
    # Remove the copy once React has rendered real content. If that never happens
    # (support.js or React failed to load), un-hide the copy after 8 s so the
    # visitor still gets a readable page instead of a blank one.
    + "(function(){var n=0,t=setInterval(function(){var r=document.getElementById('dc-root'),s=document.getElementById('dc-static'),h=document.documentElement;"
    + "if(!s){clearInterval(t);h.classList.remove('dc-js');return;}"
    + "if(r&&r.textContent.trim().length>50){clearInterval(t);s.remove();h.classList.remove('dc-js');}"
    + "else if(++n>160){clearInterval(t);h.classList.remove('dc-js');}},50);})();</script>"
    + HEAD_END
)


def pages():
    out = []
    for p in sorted(ROOT.rglob("index.html")):
        if any(part in ("tools", ".git") for part in p.relative_to(ROOT).parts):
            continue
        if "<x-dc" in p.read_text(encoding="utf-8"):
            out.append(p)
    return out


def url_path(p):
    rel = p.relative_to(ROOT).parent.as_posix()
    return "/" if rel == "." else f"/{rel}/"


def clean(html):
    html = re.sub(r"<script\b.*?</script>", "", html, flags=re.S | re.I)
    html = re.sub(r"<form\b.*?</form>", "", html, flags=re.S | re.I)
    html = re.sub(r"\s(id|on[a-z]+)=\"[^\"]*\"", "", html, flags=re.I)
    html = re.sub(r"\s(id|on[a-z]+)='[^']*'", "", html, flags=re.I)
    if "{{" in html:
        raise ValueError("rendered copy still contains {{ }}")
    return html


def strip_existing(src):
    src = re.sub(re.escape(START) + r".*?" + re.escape(END) + r"\n?", "", src, flags=re.S)
    src = re.sub(re.escape(HEAD_START) + r".*?" + re.escape(HEAD_END) + r"\n?", "", src, flags=re.S)
    return src


def render_all(targets):
    from playwright.sync_api import sync_playwright

    react_dir = Path(os.environ.get("REACT_DIR", ""))
    react = react_dir / "react-18.3.1/package/umd/react.production.min.js"
    react_dom = react_dir / "react-dom-18.3.1/package/umd/react-dom.production.min.js"
    if not (react.is_file() and react_dom.is_file()):
        sys.exit("REACT_DIR must point at the extracted npm react/react-dom 18.3.1 packages")

    class Quiet(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *a):
            pass
    handler = functools.partial(Quiet, directory=str(ROOT))
    srv = socketserver.TCPServer(("127.0.0.1", 0), handler)
    port = srv.server_address[1]
    threading.Thread(target=srv.serve_forever, daemon=True).start()

    results = {}
    with sync_playwright() as pw:
        browser = pw.chromium.launch(executable_path=os.environ.get("CHROME", "/usr/bin/google-chrome"), args=["--no-sandbox"])
        for p in targets:
            page = browser.new_page()
            def route(r):
                u = r.request.url
                if u.startswith("https://unpkg.com/react@18.3.1/"):
                    return r.fulfill(path=str(react), content_type="application/javascript", headers={"Access-Control-Allow-Origin": "*"})
                if u.startswith("https://unpkg.com/react-dom@18.3.1/"):
                    return r.fulfill(path=str(react_dom), content_type="application/javascript", headers={"Access-Control-Allow-Origin": "*"})
                if u.startswith(f"http://127.0.0.1:{port}"):
                    return r.continue_()
                return r.abort()  # analytics, fonts, images from other hosts
            page.route("**/*", route)
            page.goto(f"http://127.0.0.1:{port}{url_path(p)}", wait_until="load")
            page.wait_for_function("() => { const r = document.getElementById('dc-root'); return r && r.innerText.trim().length > 50 }", timeout=20000)
            page.wait_for_timeout(500)
            results[p] = page.eval_on_selector("#dc-root", "e => e.innerHTML")
            page.close()
        browser.close()
    srv.shutdown()
    return results


def main():
    targets = pages()
    if "--check" in sys.argv:
        missing = [str(p.relative_to(ROOT)) for p in targets if START not in p.read_text(encoding="utf-8")]
        if missing:
            print("missing plain-HTML copy:", *missing, sep="\n  ")
            sys.exit(1)
        print(f"all {len(targets)} pages carry a plain-HTML copy")
        return

    # Render from clean sources so an old copy never ends up inside a new one.
    originals = {p: p.read_text(encoding="utf-8") for p in targets}
    for p, src in originals.items():
        p.write_text(strip_existing(src), encoding="utf-8")
    try:
        rendered = render_all(targets)
    except Exception:
        for p, src in originals.items():
            p.write_text(src, encoding="utf-8")
        raise

    for p in targets:
        src = p.read_text(encoding="utf-8")
        body = clean(rendered[p])
        block = f'{START}<div id="dc-static">{body}</div>{END}\n'
        i = src.index("<x-dc")
        src = src[:i] + block + src[i:]
        src = src.replace("</head>", HEAD_SNIPPET + "\n</head>", 1)
        p.write_text(src, encoding="utf-8")
        words = len(re.sub(r"<[^>]+>", " ", body).split())
        print(f"{p.relative_to(ROOT)}: {words} words baked in")


if __name__ == "__main__":
    main()
