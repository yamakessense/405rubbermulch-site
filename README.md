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
3. `git add -A && git commit -m "…" && git push`

## Conversion tracking (how it works — don't break this)
- Every page's `<head>` runs `gtag('config', 'AW-18336005673')` **and**
  `gtag('config', 'AW-998556622')`. Both must stay on **all** pages: that's what captures the
  Google Ads click ID (gclid) into the `_gcl_aw` cookie when an ad lands anywhere on the site.
  Without it, later conversions can't be attributed and never show in Ads.
- There is **one** `gtag.js` loader per page (`?id=GT-WB72BHMG`) and every account rides on it as
  an extra `config` line. When Google's setup screen hands you a fresh snippet for a new account,
  take only the `config` command from it — adding a second loader would double-load the library.
- The quote forms (homepage, `get-a-quote/`, `fundraiser/`) submit to Formspree via fetch (AJAX),
  then redirect to **`/thank-you/`**, which fires both conversion events on page load:
  `AW-18336005673/AaJ_CMze69McEKn8pKdE` (lead) and `AW-998556622/DwixCPrwjN0cEM6Hk9wD` (purchase).
  The forms also carry `action`/`method`/`_next` attributes so a plain no-JS submission posts to
  Formspree and lands on the same thank-you page (note: Formspree honors `_next` on paid plans).
- `transaction_id` dedupe: each form mints an id at submit time and puts it on both the JS redirect
  and the `_next` fallback URL (`/thank-you/?from=…&tid=…`); `/thank-you/` reads it back from
  `?tid=`. A refresh or back-navigation replays the same id, so Google counts one conversion. If
  you add another form, mint a `tid` the same way — without it the page falls back to a per-tab
  sessionStorage id, which is weaker.
- To verify: open `/thank-you/` in a browser with Google Tag Assistant — both conversions fire on
  every load. `/thank-you/` is `noindex` and unlinked, so real traffic only reaches it via a form.
