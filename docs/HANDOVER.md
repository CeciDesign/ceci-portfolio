# Handover — moving changhsiju.xyz to Ceci's own GitHub account

**Status (2026-10-13): prepared, NOT yet executed.** The transfer is a
two-person, browser-only action (GitHub does not let an agent or token do it from
this environment). Albert initiates it, Ceci accepts it. Everything else in this
document is the before/after checklist so nothing breaks.

What is being handed over:

| Thing | Where it lives today | After handover |
|---|---|---|
| The whole site + build scripts + Ceci's exports + history | GitHub repo `yabroexperiments/ceci-portfolio` (public, ~200 MB, 93 commits) | `<ceci>/ceci-portfolio` — **transferred**, history intact |
| Hosting | GitHub Pages, deployed by `.github/workflows/pages.yml` on every push to `main` | Same workflow, runs under Ceci's account |
| Domain `changhsiju.xyz` | Namecheap, **Albert's** account, DNS → GitHub Pages | Albert's call: keep it and manage DNS for her, or push it to her Namecheap account (step C4) |
| Files NOT in the repo | Albert's Mac only (see §D) | Zip + send, or nothing — nothing live depends on them |

Nothing in this repo is secret: it has always been public, so transferring it
exposes nothing new. Ceci's export (`2026 portfolio/`) is committed in full.

---

## A. Before the transfer (Albert, 5 minutes)

1. **Get Ceci's GitHub username.** She needs a GitHub account (free). If she has
   none: github.com → Sign up, verify the email. Write the username down; every
   step below uses it as `<ceci>`.
2. **Ceci must not already own a repo named `ceci-portfolio`** (GitHub refuses
   the transfer otherwise). Rename hers first if so.
3. **Check whether `changhsiju.xyz` is a *verified domain* on Albert's account:**
   github.com → Settings → Pages → "Verified domains". If it is listed, note it:
   a domain verified on one account cannot be used by another account's Pages
   site, so it must be removed there right after the transfer (step C2).
4. Make sure `main` is clean and pushed (`git status`, `git log origin/main..`).
   Nothing in flight as of this document.

## B. The transfer (Albert initiates, Ceci accepts — within 24 h)

1. Albert: https://github.com/yabroexperiments/ceci-portfolio/settings →
   scroll to **Danger Zone** → **Transfer ownership** → "Select one of my
   organizations or specify a username" → type `<ceci>` → type
   `yabroexperiments/ceci-portfolio` to confirm → **I understand, transfer this
   repository**.
2. GitHub emails Ceci. She opens the link and clicks **Accept**. The link
   expires after 24 hours; if it does, repeat step 1.
3. Done when https://github.com/<ceci>/ceci-portfolio loads and shows the full
   history. The old URL redirects for git and the web (the old
   `yabroexperiments.github.io/ceci-portfolio` Pages URL does NOT redirect — the
   custom domain is what visitors use, so that is fine).

What moves with the repo, automatically: all commits and branches, tags
(including the `v2-current-deployed` rollback tag), Actions workflows, the Pages
configuration, the `github-pages` deployment environment. Albert is removed as
owner; he can be re-added as a collaborator if Ceci wants help later.

## C. Right after the transfer (the part that keeps the site up)

Order matters. C1–C3 the same day; C4 whenever.

**C1. Confirm Pages still deploys (Ceci, or Albert as collaborator).**
- `<ceci>/ceci-portfolio` → Settings → Pages. Expect: Source = **GitHub
  Actions**, Custom domain = `changhsiju.xyz`, "Enforce HTTPS" ticked. If the
  custom domain field is empty, type `changhsiju.xyz` and Save.
- Actions tab → "Deploy site/ to GitHub Pages" → **Run workflow** (on `main`).
  It should go green in ~1 min. Then open https://changhsiju.xyz/ and
  hard-refresh (`Cmd+Shift+R`) — Pages caches for 10 minutes, so an old page
  right after a deploy is normal.

