#!/usr/bin/env python3
"""Generate LOSSLESS WebP twins for PNGs in Ceci's export that have none.

Why: 31 of her 81 PNGs ship without a .webp twin, ~10.5 MB on the case-study
pages and 7 of the 10 homepage images. integrate_2026.py serves a twin wherever
one exists (see PREFER_WEBP there), so twins are the whole optimisation.

Why LOSSLESS (AC, 2026-10-13: "must NOT compromise image quality — it is her
portfolio"): measured on her set, lossless WebP is 27-60% of the PNG size with
pixel-identical output (PSNR inf, SSIM 1.0). Lossy q95 gains more on the photo-
like cards (apollox: 4% of PNG, PSNR 47.9) but on UI screenshots with sharp text
it drops to PSNR ~37 dB with per-pixel errors up to 159/255 (bnl-web-01) and on
flat UI (borrow-02) it is actually LARGER than lossless. Lossless never loses
and usually wins, so it is the only mode this script emits.

Where the twins live: patches/webp/ (authored assets), NOT "2026 portfolio/"
which stays purely her export (a revision drop is rsync --delete'd over it and
would wipe anything we put there). patches/webp/manifest.json records the
SHA-256 of the PNG each twin was made from; integrate_2026.py refuses to serve
a twin whose PNG has since changed, or whose PNG now has a twin from Ceci
(hers always wins), and tells you to re-run this script.

ALSO (AC, 2026-10-13, "fix her 9 low quality webp images too"): Ceci's own
twins are lossy. Measured against her PNGs, 9 of 50 sit at 30.8-33.9 dB PSNR
with per-pixel errors up to 255 — visibly soft UI screenshots. Any twin of hers
below OVERRIDE_BELOW_DB gets a lossless twin from us that the build serves
INSTEAD of hers. The manifest pins the SHA-256 of her twin too, so the moment
she re-exports that image the override is re-measured: a good re-export wins
back automatically, a still-bad one is overridden again. The next-lowest of her
twins is 36.8 dB, so 35 dB catches exactly those 9 and nothing else.

Rules, enforced here:
  - a twin is written only if it round-trips PIXEL-EXACT (decoded RGBA == PNG);
  - a twin is kept only if it is < KEEP_BELOW of the PNG's size — a twin that
    saves nothing is just a second copy to maintain;
  - idempotent: re-running regenerates nothing that is already current, and
    removes twins whose PNG is gone or now has a twin from Ceci.

Needs Pillow with WebP support (python3 -c "from PIL import features;
print(features.check('webp'))"). Present in the cloud sessions; on a Mac it is
a NEW dependency and therefore an ECVP vetting event — do not pip-install it
on a whim, run this in a cloud session instead.

Usage: python3 scripts/make_webp_twins.py [--check]
  --check  verify the manifest against the PNGs and exit non-zero on drift,
           without encoding anything (what CI would run).
"""

import hashlib
import io
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "2026 portfolio" / "images"
OUT = ROOT / "patches" / "webp"
MANIFEST = OUT / "manifest.json"
KEEP_BELOW = 0.85      # twin must be smaller than 85% of the PNG to be worth serving
OVERRIDE_BELOW_DB = 35.0   # her lossy twin below this PSNR (vs her PNG) is replaced by ours
ENCODE = dict(lossless=True, quality=100, method=6)   # method 6 = slowest, smallest


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_manifest():
    if MANIFEST.exists():
        return json.loads(MANIFEST.read_text(encoding="utf-8"))
    return {}


def psnr_vs_png(png_path, webp_path):
    """(PSNR in dB over RGB, max abs channel error) of her twin vs her PNG;
    (None, None) if the twin does not decode or is not the same size."""
    from PIL import Image
    import numpy as np
    try:
        a = np.asarray(Image.open(png_path).convert("RGB"), dtype=np.float64)
        b = np.asarray(Image.open(webp_path).convert("RGB"), dtype=np.float64)
    except Exception:
        return None, None
    if a.shape != b.shape:
        return None, None
    mse = float(np.mean((a - b) ** 2))
    psnr = 99.0 if mse == 0 else 10 * np.log10(255 ** 2 / mse)
    return round(float(psnr), 1), int(np.abs(a - b).max())


def encode_exact(png_path):
    """Return lossless WebP bytes that decode to exactly the PNG's pixels, or
    raise if the round-trip is not pixel-exact (it always should be)."""
    from PIL import Image
    import numpy as np
    im = Image.open(png_path)
    im.load()
    src = im.convert("RGBA")
    buf = io.BytesIO()
    src.save(buf, "WEBP", exact=True, **ENCODE)
    data = buf.getvalue()
    back = Image.open(io.BytesIO(data))
    back.load()
    if back.size != src.size:
        raise RuntimeError(f"{png_path.name}: size changed {src.size} -> {back.size}")
    a, b = np.asarray(src), np.asarray(back.convert("RGBA"))
    if a.shape != b.shape or not np.array_equal(a, b):
        diff = int(np.abs(a.astype(int) - b.astype(int)).max())
        raise RuntimeError(f"{png_path.name}: NOT pixel-exact (max channel diff {diff})")
    return data


