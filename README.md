# 405rubbermulch.com — website source

Source for the live site at **https://405rubbermulch.com**, deployed to Hostinger.

## Repo structure (important)
Every site file lives at the **repository root** — `index.html`, `.htaccess`, `img/`, and the
state/section folders (`arkansas/`, `kansas/`, `missouri/`, `oklahoma/`,
`commercial-playgrounds/`, `coverage-calculator/`, `get-a-quote/`, `premium-quality/`, `terms/`).

**Why this matters:** Hostinger deploys the repo *contents* into `public_html/`. Keeping files at
the root means they land as `public_html/index.html`, `public_html/arkansas/index.html`, etc. —
directly servable. A previous setup nested the site inside a subfolder, so pages ended up buried
too deep in `public_html/…/…` and never showed. Do **not** add a wrapping folder.

## Deploy (Hostinger built-in Git — preferred)
1. hPanel → **Websites → 405rubbermulch.com → Advanced → Git**
2. Repository: `https://github.com/yamakessense/405rubbermulch-site.git`
3. Branch: `main`
4. Install path / directory: `public_html`
5. For push-to-deploy, add the Hostinger-provided **webhook URL** to this repo:
   GitHub → Settings → Webhooks → Add webhook.

After that, publishing an update = commit + push to `main`, then Hostinger auto-deploys (or click
**Deploy** in the Git panel).

## Updating content from Claude Design
1. Export/deploy the latest draft out of Claude Design.
2. Copy the exported files over these (replace `index.html`, add new pages like `thank-you/`, etc.).
3. **Run `python3 tools/build-seo.py`** — see below. A fresh export re-buries the SEO tags in
   `<helmet>`; this puts them back in `<head>`. It is idempotent, so running it twice is harmless.
4. **Run `python3 tools/prerender.py`** — bakes a plain-HTML copy of each rendered page into the
   file so crawlers that don't run JavaScript see real words and prices instead of `{{ }}`.
   Needs Playwright + Chrome and `REACT_DIR` (see the script's docstring). Re-run after every
   content change; `--check` exits 1 if a page lacks its copy.
5. Re-add the tracking pieces below if the export dropped them, then
   `git add -A && git commit -m "…" && git push`

## SEO tags must live in the real `<head>` (don't break this)
Claude Design exports put every head-level tag — `<title>`, the meta description, canonical,
OG/Twitter, the JSON-LD, gtag, the font links — inside `<helmet>`, an element that sits in the
**`<body>`**. `support.js` copies its children into `<head>` **at runtime, with JavaScript**.

Googlebot renders JS and sees them. **Bingbot does not**, and neither does any social scraper
(Facebook, LinkedIn, X). To Bing the `<head>` held nothing but charset, viewport and favicons —
which is why Bing Webmaster Tools reported "Meta Description tag missing" site-wide.

`tools/build-seo.py` fixes this by moving the tags out of `<helmet>` and into `<head>`:

```
python3 tools/build-seo.py            # rewrite the pages in place
python3 tools/build-seo.py --check    # exit 1 if any page still needs it — use before deploying
```

Tags are **moved, not copied**. `support.js` appends helmet children to `<head>` without checking
what is already there, so a tag left in both places would render twice — trading a missing
description for a duplicate one. The script de-duplicates against the existing `<head>` (the
favicons appear in both) and deletes the emptied `<helmet>` wrapper. Pages with no `<helmet>` are
left alone.

### Page body is client-rendered (partly solved by tools/prerender.py)
`<x-dc>` is a template full of `{{ }}` bindings that React turns into the real page in the browser.
A crawler that doesn't run JS still sees no body copy at all — so Bing indexes these pages on their
head tags alone. `tools/prerender.py` now bakes a static copy of the rendered body ahead of `<x-dc>`, hidden for
JS visitors and removed once React renders. The raw `<x-dc>` template (with its `{{ }}`) still
follows it in the file because support.js needs it, so non-JS crawlers read the real copy first
but can still see template text after it.

## Conversion tracking (how it works — don't break this)
- Every page's `<head>` runs `gtag('config', 'AW-18336005673')`. This must stay on **all** pages:
  it's what captures the Google Ads click ID (gclid) into the `_gcl_aw` cookie when an ad lands
  anywhere on the site. Without it, later conversions can't be attributed and never show in Ads.
- The quote forms (homepage, `get-a-quote/`, `fundraiser/`) submit to Formspree via fetch (AJAX),
  then redirect to **`/thank-you/`**, which fires the conversion event
  (`AW-18336005673/AaJ_CMze69McEKn8pKdE`) on page load. The forms also carry
  `action`/`method`/`_next` attributes so a plain no-JS submission posts to Formspree and lands on
  the same thank-you page (note: Formspree honors `_next` on paid plans).
- **Enhanced conversions:** each quote form saves the visitor's email and phone to
  `sessionStorage` (`ec_ud`) right before redirecting. `/thank-you/` reads it, calls
  `gtag('set', 'user_data', …)` (Google hashes it), fires the conversion, and deletes the key.
- **Website call conversion:** every page except `/thank-you/` configures
  `AW-18336005673/VxaCCN6jzuEcEKn8pKdE` with `phone_conversion_number: '(405) 206-8111'`.
  A `phone_conversion_callback` swaps the number (text and `tel:` links) for Google's
  forwarding number on ad visits, re-applying for 15 s as React renders. Keep the number on the
  page written exactly `(405) 206-8111`.
- To verify: open `/thank-you/` in a browser with Google Tag Assistant — the conversion fires on
  every load. `/thank-you/` is `noindex` and unlinked, so real traffic only reaches it via a form.