**C2. Domain verification handoff (only if A3 found it verified).**
- Albert: Settings → Pages → Verified domains → remove `changhsiju.xyz`.
- Ceci: Settings → Pages → Add a domain → `changhsiju.xyz`. GitHub shows a TXT
  record (`_github-pages-challenge-<ceci>` → a token). Whoever controls
  Namecheap (Albert, until C4) adds it under Advanced DNS, then Ceci clicks
  Verify. This is optional for serving but protects the domain from being
  claimed by someone else's Pages site.

**C3. DNS: repoint `www` (Albert at Namecheap, 1 record).**
- Advanced DNS → the `CNAME` record for host `www` currently targets
  `yabroexperiments.github.io`. Change it to **`<ceci>.github.io`**.
- Leave the four `A` records for `@` (`185.199.108.153` … `185.199.111.153`)
  exactly as they are — those are GitHub's shared IPs, not account-specific.
- The old CNAME keeps working for a while because GitHub routes by hostname,
  but it will break the day Albert's account stops hosting anything, so do it
  now while it is fresh.

**C4. The domain registration itself (Albert's decision).**
- Option 1 — keep it: Albert keeps paying the yearly renewal and does DNS edits
  on request. Lowest effort, but the site goes dark if the renewal lapses.
- Option 2 — hand it over: Namecheap → Domain List → Manage → **Sharing &
  Transfer** → **Change Ownership** → enter Ceci's Namecheap username (she
  creates a free account first). Free, takes minutes, DNS records travel with
  the domain. Then she sets up auto-renew with her own card. This is the option
  that matches "everything in her own account".

**C5. Text in the repo that names the old owner (Ceci's first commit, or Albert
as collaborator).** None of these affect the live site; they are notes for
whoever maintains it.
- `CLAUDE.md`: the "Architecture at a glance" lines for the repo URL and
  GitHub user/email, the DNS line `www → CNAME yabroexperiments.github.io`, and
  "`gh` CLI … authenticated as `yabroexperiments`".
- `scripts/dep-vet-guard.mjs` line `OWN_ORG` (auto-passes git deps from the
  owner's own GitHub; there are no such deps, so it is cosmetic).
- `README.md` was rewritten for this handover and names no account.

## D. What is NOT in the repo (lives only on Albert's Mac)

All of it is gitignored by design and nothing live depends on it:
- `2026 portfolio revised/`, `202609_portfolio/` and their `.zip`s — Ceci's own
  original drops; she has them. `2026 portfolio/` in the repo is the folded,
  canonical copy.
- `mirror_v2/`, `.ripcache_live/`, `captured/` — scratch from the 2025–2026
  IM Creator rip. Obsolete; the site is standalone since 2026-08-03.
- Albert's global Claude Code config (`~/.claude/`), the yabro-hq scripts the
  guards reference in comments, and the `.claude/` session guard masters. The
  copies committed here work on their own; the comments just say where the
  masters are.
- Albert's git identity and `gh` login. Ceci commits as herself.

## E. How Ceci updates the site afterwards (the short version)

Full detail in `README.md` and `CLAUDE.md`; this is the loop:

1. Export from her editor into `2026 portfolio/` (HTML, `images/`, `i18n.js`).
2. `python3 integrate_2026.py` — it mirrors her export into `site/` and refuses
   to finish if an image is missing, an i18n key is undefined, or a page points
   off-domain. Trust the exit code.
3. `git add -A && git commit -m "..." && git push` — GitHub Pages redeploys in
   about a minute. Hard-refresh to see it.

She needs: git, Python 3 with `beautifulsoup4` and `lxml`, and `./setup.sh` once
after cloning (enables the tracked hooks).

## F. Rollback

A transfer can be reversed only by transferring back the same way (B1 from
Ceci's account to `yabroexperiments`). The site content itself is never at
risk: every commit is in the repo, and the `v2-current-deployed` tag plus the
`archive/v2-current-deployed` branch travel with it.
