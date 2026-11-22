#!/usr/bin/env python3
"""Builds store/banner-720x320.png: the app's name in the face's own DST-style
lettering over three of the store screenshots.

Run from the project root after updating store/screenshots:
    python3 tools/make_banner.py
"""
import json
import os

from PIL import Image

import gen_glyphs

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SHOTS = ['emery-1-real-size.png', 'emery-3-fill-width.png', 'emery-4-original-inverted.png']
W, H = 720, 320
BACKGROUND = (17, 17, 17)
TITLE_SCALE = 5  # screen pixels per font dot


def draw_title(banner, text, top):
    glyphs = [gen_glyphs.from_art(gen_glyphs.TZ_FONT_ART[c]) for c in text.upper()
              if c in gen_glyphs.TZ_FONT_ART]
    width = (sum(g.w for g in glyphs) + len(glyphs) - 1) * TITLE_SCALE
    x = (W - width) // 2
    for g in glyphs:
        for y, row in enumerate(g.px):
            for gx, on in enumerate(row):
                if on:
                    banner.paste((255, 255, 255), (x + gx * TITLE_SCALE, top + y * TITLE_SCALE,
                                                   x + (gx + 1) * TITLE_SCALE, top + (y + 1) * TITLE_SCALE))
        x += (g.w + 1) * TITLE_SCALE


def main():
    with open(os.path.join(ROOT, 'package.json')) as f:
        name = json.load(f)['pebble']['displayName']
    banner = Image.new('RGB', (W, H), BACKGROUND)
    draw_title(banner, name, 18)
    shots = [Image.open(os.path.join(ROOT, 'store', 'screenshots', s)).convert('RGB') for s in SHOTS]
    gap = (W - sum(s.width for s in shots)) // (len(shots) + 1)
    x = gap
    for s in shots:
        banner.paste(s, (x, H - s.height - 12))
        x += s.width + gap
    banner.save(os.path.join(ROOT, 'store', 'banner-720x320.png'))


if __name__ == '__main__':
    main()
