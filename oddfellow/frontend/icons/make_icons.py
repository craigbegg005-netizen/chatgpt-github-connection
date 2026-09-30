#!/usr/bin/env python3
"""
Generate the Oddfellow PWA icons, reproducibly.

The orb is the app's identity mark and is defined in index.html as:

    radial-gradient(circle at 35% 30%, #fff, #aebdcc 22%, #354558 56%, #111822 72%)

This script renders the same gradient to PNG so the home-screen icon matches the
in-app mark instead of being an unrelated asset someone has to hunt for.

    pip install pillow
    python icons/make_icons.py

Outputs (all committed, so a build step is not required):
    icons/icon-192.png              standard
    icons/icon-512.png              standard
    icons/icon-maskable-512.png     extra padding for Android adaptive masking
    icons/apple-touch-icon.png      180x180, opaque, for iOS home screen
"""

import math
import os

from PIL import Image, ImageDraw

BG = (11, 13, 17)
STOPS = [
    (0.00, (255, 255, 255)),
    (0.22, (174, 189, 204)),
    (0.56, (53, 69, 88)),
    (0.72, (17, 24, 34)),
]
EDGE = (8, 10, 13)


def lerp(a, b, t):
    return tuple(int(round(a[i] + (b[i] - a[i]) * t)) for i in range(3))


def sample(radius_fraction):
    """Colour of the orb at a given fraction of its radius."""
    for i in range(len(STOPS) - 1):
        p0, c0 = STOPS[i]
        p1, c1 = STOPS[i + 1]
        if radius_fraction <= p1:
            t = 0.0 if p1 == p0 else (radius_fraction - p0) / (p1 - p0)
            return lerp(c0, c1, max(0.0, min(1.0, t)))
    return EDGE


def render(size, orb_fraction, supersample=3):
    """
    Draw the orb so it matches the CSS mark.

    Two details matter and are easy to get wrong:

    * The orb itself is a circle centred on the canvas. The light source is
      offset *inside* it at 35% 30% of the orb's box -- it is not the centre of
      the circle. Centring the gradient on the light source shifts the whole
      mark up and to the left.
    * CSS `radial-gradient(circle at ...)` with no explicit size defaults to
      `farthest-corner`, so the stop scale runs to the distance from the light
      source to the farthest corner (~0.955 x the orb's diameter), not to its
      radius. Using the radius as the scale makes the mark far too bright.

    orb_fraction is the orb's diameter as a fraction of the canvas. Standard
    icons use ~0.86; maskable icons use ~0.62 so Android's adaptive mask has
    safe space and never crops the mark.
    """
    big = size * supersample
    img = Image.new("RGB", (big, big), BG)
    draw = ImageDraw.Draw(img)

    diameter = big * orb_fraction
    cx = cy = big * 0.5
    radius = diameter / 2.0
    grad_radius = diameter * 0.955          # farthest-corner, as CSS computes it
    lx = cx + (0.35 - 0.5) * diameter       # light source, inside the orb
    ly = cy + (0.30 - 0.5) * diameter

    # Soft outer glow first; the orb is painted over the middle of it.
    steps = 30
    for i in range(steps, 0, -1):
        t = i / steps
        r = radius * (1.0 + 0.34 * t)
        alpha = (1.0 - t) * 0.30
        col = tuple(int(BG[c] + (125 - BG[c]) * alpha) for c in range(3))
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=col)

    px = img.load()
    r2 = radius * radius
    for y in range(big):
        dy2 = (y - cy) ** 2
        if dy2 > r2:
            continue
        for x in range(big):
            if (x - cx) ** 2 + dy2 > r2:
                continue
            d = math.hypot(x - lx, y - ly)
            px[x, y] = sample(d / grad_radius)

    return img.resize((size, size), Image.LANCZOS)


def main():
    here = os.path.dirname(os.path.abspath(__file__))

    def save(img, name, **kw):
        path = os.path.join(here, name)
        img.save(path, "PNG", optimize=True, **kw)
        print("wrote %s (%dx%d, %d bytes)" % (name, img.width, img.height,
                                              os.path.getsize(path)))

    save(render(192, 0.86), "icon-192.png")
    save(render(512, 0.86), "icon-512.png")
    save(render(512, 0.62), "icon-maskable-512.png")
    save(render(180, 0.80), "apple-touch-icon.png")


if __name__ == "__main__":
    main()
