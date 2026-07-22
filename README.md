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

## Conversion tracking note
The new Google Ads conversion (AW) tag belongs on the **thank-you page** that the visitor reaches
after a Formspree submission. Set the Formspree form's `_next` to the thank-you URL so the tag
actually fires on lead completion (the tag can't fire if Formspree keeps the user off-site).