def desired_rows(pngs, her_twins):
    """What the manifest SHOULD contain, by PNG name: 'twin' rows for PNGs she
    ships without a twin, 'override' rows for her twins below the PSNR bar.
    Measuring is the only cost here; encoding happens only for stale rows."""
    want = {}
    for name, png in sorted(pngs.items()):
        stem = name[:-4]
        hers = SRC / f"{stem}.webp"
        if stem not in her_twins:
            want[name] = {"kind": "twin"}
            continue
        if hers.stat().st_size == 0:
            continue   # a zero-byte twin is handled by WEBP_SKIP in the build, not here
        db, err = psnr_vs_png(png, hers)
        if db is not None and db < OVERRIDE_BELOW_DB:
            want[name] = {"kind": "override", "hers_sha256": sha256(hers),
                          "hers_psnr_db": db, "hers_max_err": err}
    return want


def row_is_current(row, want, png, twin):
    if row is None or row.get("kind", "twin") != want["kind"]:
        return False
    if row.get("png_sha256") != sha256(png):
        return False
    if want["kind"] == "override" and row.get("hers_sha256") != want["hers_sha256"]:
        return False
    if row.get("kept_png"):
        return True
    return twin.exists() and row.get("webp_sha256") == sha256(twin)


def main(check_only=False):
    OUT.mkdir(parents=True, exist_ok=True)
    manifest = load_manifest()
    pngs = {p.name: p for p in SRC.glob("*.png")}
    her_twins = {p.stem for p in SRC.glob("*.webp")}
    want = desired_rows(pngs, her_twins)

    problems, changed = [], 0
    fix = "re-run make_webp_twins.py"

    # 1. rows whose reason is gone (PNG dropped, she now ships a good twin, ...)
    for name in sorted(set(manifest) - set(want)):
        stem = name[:-4]
        if name not in pngs:
            why = "PNG no longer in her export"
        elif manifest[name].get("kind", "twin") == "override":
            why = (f"Ceci's own {stem}.webp is now >= {OVERRIDE_BELOW_DB} dB "
                   "(or changed) — hers wins again")
        else:
            why = "Ceci now ships her own twin (hers wins)"
        if check_only:
            problems.append(f"{name}: row is stale — {why}; {fix}")
            continue
        (OUT / f"{stem}.webp").unlink(missing_ok=True)
        del manifest[name]
        changed += 1
        print(f"removed {stem}.webp — {why}")

    # 2. stray files without a row
    for f in sorted(OUT.glob("*.webp")):
        if f"{f.stem}.png" not in want:
            if check_only:
                problems.append(f"patches/webp/{f.name}: no manifest row; {fix}")
            else:
                f.unlink()
                changed += 1
                print(f"removed stray {f.name}")

    # 3. (re)generate stale or missing rows
    for name, w in sorted(want.items()):
        stem = name[:-4]
        png, twin = pngs[name], OUT / f"{stem}.webp"
        if row_is_current(manifest.get(name), w, png, twin):
            continue
        if check_only:
            problems.append(f"{name}: twin missing, or PNG/her twin changed since it was made; {fix}")
            continue
        data = encode_exact(png)
        png_bytes = png.stat().st_size
        ratio = len(data) / png_bytes
        row = {"kind": w["kind"], "png_sha256": sha256(png), "png_bytes": png_bytes,
               "webp_bytes": len(data)}
        if w["kind"] == "override":
            row.update({k: w[k] for k in ("hers_sha256", "hers_psnr_db", "hers_max_err")})
            row["hers_bytes"] = (SRC / f"{stem}.webp").stat().st_size
        if ratio >= KEEP_BELOW and w["kind"] == "twin":
            twin.unlink(missing_ok=True)
            row.update({"kept_png": True,
                        "note": f"lossless twin would be {ratio:.0%} of the PNG — not worth serving"})
            print(f"{name}: kept PNG (lossless twin {ratio:.0%} of PNG, below the bar)")
        else:
            twin.write_bytes(data)
            row.update({"webp_sha256": sha256(twin), "mode": "lossless", "pixel_exact": True})
            tag = (f"OVERRIDES hers ({w['hers_psnr_db']} dB, max err {w['hers_max_err']})"
                   if w["kind"] == "override" else "lossless, pixel-exact")
            print(f"{name}: {png_bytes // 1024} KB -> {len(data) // 1024} KB ({ratio:.0%}), {tag}")
        manifest[name] = row
        changed += 1

    if check_only:
        if problems:
            print("\n".join(problems))
            return 1
        print(f"webp twins: manifest current ({len(manifest)} rows)")
        return 0

    MANIFEST.write_text(json.dumps(manifest, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    twins = [r for r in manifest.values() if not r.get("kept_png") and r.get("kind", "twin") == "twin"]
    overs = [r for r in manifest.values() if r.get("kind") == "override"]
    b, a = sum(r["png_bytes"] for r in twins), sum(r["webp_bytes"] for r in twins)
    print(f"\n{len(twins)} twin(s) for untwinned PNGs: {b // 1024} KB of PNG -> {a // 1024} KB "
          f"of lossless WebP" + (f" (-{100 - a * 100 // b}%)" if b else ""))
    if overs:
        hb, ob = sum(r["hers_bytes"] for r in overs), sum(r["webp_bytes"] for r in overs)
        print(f"{len(overs)} override(s) of her lossy twins below {OVERRIDE_BELOW_DB} dB: "
              f"{hb // 1024} KB (hers) -> {ob // 1024} KB (ours, lossless)")
    print(f"{sum(1 for r in manifest.values() if r.get('kept_png'))} kept as PNG; "
          f"{changed} change(s) this run")
    return 0


if __name__ == "__main__":
    sys.exit(main(check_only="--check" in sys.argv[1:]))
