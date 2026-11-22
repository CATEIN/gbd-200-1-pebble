#!/usr/bin/env python3
"""Builds resources/images/menu_icon.png: a 25x25 miniature of the face - the
octagon LCD panel with the time and its two divider lines.

Run from the project root: python3 tools/make_icon.py
"""
import os

from PIL import Image, ImageDraw

import gen_glyphs

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SIZE = 25
PANEL = (85, 85, 85, 255)  # GColorDarkGray
INK = (255, 255, 255, 255)

# 3x5 digits for the miniature time.
DIGITS = {
    '1': ['.#.', '##.', '.#.', '.#.', '###'],
    '0': ['###', '#.#', '#.#', '#.#', '###'],
    '5': ['###', '#..', '###', '..#', '###'],
    '8': ['###', '#.#', '###', '#.#', '###'],
    ':': ['.', '#', '.', '#', '.'],
}


def main():
    icon = Image.new('RGBA', (SIZE, SIZE), (0, 0, 0, 0))
    draw = ImageDraw.Draw(icon)
    # The panel octagon, fitted to the icon's width and centered vertically.
    xs = [x for x, _ in gen_glyphs.PANEL_CORNERS]
    ys = [y for _, y in gen_glyphs.PANEL_CORNERS]
    sx = (SIZE - 1) / (max(xs) - min(xs))
    height = (max(ys) - min(ys)) * sx
    top = (SIZE - 1 - height) / 2
    draw.polygon([(round((x - min(xs)) * sx), round(top + (y - min(ys)) * sx))
                  for x, y in gen_glyphs.PANEL_CORNERS], fill=PANEL)
    # Divider lines where the face has them: full width above the time,
    # left part below it.
    draw.line([(4, 7), (20, 7)], fill=INK)
    draw.line([(4, 17), (13, 17)], fill=INK)
    x = 4
    for ch in '10:58':
        rows = DIGITS[ch]
        for y, row in enumerate(rows):
            for dx, c in enumerate(row):
                if c == '#':
                    icon.putpixel((x + dx, 10 + y), INK)
        x += len(rows[0]) + 1
    icon.save(os.path.join(ROOT, 'resources', 'images', 'menu_icon.png'))


if __name__ == '__main__':
    main()
