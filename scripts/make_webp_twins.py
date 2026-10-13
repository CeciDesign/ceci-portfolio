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
ENCODE = dict(lossless=True, quality=100, method=6)   # method 6 = slowest, smallest


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_manifest():
    if MANIFEST.exists():
        return json.loads(MANIFEST.read_text(encoding="utf-8"))
    return {}


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


def main(check_only=False):
    OUT.mkdir(parents=True, exist_ok=True)
    manifest = load_manifest()
    pngs = {p.name: p for p in SRC.glob("*.png")}
    her_twins = {p.stem for p in SRC.glob("*.webp")}
    wanted = {n: p for n, p in pngs.items() if p.stem not in her_twins}

    problems, changed = [], 0

    # 1. drop manifest rows / files whose reason is gone
    for name in sorted(manifest):
        stem = name[:-4]
        why = None
        if name not in pngs:
            why = "PNG no longer in her export"
        elif stem in her_twins:
            why = "Ceci now ships her own twin (hers wins)"
        if why:
            if check_only:
                problems.append(f"{name}: twin is stale — {why}; re-run make_webp_twins.py")
                continue
            (OUT / f"{stem}.webp").unlink(missing_ok=True)
            del manifest[name]
            changed += 1
            print(f"removed {stem}.webp — {why}")

    # 2. stray files in patches/webp without a manifest row
    for f in sorted(OUT.glob("*.webp")):
        if f"{f.stem}.png" not in manifest:
            if check_only:
                problems.append(f"patches/webp/{f.name}: no manifest row; re-run make_webp_twins.py")
            else:
                f.unlink()
                changed += 1
                print(f"removed stray {f.name}")

    # 3. (re)generate where missing or where the PNG changed
    for name, png in sorted(wanted.items()):
        stem = name[:-4]
        twin = OUT / f"{stem}.webp"
        digest = sha256(png)
        row = manifest.get(name)
        current = (row is not None and row.get("png_sha256") == digest
                   and (twin.exists() or row.get("kept_png")))
        if current:
            if twin.exists() and row.get("webp_sha256") != sha256(twin):
                current = False
        if current:
            continue
        if check_only:
            problems.append(f"{name}: twin missing or PNG changed since it was made; "
                            "re-run make_webp_twins.py")
            continue
        data = encode_exact(png)
        png_bytes = png.stat().st_size
        ratio = len(data) / png_bytes
        if ratio >= KEEP_BELOW:
            twin.unlink(missing_ok=True)
            manifest[name] = {"png_sha256": digest, "png_bytes": png_bytes,
                              "kept_png": True, "webp_bytes": len(data),
                              "note": f"lossless twin would be {ratio:.0%} of the PNG — not worth serving"}
            print(f"{name}: kept PNG (lossless twin {ratio:.0%} of PNG, below the bar)")
        else:
            twin.write_bytes(data)
            manifest[name] = {"png_sha256": digest, "png_bytes": png_bytes,
                              "webp_bytes": len(data), "webp_sha256": sha256(twin),
                              "mode": "lossless", "pixel_exact": True}
            print(f"{name}: {png_bytes // 1024} KB -> {len(data) // 1024} KB "
                  f"({ratio:.0%}), lossless, pixel-exact")
        changed += 1

    if check_only:
        if problems:
            print("\n".join(problems))
            return 1
        print(f"webp twins: manifest current ({len(manifest)} rows)")
        return 0

    MANIFEST.write_text(json.dumps(manifest, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    served = [r for r in manifest.values() if not r.get("kept_png")]
    before = sum(r["png_bytes"] for r in served)
    after = sum(r["webp_bytes"] for r in served)
    print(f"\n{len(served)} twin(s) in patches/webp/: {before // 1024} KB of PNG -> "
          f"{after // 1024} KB of lossless WebP"
          + (f" (-{100 - after * 100 // before}%)" if before else "")
          + f"; {len(manifest) - len(served)} kept as PNG; {changed} change(s) this run")
    return 0


if __name__ == "__main__":
    sys.exit(main(check_only="--check" in sys.argv[1:]))
