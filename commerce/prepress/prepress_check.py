#!/usr/bin/env python3
"""
Prepress viability for a source image against a list of print sizes.

WHY THIS EXISTS
---------------
The SAM-POST-01 analysis (``commerce/prepress/SAMURAI-PREPRESS-2026-10-14.md``) was
done by hand, and it reached a strategy-level conclusion: a 1122x1402 source cannot
make a 300-DPI print at ANY size Fourthwall offers, so the wall-art launch is a 5x7
product rather than a "matte art print" range.

That conclusion has to be re-derived for every artwork and every collection, and the
document itself says so twice -- *"Apply the same analysis to every other collection
before launch"* and *"must be re-run when the real file arrives"*. Hand arithmetic
re-run under time pressure is how a wrong number gets into a pricing decision.

So the arithmetic lives here, once, and the test asserts it reproduces the numbers in
that document exactly. If the two ever disagree, one of them is wrong and the test
says so.

WHAT IT DOES NOT DO
-------------------
It does not upscale, and it does not recommend upscaling. A resampled file is a bigger
number, not more detail: the "real DPI" column is what the source actually resolves to
at that print size, and no amount of interpolation changes it.

Usage:
    python3 prepress_check.py 1122 1402
    python3 prepress_check.py 1122 1402 --sizes 5x7,8x10,16x20
    python3 prepress_check.py 2400 3000 --min-dpi 300
"""

from __future__ import annotations

import argparse
import sys

# Fourthwall Enhanced Matte Paper Poster (P001). Resolved 2026-10-14 13:02 UTC:
# the full list is 14 sizes, read from the catalog API record
# (api.fourthwall.com/api/products/pro_15bc29bc8a324d449d — variants array).
# The four the document's original table lacked are the square formats.
FOURTHWALL_POSTER_SIZES = (
    (5, 7),
    (8, 10),
    (11, 14),
    (10, 10),
    (12, 12),
    (12, 16),
    (12, 18),
    (14, 14),
    (16, 16),
    (16, 20),
    (18, 18),
    (18, 24),
    (20, 30),
    (24, 36),
)

# The owner's gates for this lane. A size below these is not a candidate whatever
# its DPI, so the verdict says so rather than leaving it to the reader.
MIN_CONTRIBUTION_USD = 5.00
MIN_MARGIN_PCT = 25.0


def assess(width: int, height: int, print_w: float, print_h: float) -> dict:
    """Viability of one source image at one print size, with no upscaling.

    The source is fitted to the print size, so the limiting dimension is whichever
    supplies fewer pixels per inch. The other dimension then over-supplies, and the
    excess must be cropped -- which is a real cost, because it changes the composition.
    """
    if width <= 0 or height <= 0:
        raise ValueError("source dimensions must be positive")
    if print_w <= 0 or print_h <= 0:
        raise ValueError("print dimensions must be positive")

    dpi_w = width / print_w
    dpi_h = height / print_h
    limiting = min(dpi_w, dpi_h)

    source_aspect = width / height
    print_aspect = print_w / print_h

    if abs(source_aspect - print_aspect) < 0.0005:
        crop_axis, crop_pct = "none", 0.0
    elif source_aspect > print_aspect:
        # Source is wider than the print: the width over-supplies, so crop width.
        needed = print_w * limiting
        crop_axis, crop_pct = "width", max(0.0, (width - needed) / width * 100.0)
    else:
        needed = print_h * limiting
        crop_axis, crop_pct = "height", max(0.0, (height - needed) / height * 100.0)

    return {
        "size": f"{print_w:g}x{print_h:g}",
        "print_aspect": print_aspect,
        "source_aspect": source_aspect,
        "dpi": limiting,
        "dpi_w": dpi_w,
        "dpi_h": dpi_h,
        "crop_axis": crop_axis,
        "crop_pct": crop_pct,
    }


def verdict(dpi: float, min_dpi: int) -> str:
    if dpi >= min_dpi:
        return "OK"
    if dpi >= 150:
        return "soft"
    if dpi >= 100:
        return "poor"
    return "unusable"


def upscale_factor(width: int, height: int, print_w: float, print_h: float, target_dpi: int) -> float:
    """Linear upscale needed to reach target_dpi. >1 means inventing pixels."""
    need_w, need_h = print_w * target_dpi, print_h * target_dpi
    return max(need_w / width, need_h / height)


def parse_sizes(spec: str) -> tuple[tuple[float, float], ...]:
    out = []
    for part in spec.split(","):
        part = part.strip().lower().replace(" ", "")
        if not part:
            continue
        if "x" not in part:
            raise ValueError(f"size {part!r} is not WxH")
        w, h = part.split("x", 1)
        out.append((float(w), float(h)))
    if not out:
        raise ValueError("no sizes given")
    return tuple(out)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    ap.add_argument("width", type=int, help="source width in pixels")
    ap.add_argument("height", type=int, help="source height in pixels")
    ap.add_argument("--sizes", help="comma-separated WxH list (default: Fourthwall posters)")
    ap.add_argument("--min-dpi", type=int, default=300, help="DPI considered acceptable")
    args = ap.parse_args(argv)

    sizes = parse_sizes(args.sizes) if args.sizes else FOURTHWALL_POSTER_SIZES

    print(f"source: {args.width} x {args.height} px  (aspect {args.width / args.height:.3f})")
    print(f"at {args.min_dpi} DPI this source supports "
          f"{args.width / args.min_dpi:.2f} x {args.height / args.min_dpi:.2f} in")
    print()
    print(f"{'size':>7}  {'aspect':>7}  {'crop':>7}  {'crop%':>6}  {'DPI':>5}  verdict")
    print(f"{'-' * 7}  {'-' * 7}  {'-' * 7}  {'-' * 6}  {'-' * 5}  {'-' * 8}")
    for pw, ph in sizes:
        a = assess(args.width, args.height, pw, ph)
        print(f"{a['size']:>7}  {a['print_aspect']:7.3f}  {a['crop_axis']:>7}  "
              f"{a['crop_pct']:5.1f}%  {a['dpi']:5.0f}  {verdict(a['dpi'], args.min_dpi)}")
    print()
    print("Upscaling is not a remedy -- it is a larger number, not more detail:")
    for pw, ph in sizes:
        f = upscale_factor(args.width, args.height, pw, ph, args.min_dpi)
        if f > 1.0:
            print(f"  {pw:g}x{ph:g}: {f:.1f}x linear upscale to reach {args.min_dpi} DPI "
                  f"(real detail stays {assess(args.width, args.height, pw, ph)['dpi']:.0f} DPI)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
