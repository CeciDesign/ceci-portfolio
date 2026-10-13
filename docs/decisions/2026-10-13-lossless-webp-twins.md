# 2026-10-13 — Lossless WebP twins for the 31 untwinned PNGs

**Ask (AC):** "fix the PNG images by changing them to WebP — but ensure that the
file load improvement does NOT compromise the image quality for the viewer as
this is her portfolio so needs to look professional and high res."

**Done:** every PNG Ceci ships without a WebP twin now has one, generated
losslessly (pixel-identical, verified by decode-and-compare), served through the
same build gate that already serves her own twins. Nothing lossy was added.

## Numbers

Per-page image payload (KB; `before` = production as of 295cb18):

| page | before | after |
|---|---:|---:|
| index.html (homepage) | 3717 | 2209 |
| drift-growth.html | 2644 | 2055 |
| drift-earn.html | 2245 | 1479 |
| binance-copytrading.html | 2016 | 1404 |
| binance-leaderboard.html | 1462 | 804 |
| binance-futures.html | 1281 | 850 |
| traderwagon.html | 1217 | 1004 |
| ui-design.html | 1217 | 1217 (all images already had her twins) |
| **total** | **15799** | **11022** (-30%) |

The 31 new twins: 10582 KB of PNG → 5690 KB of WebP (-47%), every one
pixel-exact (PSNR ∞, SSIM 1.0, max channel error 0). Only `bnct-app-05.png`
still serves as PNG (her twin is a zero-byte file; already in `WEBP_SKIP`).

## Why lossless, with evidence

Trial on four representative images (Pillow 12.3 / libwebp, method 6):

| image | PNG | lossless | lossy q95 | q95 PSNR | q95 max err |
|---|---:|---:|---:|---:|---:|
| apollox.png (photo-like card) | 744K | 404K (54%) | 32K (4%) | 47.9 dB | 32 |
| bnl-web-01.png (dark UI, text) | 551K | 310K (56%) | 158K (29%) | 36.8 dB | 159 |
| borrow-02.png (flat UI) | 156K | 41K (27%) | 103K (66%) | 42.7 dB | 107 |
| tw-feedback.png | 527K | 314K (60%) | 159K (30%) | 41.0 dB | 74 |

- On UI screenshots with sharp text, lossy q95 drops to ~37 dB with per-pixel
  errors up to 159/255 — ringing around text and flat-colour banding, which is
  exactly what "professional and high res" forbids.
- On flat UI, lossy is *larger* than lossless (borrow-02).
- Lossless never loses and still halves the PNG. The one place lossy would
  win big is the photo-like 1200×1200 cards (apollox, hoyabit-landing, x-xyz,
  drift-growth) at ~48 dB — imperceptible by any normal standard, but it is a
  quality trade and the ask said none. Left as lossless; revisit only if AC
  wants those four smaller (~1.2 MB → ~0.15 MB).

## Where it lives and how it stays correct

- `scripts/make_webp_twins.py` → `patches/webp/*.webp` + `manifest.json`
  (SHA-256 of the source PNG and of the twin). Idempotent; `--check` mode.
- `integrate_2026.py` copies the twins into `site/images` **only** when the
  PNG's hash still matches, Ceci does not ship her own twin, and the twin
  matches the manifest. Each of those failing is a build ERROR naming the fix
  (re-run the generator). All three gates plus `--check` were verified against
  deliberately broken input on 2026-10-13.
- `patches/webp/`, not `2026 portfolio/images/`: her export folder is
  rsync'd `--delete` on every drop, so anything we put there would vanish.
- The PNGs stay deployed (og:image must remain PNG for chat scrapers).

**After every drop from Ceci:** `python3 scripts/make_webp_twins.py` then
`python3 integrate_2026.py`. The build errors if you forget and a PNG changed.

Pillow with WebP support is required by the generator. It is present in the
cloud sessions; on Albert's Mac it would be a new dependency → ECVP vetting
before any `pip install`. Run the generator in a cloud session instead.

## FINDING for AC — Ceci's own 50 twins are lossy, and 9 are low

Measured her twins against her PNGs (same metric as above). Her twins are
served today and were visually accepted on 2026-09-08 ("indistinguishable at
3× magnification"). By the numbers, 23 of 50 are below 40 dB and these 9 are
in clearly-visible territory for UI screenshots:

| her twin | PSNR | max err | PNG → WebP |
|---|---:|---:|---|
| app-07.webp | 30.8 dB | 125 | 109K → 48K |
| app-03.webp | 31.4 dB | 123 | 54K → 23K |
| app-05.webp | 31.4 dB | 125 | 102K → 21K |
| app-04.webp | 31.5 dB | 124 | 64K → 18K |
| growth-campaigns.webp | 31.7 dB | 153 | 371K → 50K |
| airdrop-02.webp | 32.6 dB | 255 | 631K → 83K |
| airdrop-01.webp | 32.7 dB | 255 | 613K → 73K |
| discovery-after.webp | 33.5 dB | 227 | 86K → 17K |
| bnf-iteration-01.webp | 33.9 dB | 180 | 596K → 95K |

The rest sit at 37–46 dB (fine at display size). Full table in the session
log of 2026-10-13.

**Acted on (AC, same day: "fix her 9 low quality webp images too").** The
generator now measures every twin of hers; below `OVERRIDE_BELOW_DB = 35.0`
it emits a lossless replacement that the build serves instead of hers. 35 dB
was chosen because it catches exactly these 9 and nothing else (the next of
hers is 36.8 dB). Each override row pins the SHA-256 of *her* twin: when she
re-exports that image the build refuses the stale override until the
generator re-measures, and a re-export at or above 35 dB simply wins back.
Verified against broken input: a changed twin of hers → build error; a
lossless re-export of hers → override dropped on the next generator run; her
original restored → override returns.

Byte cost of the 9 overrides: 432 KB (hers) → 1518 KB (ours, lossless), i.e.
about +1.1 MB spread over the pages that use them. Site total is now
15.8 MB (before today) → 11.0 MB (lossless twins) → 12.1 MB (with overrides).

The 14 of her twins between 36.8 and 40 dB were left as hers: at display size
they are fine, and the bar is deliberately set at the visible cases only.

Alternative for the long run: ask Ceci to re-export those 9 at WebP
quality ≥ 90 — a good re-export of hers replaces our override automatically.

## GLOBAL CANDIDATE

- "Lossy is fine" is a per-image claim. Measure PSNR / max error per file; on
  UI screenshots the floor is ~40 dB, and flat UI often compresses *better*
  losslessly. Default to lossless for portfolio/design work unless told
  otherwise.
- Generated assets never live inside a folder that is rsync'd `--delete` from
  someone else's export. Put them beside it with a manifest that pins the
  source's hash, and make the build refuse on drift.
