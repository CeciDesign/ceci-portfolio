# Ceci Chang — portfolio site (changhsiju.xyz)

Static site for [Ceci Chang's UX/UI design portfolio](https://changhsiju.xyz),
hosted on GitHub Pages. Fully self-contained: every page, image and font is in
this repo; no third-party CDN, no site builder.

**Changing hands?** See [`docs/HANDOVER.md`](docs/HANDOVER.md) for the
account-transfer checklist (repo, Pages, DNS, domain).

## What is in here

| Path | What it is |
|---|---|
| `2026 portfolio/` | **Ceci's export — the source of truth.** HTML pages, `images/`, `i18n.js` (EN + zh-Hant strings), `translations-editor.html` (her offline editor; not deployed). |
| `site/` | **What is deployed.** Generated from the export by `integrate_2026.py`; never hand-edit page content here. Also holds the 23 preserved legacy project pages (`site/<slug>/`) and all assets. |
| `integrate_2026.py` | The build. Mirrors the export into `site/`, self-hosts fonts, injects SEO/share meta, and **fails** on a missing image, an undefined i18n key or an off-domain reference. |
| `patches/` | Pages authored for the site rather than exported (e.g. `/about-me/`), applied by the build. |
| `.github/workflows/pages.yml` | Deploys `site/` to GitHub Pages on every push to `main` (about 1 minute). |
| `docs/` | Handover checklist, decision notes, session handoffs, asset manifest. |
| `legacy/`, `rip2.py`, `build_clean.py`, `fix_*.py`, `enrich_meta.py`, `localize_assets.py` | Historical tooling from the 2025–2026 migration off IM Creator. Not part of the current build; kept for reference. |
| `CLAUDE.md` (= `AGENTS.md`) | Working rules and project memory for AI-assisted sessions. |

## Updating the site

```bash
# one-time after cloning
pip3 install beautifulsoup4 lxml
./setup.sh                      # enables the tracked git hooks

# every update
#   1. put the new export into "2026 portfolio/"
python3 integrate_2026.py       # must exit 0 — read its output if it doesn't
git add -A && git commit -m "Update portfolio" && git push
```

GitHub Pages serves the new build within a minute or two. Browsers cache pages
for 10 minutes, so hard-refresh (`Cmd+Shift+R`) before concluding a change is
missing.

## Local preview

```bash
python3 -m http.server 8765 --directory site
# open http://localhost:8765/
```

## Hosting and domain

- GitHub Pages, source = GitHub Actions (`pages.yml`), custom domain
  `changhsiju.xyz`, HTTPS via Let's Encrypt (automatic).
- Domain registered at Cloudflare Registrar, DNS on Cloudflare (records set to
  DNS only, not proxied): apex `A` records → GitHub Pages IPs
  (`185.199.108–111.153`), `www` → `CNAME` to the repo owner's
  `<username>.github.io`.
