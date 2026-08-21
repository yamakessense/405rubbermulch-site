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
3. **Re-apply the static `<head>` SEO tags** — see below. A fresh export puts them back inside
   `<helmet>`, which undoes the fix.
4. `git add -A && git commit -m "…" && git push`

## SEO tags must live in the real `<head>` (don't break this)
Claude Design exports put `<title>`, `<meta name="description">`, `<meta name="robots">`, the
canonical link, the OG/Twitter tags and the JSON-LD inside `<helmet>` — an element in the `<body>`
whose contents `support.js` copies into `<head>` **at runtime, with JavaScript**. Bingbot does not
run JavaScript for its SEO checks, so to Bing those tags simply do not exist; Bing Webmaster Tools
reported "Meta Description tag missing" site-wide because of this.

So on every page the four crawler-critical tags are kept **directly in `<head>`**, not in
`<helmet>`:

```html
<title>…</title>
<meta name="description" content="…">
<meta name="robots" content="index, follow, max-image-preview:large">
<link rel="canonical" href="https://405rubbermulch.com/…">
```

Keep each tag in exactly one place. Leaving a copy in `<helmet>` too makes `support.js` append a
second one at runtime, which is its own SEO problem (duplicate description / title).

Still JS-injected and therefore invisible to non-rendering crawlers: the OG and Twitter card tags
(so link previews on Facebook, LinkedIn and X may come up blank) and the LocalBusiness/FAQ JSON-LD.
The page body is client-rendered too, so a non-rendering crawler sees no copy at all. Fixing that
means pre-rendering the pages to static HTML — a bigger change, not yet done.

## Conversion tracking (how it works — don't break this)
- Every page's `<head>` runs `gtag('config', 'AW-18336005673')`. This must stay on **all** pages:
  it's what captures the Google Ads click ID (gclid) into the `_gcl_aw` cookie when an ad lands
  anywhere on the site. Without it, later conversions can't be attributed and never show in Ads.
- The quote forms (homepage, `get-a-quote/`, `fundraiser/`) submit to Formspree via fetch (AJAX),
  then redirect to **`/thank-you/`**, which fires the conversion event
  (`AW-18336005673/AaJ_CMze69McEKn8pKdE`) on page load. The forms also carry
  `action`/`method`/`_next` attributes so a plain no-JS submission posts to Formspree and lands on
  the same thank-you page (note: Formspree honors `_next` on paid plans).
- To verify: open `/thank-you/` in a browser with Google Tag Assistant — the conversion fires on
  every load. `/thank-you/` is `noindex` and unlinked, so real traffic only reaches it via a form.
