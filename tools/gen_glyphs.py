#!/usr/bin/env python3
"""Builds src/c/glyphs.auto.h: every shape on the GBD-200 face as a dot bitmap.

Shapes are measured from a photo of the real watch, one '#' per LCD dot.
Digits the photo doesn't show (2, 3, 4, 6, 7, 9 and most of the weekday
letters) are drawn in the same style as the ones it does.

Run from the project root: python3 tools/gen_glyphs.py
"""
import os

import scale_plan


class Bitmap:
    def __init__(self, w, h):
        self.w, self.h = w, h
        self.px = [[False] * w for _ in range(h)]

    def fill(self, x0, x1, y0, y1, on=True):
        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1):
                self.px[y][x] = on

    def clear(self, x0, x1, y0, y1):
        self.fill(x0, x1, y0, y1, False)

    # Knocks a stepped curve out of an outer corner: insets[i] dots are
    # cleared from the side on the i-th row in from the top/bottom.
    def round(self, corner, insets):
        for i, n in enumerate(insets):
            y = i if corner[0] == 't' else self.h - 1 - i
            for k in range(n):
                x = k if corner[1] == 'l' else self.w - 1 - k
                self.px[y][x] = False

    # Pinches one side in over rows y0.. by insets (the 8's waist).
    def pinch(self, side, y0, insets):
        for i, n in enumerate(insets):
            for k in range(n):
                x = k if side == 'l' else self.w - 1 - k
                self.px[y0 + i][x] = False

    def vflip(self):
        b = Bitmap(self.w, self.h)
        b.px = [row[:] for row in reversed(self.px)]
        return b

    def rot180(self):
        b = Bitmap(self.w, self.h)
        b.px = [row[::-1] for row in reversed(self.px)]
        return b


def from_art(art):
    rows = [r for r in art.strip('\n').split('\n')]
    w = max(len(r) for r in rows)
    b = Bitmap(w, len(rows))
    for y, r in enumerate(rows):
        for x, c in enumerate(r):
            b.px[y][x] = c == '#'
    return b


# ---- Big time digits: 27x43, 8-dot uprights, 6-dot bars ------------------

def big_digits():
    W, H, V = 27, 43, 8
    R = [3, 1]
    L, Rt = (0, V - 1), (W - V, W - 1)
    d = {}

    b = Bitmap(W, H); b.fill(0, W - 1, 0, H - 1); b.clear(V, W - V - 1, 6, 36)
    for c in ('tl', 'tr', 'bl', 'br'): b.round(c, R)
    d['0'] = b

    b = Bitmap(W, H)
    for y, x0 in enumerate([16, 15, 13, 12, 12, 12]): b.fill(x0, 25, y, y)
    b.fill(18, 25, 6, H - 1)
    d['1'] = b

    b = Bitmap(W, H)
    b.fill(0, W - 1, 0, 5)
    b.fill(*L, 6, 16)
    b.fill(0, W - 1, 17, 23)
    b.fill(*L, 24, 24)
    b.fill(*Rt, 24, 35)
    b.fill(*L, 32, 35)
    b.fill(0, W - 1, 36, H - 1)
    b.round('bl', R); b.round('br', R)
    d['5'] = b

    b = Bitmap(W, H)
    b.fill(0, W - 1, 0, 5); b.fill(*L, 6, 8); b.fill(*Rt, 6, 17)
    b.fill(0, W - 1, 18, 23); b.fill(*L, 24, 36); b.fill(*Rt, 34, 36)
    b.fill(0, W - 1, 37, H - 1)
    b.round('tl', R); b.round('tr', R)
    for i, n in enumerate(R):  # the shoulder where the stroke turns down-left
        b.clear(0, n - 1, 18 + i, 18 + i)
    d['2'] = b

    b = Bitmap(W, H)
    b.fill(0, W - 1, 0, 5); b.fill(*L, 6, 9); b.fill(*Rt, 6, 35)
    b.fill(6, W - 1, 18, 23); b.pinch('r', 18, [1, 2, 3, 2, 1])
    b.fill(*L, 33, 35); b.fill(0, W - 1, 36, H - 1)
    for c in ('tl', 'tr', 'bl', 'br'): b.round(c, R)
    d['3'] = b

    # The 4's left stroke leans like the 7's; its crossbar runs past the
    # upright, which sits in from the right edge.
    b = Bitmap(W, H)
    for y in range(20):
        x = 10 - y // 2
        b.fill(x, x + V - 1, y, y)
    b.fill(*L, 20, 27); b.fill(0, W - 1, 28, 33); b.fill(16, 23, 0, H - 1)
    d['4'] = b

    b = Bitmap(W, H)
    b.fill(0, W - 1, 0, 5); b.fill(*L, 6, 19); b.fill(*Rt, 6, 35)
    b.fill(0, W - 1, 20, 25); b.fill(*L, 33, 35); b.fill(0, W - 1, 36, H - 1)
    for c in ('tl', 'tr', 'bl', 'br'): b.round(c, R)
    d['9'] = b

    b = Bitmap(W, H)
    b.fill(0, W - 1, 0, 5); b.fill(*Rt, 6, 9); b.fill(*L, 6, 35)
    b.fill(0, W - 1, 17, 23); b.fill(*Rt, 24, 35); b.fill(0, W - 1, 36, H - 1)
    for c in ('tl', 'tr', 'bl', 'br'): b.round(c, R)
    d['6'] = b

    # The 7's upright leans: one dot left every two rows, then straight down.
    b = Bitmap(W, H)
    b.fill(0, W - 1, 0, 5); b.fill(*L, 6, 8); b.fill(*Rt, 6, 11)
    for i in range(9):
        x = W - V - 1 - i
        b.fill(x, x + V - 1, 12 + 2 * i, 13 + 2 * i)
    b.fill(10, 10 + V - 1, 30, H - 1)
    d['7'] = b

    b = Bitmap(W, H); b.fill(0, W - 1, 0, H - 1)
    b.clear(V, W - V - 1, 6, 16); b.clear(V, W - V - 1, 23, 36)
    for c in ('tl', 'tr', 'bl', 'br'): b.round(c, R)
    b.pinch('l', 17, [1, 2, 3, 2, 1]); b.pinch('r', 17, [1, 2, 3, 2, 1])
    d['8'] = b
    return d


# ---- Seconds digits: 16x23, 5-dot uprights, 4-dot bars -------------------

def sec_digits():
    W, H, V = 16, 23, 5
    R = [2, 1]
    L, Rt = (0, V - 1), (W - V, W - 1)
    d = {}

    b = Bitmap(W, H); b.fill(0, W - 1, 0, H - 1); b.clear(V, W - V - 1, 4, 18)
    for c in ('tl', 'tr', 'bl', 'br'): b.round(c, R)
    d['0'] = b

    b = Bitmap(W, H)
    for y, x0 in enumerate([9, 8, 7, 7]): b.fill(x0, 14, y, y)
    b.fill(10, 14, 4, H - 1)
    d['1'] = b

    b = Bitmap(W, H)
    b.fill(0, W - 1, 0, 3); b.fill(*L, 4, 7); b.fill(0, W - 1, 8, 11)
    b.fill(*L, 12, 12); b.fill(*Rt, 12, 18); b.fill(*L, 17, 18)
    b.fill(0, W - 1, 19, H - 1)
    b.round('bl', R); b.round('br', R)
    d['5'] = b

    b = Bitmap(W, H)
    b.fill(0, W - 1, 0, 3); b.fill(*L, 4, 5); b.fill(*Rt, 4, 18)
    b.fill(V, W - 1, 9, 12); b.fill(*L, 16, 18); b.fill(0, W - 1, 19, H - 1)
    for c in ('tl', 'tr', 'bl', 'br'): b.round(c, R)
    d['3'] = b

    # Not on any photo yet: drawn after the big 2.
    b = Bitmap(W, H)
    b.fill(0, W - 1, 0, 3); b.fill(*L, 4, 5); b.fill(*Rt, 4, 8)
    b.fill(0, W - 1, 9, 12); b.fill(*L, 13, 18); b.fill(*Rt, 16, 18)
    b.fill(0, W - 1, 19, H - 1)
    b.round('tl', R); b.round('tr', R)
    for i, n in enumerate(R):
        b.clear(0, n - 1, 9 + i, 9 + i)
    d['2'] = b

    b = Bitmap(W, H)
    for y in range(15):
        x = max(0, 6 - (y + 1) // 2)
        b.fill(x, x + V - 1, y, y)
    b.fill(0, W - 1, 15, 18); b.fill(9, 13, 0, H - 1)
    d['4'] = b

    b = Bitmap(W, H)
    b.fill(0, W - 1, 0, 3); b.fill(*L, 4, 10); b.fill(*Rt, 4, 18)
    b.fill(0, W - 1, 11, 14); b.fill(*L, 17, 18); b.fill(0, W - 1, 19, H - 1)
    for c in ('tl', 'tr', 'bl', 'br'): b.round(c, R)
    d['9'] = b
    d['6'] = d['9'].rot180()

    b = Bitmap(W, H)
    b.fill(0, W - 1, 0, 3); b.fill(*L, 4, 4); b.fill(*Rt, 4, 7)
    for i in range(4):
        x = W - V - 1 - i
        b.fill(x, x + V - 1, 8 + 2 * i, 9 + 2 * i)
    b.fill(6, 6 + V - 1, 16, H - 1)
    d['7'] = b

    b = Bitmap(W, H); b.fill(0, W - 1, 0, H - 1)
    b.clear(V, W - V - 1, 4, 8); b.clear(V, W - V - 1, 13, 18)
    for c in ('tl', 'tr', 'bl', 'br'): b.round(c, R)
    b.pinch('l', 10, [1, 1]); b.pinch('r', 11, [1])
    d['8'] = b
    return d


# ---- Date digits: 11x15, 3-dot strokes -----------------------------------

DATE_ART = {
    '0': """
..#######..
###########
###########
###.....###
###.....###
###.....###
###.....###
###.....###
###.....###
###.....###
###.....###
###.....###
###########
###########
..#######..""",
    '1': """
......####.
....######.
....######.
.......###.
.......###.
.......###.
.......###.
.......###.
.......###.
.......###.
.......###.
.......###.
.......###.
.......###.
.......###.""",
    '2': """
..#######..
###########
###########
###.....###
........###
........###
......#####
....#######
..#######..
#######....
#####......
###........
###########
###########
###########""",
    '3': """
..#######..
###########
###########
###.....###
........###
........###
....######.
....######.
........###
........###
........###
###.....###
###########
###########
..#######..""",
    '4': """
###.....###
###.....###
###.....###
###.....###
###.....###
###.....###
###########
###########
........###
........###
........###
........###
........###
........###
........###""",
    '5': """
###########
###########
###########
###........
###........
###########
###########
###.....###
........###
........###
........###
###.....###
###########
###########
..#######..""",
    '6': """
..#######..
###########
###########
###.....###
###........
###........
#########..
###########
###.....###
###.....###
###.....###
###.....###
###########
###########
..#######..""",
    '7': """
###########
###########
###########
###.....###
###.....###
.......###.
.......###.
.......###.
......###..
......###..
......###..
.....###...
.....###...
.....###...
.....###...""",
    '8': """
..#######..
###########
###########
###.....###
###.....###
###.....###
.#########.
.#########.
###.....###
###.....###
###.....###
###.....###
###########
###########
..#######..""",
}


def date_digits():
    d = {k: from_art(v) for k, v in DATE_ART.items()}
    d['9'] = d['6'].rot180()
    return d


SLASH = """
......#
......#
.....##
.....#.
....##.
....#..
...##..
...#...
..##...
..#....
.##....
.#.....
##.....
#......
#......"""

# ---- Weekday letters: 15 tall, 3-dot strokes -----------------------------

LETTER_ART = {
    'W': """
###.......###
###..###..###
###..###..###
###..###..###
###..###..###
###..###..###
###..###..###
###..###..###
###..###..###
###..###..###
###..###..###
###..###..###
.###########.
.#####.#####.
..###...###..""",
    'M': """
..###...###..
.#####.#####.
.###########.
###..###..###
###..###..###
###..###..###
###..###..###
###..###..###
###..###..###
###..###..###
###..###..###
###..###..###
###..###..###
###..###..###
###.......###""",
    'E': """
###########
###########
###########
###........
###........
###........
#########..
#########..
#########..
###........
###........
###........
###########
###########
###########""",
    'F': """
###########
###########
###########
###........
###........
###........
#########..
#########..
#########..
###........
###........
###........
###........
###........
###........""",
    'D': """
#########..
##########.
##########.
###....####
###.....###
###.....###
###.....###
###.....###
###.....###
###.....###
###.....###
###....####
##########.
##########.
#########..""",
    'O': """
..#######..
.#########.
.#########.
####...####
###.....###
###.....###
###.....###
###.....###
###.....###
###.....###
###.....###
####...####
.#########.
.#########.
..#######..""",
    'U': """
###.....###
###.....###
###.....###
###.....###
###.....###
###.....###
###.....###
###.....###
###.....###
###.....###
###.....###
####...####
###########
.#########.
..#######..""",
    'S': """
..#######..
.#########.
###########
###.....###
###........
###........
.########..
..########.
.......####
........###
........###
###.....###
###########
.#########.
..#######..""",
    'N': """
###.....###
####....###
####....###
#####...###
###.#...###
###.##..###
###..#..###
###..##.###
###...#.###
###...#####
###....####
###....####
###.....###
###.....###
###.....###""",
    'T': """
###########
###########
###########
....###....
....###....
....###....
....###....
....###....
....###....
....###....
....###....
....###....
....###....
....###....
....###....""",
    'H': """
###.....###
###.....###
###.....###
###.....###
###.....###
###.....###
###########
###########
###########
###.....###
###.....###
###.....###
###.....###
###.....###
###.....###""",
    'R': """
#########..
##########.
###########
###....####
###.....###
###.....###
###.....###
###########
###########
##########.
#########..
###..####..
###...####.
###....####
###.....###""",
    'I': """
###
###
###
###
###
###
###
###
###
###
###
###
###
###
###""",
    'A': """
...#####...
..#######..
.#########.
###########
####...####
###.....###
###.....###
###.....###
###.....###
###########
###########
###########
###.....###
###.....###
###.....###""",
}

# ---- Marks and icons -----------------------------------------------------

ICON_ART = {
    'DST': """
#####...#####.######
##..##.##.......##..
##..##.##.......##..
##..##..####....##..
##..##.....##...##..
##..##.....##...##..
#####..#####....##..""",
    'P': """
##########.
###########
###.....###
###.....###
###.....###
###########
##########.
###........
###........
###........""",
    'COLON_DOT': """
.#####.
#######
#######
#######
#######
#######
#######
#######
#######
#######
#######
.#####.""",
    'BT': """
..#..
..##.
#.#.#
.###.
..#..
.###.
#.#.#
..##.
..#..""",
    # The watch shows its notification count inside, as dark digits; Pebble
    # apps can't read notifications, so it is drawn without one.
    'BUBBLE': """
.###########.
#############
#############
#############
#############
#############
.###########.
...##........
...#.........""",
    'SNZ': """
.###.#...#.####
##...##..#....#
##...#.#.#...##
.##..#.#.#..##.
..##.#..##.##..
..##.#...#.#...
###..#...#.####""",
    'SIGNAL': """
####...##..##..#.
#####...##..#...#
######..##..##..#
######..##..##..#
######..##..##..#
#####...##..#...#
####...##..##..#.""",
    'MUTE': """
....##...
#...#.#..
.#..#..#.
..#.#..##
...#...##
....#..#.
.....#...
.####.#..
#####..#.
.###.....""",
    'VIB': """
#.#.#.#.#.#.#
.#.#.#.#.#.#.
.............
#...#.#.####.
#...#.#.#...#
#...#.#.####.
.#.#..#.#...#
..#...#.####.
.............
.#.#.#.#.#.#.
#.#.#.#.#.#.#""",
    'PLANE': """
....#........
....##.......
#....##......
##....##.....
#############
#############
##....##.....
#....##......
....##.......
....#........""",
    'ALERT': """
....####....
..########..
.####..####.
.####..####.
#####..#####
#####..#####
#####..#####
############
#####..#####
.####..####.
..########..
....####....""",
    'LT': """
#....#####
#....#####
#......#..
#......#..
#......#..
#####..#..
#####..#..""",
}


# ---- Case printing (drawn around the LCD) -------------------------------
# Sized in LCD dots from the product photo: "CASIO" above the display is 8
# dots tall with 2-dot strokes, "WR20BAR" below it 6 dots tall. PEBBLE uses
# CASIO's letter style; W, R and 0 are traced from WR20BAR, 3 and M match.

LOGO_ART = {
    'P': """
#######.
########
##....##
##....##
########
#######.
##......
##......""",
    'E': """
########
########
##......
#######.
#######.
##......
########
########""",
    'B': """
#######.
########
##....##
#######.
########
##....##
########
#######.""",
    'L': """
##......
##......
##......
##......
##......
##......
########
########""",
}

WR_ART = {
    'W': """
##...##...##
##..####..##
##..####..##
.##.#..#.##.
.####..####.
..##....##..""",
    'R': """
#######.
##....##
##....##
#######.
##...##.
##....##""",
    '3': """
#######.
......##
..#####.
......##
##....##
.######.""",
    '0': """
.######.
###..###
##....##
##....##
##....##
.######.""",
    'M': """
..##....##..
.####..####.
.##.#..#.##.
##..####..##
##..####..##
##...##...##""",
}


# ---- Time zone abbreviation: the DST label's style (7 dots tall, 2-dot
# uprights, 1-dot bars), so a zone like "EST" reads like "DST" does.

TZ_FONT_ART = {
    'A': """
.####.
##..##
##..##
######
##..##
##..##
##..##""",
    'B': """
#####.
##..##
##..##
#####.
##..##
##..##
#####.""",
    'C': """
.####.
##..##
##....
##....
##....
##..##
.####.""",
    'D': """
#####.
##..##
##..##
##..##
##..##
##..##
#####.""",
    'E': """
######
##....
##....
#####.
##....
##....
######""",
    'F': """
######
##....
##....
#####.
##....
##....
##....""",
    'G': """
.####.
##..##
##....
##.###
##..##
##..##
.####.""",
    'H': """
##..##
##..##
##..##
######
##..##
##..##
##..##""",
    'I': """
######
..##..
..##..
..##..
..##..
..##..
######""",
    'J': """
....##
....##
....##
....##
##..##
##..##
.####.""",
    'K': """
##..##
##.##.
####..
###...
####..
##.##.
##..##""",
    'L': """
##....
##....
##....
##....
##....
##....
######""",
    'M': """
##...##
###.###
##.#.##
##.#.##
##...##
##...##
##...##""",
    'N': """
##..##
###.##
######
##.###
##..##
##..##
##..##""",
    'O': """
.####.
##..##
##..##
##..##
##..##
##..##
.####.""",
    'P': """
#####.
##..##
##..##
#####.
##....
##....
##....""",
    'Q': """
.####.
##..##
##..##
##..##
##.###
##..##
.###.#""",
    'R': """
#####.
##..##
##..##
#####.
##.##.
##..##
##..##""",
    'S': """
.#####
##....
##....
.####.
....##
....##
#####.""",
    'T': """
######
..##..
..##..
..##..
..##..
..##..
..##..""",
    'U': """
##..##
##..##
##..##
##..##
##..##
##..##
.####.""",
    'V': """
##..##
##..##
##..##
##..##
.####.
.####.
..##..""",
    'W': """
##...##
##...##
##...##
##.#.##
##.#.##
###.###
##...##""",
    'X': """
##..##
##..##
.####.
..##..
.####.
##..##
##..##""",
    'Y': """
##..##
##..##
.####.
..##..
..##..
..##..
..##..""",
    'Z': """
######
....##
...##.
..##..
.##...
##....
######""",
    '0': """
.####.
##..##
##..##
##..##
##..##
##..##
.####.""",
    '1': """
..##..
.###..
..##..
..##..
..##..
..##..
.####.""",
    '2': """
.####.
##..##
....##
...##.
..##..
.##...
######""",
    '3': """
#####.
....##
....##
.####.
....##
....##
#####.""",
    '4': """
...##.
..###.
.####.
##.##.
######
...##.
...##.""",
    '5': """
######
##....
#####.
....##
....##
##..##
.####.""",
    '6': """
.####.
##....
##....
#####.
##..##
##..##
.####.""",
    '7': """
######
....##
...##.
..##..
..##..
..##..
..##..""",
    '8': """
.####.
##..##
##..##
.####.
##..##
##..##
.####.""",
    '9': """
.####.
##..##
##..##
.#####
....##
....##
.####.""",
    '+': """
......
..##..
..##..
######
..##..
..##..
......""",
    '-': """
......
......
......
######
......
......
......""",
}


# ---- Button labels along the screen edges ---------------------------------
# The watch prints FWD/REV/RUN/BACK beside its buttons, running along the
# display edge with a triangle pointing at the button. These are drawn 1:1 in
# screen pixels, 6 tall in WR30M's style (2-pixel uprights, 1-pixel bars) -
# a little smaller than WR30M at real size; '^' is the triangle.

LABEL_FONT_ART = {
    'R': "#####.\n##..##\n##..##\n#####.\n##.##.\n##..##",
    'E': "######\n##....\n##....\n#####.\n##....\n######",
    'V': "##..##\n##..##\n##..##\n.####.\n.####.\n..##..",
    'U': "##..##\n##..##\n##..##\n##..##\n##..##\n.####.",
    'P': "#####.\n##..##\n##..##\n#####.\n##....\n##....",
    'D': "#####.\n##..##\n##..##\n##..##\n##..##\n#####.",
    'O': ".####.\n##..##\n##..##\n##..##\n##..##\n.####.",
    'W': "##....##\n##....##\n##.##.##\n##.##.##\n.######.\n.##..##.",
    'N': "##..##\n###.##\n######\n##.###\n##..##\n##..##",
    '^': "......\n..##..\n.####.\n######\n......\n......",
}


def label_bitmap(text, side):
    """Lays text out left to right, then turns it to run along a screen edge:
    on the left it reads bottom to top, on the right top to bottom, with the
    letters' tops (and the triangle) facing the edge, like the watch's."""
    glyphs = [from_art(LABEL_FONT_ART[c]) for c in text]
    w = sum(g.w for g in glyphs) + len(glyphs) - 1
    flat = Bitmap(w, max(g.h for g in glyphs))
    x = 0
    for g in glyphs:
        for y in range(g.h):
            for gx in range(g.w):
                flat.px[y][x + gx] = g.px[y][gx]
        x += g.w + 1
    out = Bitmap(flat.h, flat.w)
    for r in range(out.h):
        for c in range(out.w):
            if side == 'left':  # 90 degrees counter-clockwise
                out.px[r][c] = flat.px[c][flat.w - 1 - r]
            else:               # 90 degrees clockwise
                out.px[r][c] = flat.px[flat.h - 1 - c][r]
    return out


LABELS = {'REV': ('REV^', 'left'), 'UP': ('^UP', 'right'), 'RUN': ('^', 'right'),  # RUN: the triangle alone
          'DOWN': ('DOWN^', 'right')}

# The seconds digits' minus sign and a degree mark, for temperature.
SEC_MINUS = """
................
................
................
................
................
................
................
................
................
................
..############..
..############..
..############..
..############..
................
................
................
................
................
................
................
................
................"""

DEGREE = """
.##.
#..#
#..#
.##."""


# ---- LCD panel outline -----------------------------------------------------
# The octagon behind the display, measured in dots from the product photo
# (symmetric about x = 87.5), with its corners rounded off.

PANEL_CORNERS = [(27, 3), (148, 3), (172, 42), (172, 96), (149, 129), (26, 129), (3, 96), (3, 42)]
PANEL_RADIUS = 5   # corner radius, in dots
ARC_STEPS = 6      # straight segments per rounded corner


def rounded_outline(corners, radius, steps):
    """Replaces each corner of a convex polygon with a circular arc of the
    given radius, tangent to both edges."""
    import math
    out = []
    n = len(corners)
    for i, (cx, cy) in enumerate(corners):
        px, py = corners[i - 1]
        nx, ny = corners[(i + 1) % n]
        ux, uy = cx - px, cy - py
        vx, vy = nx - cx, ny - cy
        lu, lv = math.hypot(ux, uy), math.hypot(vx, vy)
        ux, uy, vx, vy = ux / lu, uy / lu, vx / lv, vy / lv
        theta = math.acos(max(-1.0, min(1.0, -ux * vx - uy * vy)))  # interior angle
        t = min(radius / math.tan(theta / 2), lu / 2, lv / 2)
        r = t * math.tan(theta / 2)
        a = (cx - ux * t, cy - uy * t)  # where the arc leaves the incoming edge
        b = (cx + vx * t, cy + vy * t)  # where it joins the outgoing edge
        bx, by = -ux + vx, -uy + vy     # bisector, pointing into the polygon
        bl = math.hypot(bx, by)
        d = r / math.sin(theta / 2)
        ox, oy = cx + bx / bl * d, cy + by / bl * d
        a0 = math.atan2(a[1] - oy, a[0] - ox)
        a1 = math.atan2(b[1] - oy, b[0] - ox)
        while a1 < a0:
            a1 += 2 * math.pi
        if a1 - a0 > math.pi:
            a1 -= 2 * math.pi
        for k in range(steps + 1):
            ang = a0 + (a1 - a0) * k / steps
            out.append((ox + r * math.cos(ang), oy + r * math.sin(ang)))
    return out


def emit(path):
    groups = []  # (c array name, [(label, Bitmap)])
    big, sec, date = big_digits(), sec_digits(), date_digits()
    date['/'] = from_art(SLASH)
    groups.append(('BIG_DIGITS', [(str(i), big[str(i)]) for i in range(10)]))
    groups.append(('SEC_DIGITS', [(str(i), sec[str(i)]) for i in range(10)]))
    groups.append(('DATE_DIGITS', [(str(i), date[str(i)]) for i in range(10)]))
    letters = {k: from_art(v) for k, v in LETTER_ART.items()}
    icons = {k: from_art(v) for k, v in ICON_ART.items()}
    logo = {k: from_art(v) for k, v in LOGO_ART.items()}
    tz = {k: from_art(v) for k, v in TZ_FONT_ART.items()}
    labels = {k: label_bitmap(*v) for k, v in LABELS.items()}
    sec_minus, degree = from_art(SEC_MINUS), from_art(DEGREE)
    wr = {k: from_art(v) for k, v in WR_ART.items()}

    # Glyphs that are drawn side by side and must scale identically share a
    # family: the digits of one size, letters of one width, each icon alone.
    families = []  # (name, [Bitmap], size weight for scale_plan)
    fam_of = {}

    def family(name, bitmaps, size_weight=scale_plan.TEXT_SIZE_WEIGHT):
        fam_of.update({id(b): len(families) for b in bitmaps})
        families.append((name, bitmaps, size_weight))

    for arr, items in groups:
        family(arr, [b for _, b in items] + ([sec_minus] if arr == 'SEC_DIGITS' else []))
    family('SLASH', [date['/']])
    for w in sorted({b.w for b in letters.values()}):
        family('LETTERS_W%d' % w, [b for b in letters.values() if b.w == w])
    family('LOGO', list(logo.values()))
    for w in sorted({b.w for b in wr.values()}):
        family('WR_W%d' % w, [b for b in wr.values() if b.w == w])
    for w in sorted({b.w for b in tz.values()}):
        family('TZ_W%d' % w, [b for b in tz.values() if b.w == w])
    family('DEGREE', [degree])
    # Button labels are drawn 1:1 in screen pixels; they still need a family
    # entry because every glyph carries one.
    for k, b in labels.items():
        family('LABEL_' + k, [b], scale_plan.ICON_SIZE_WEIGHT)
    TEXT_ICONS = ('DST', 'P', 'COLON_DOT')  # read as part of the text around them
    for k, b in icons.items():
        family('ICON_' + k, [b], scale_plan.TEXT_SIZE_WEIGHT if k in TEXT_ICONS
               else scale_plan.ICON_SIZE_WEIGHT)

    out = ['// Generated by tools/gen_glyphs.py - do not edit.',
           '#pragma once', '#include <pebble.h>', '',
           '// Per family and scale (see SCALE_* in main.c): bit i of xmask/ymask set',
           '// means dot column/row i is drawn two pixels wide. Chosen by',
           '// tools/scale_plan.py to keep same-width strokes the same width.',
           '#define NUM_SCALES %d' % scale_plan.NUM_SCALES,
           '#define SCALE_INDEX_MIN_PERCENT %d' % scale_plan.PERCENTS[0],
           '#define SCALE_INDEX_FILL %d' % scale_plan.FILL,
           'typedef struct { uint8_t w, h; const uint64_t *xmask, *ymask; } Family;', '',
           '// One uint32_t per row; bit (w - 1 - x) is dot x of that row.',
           'typedef struct { uint8_t w, h, fam; const uint32_t *rows; } Glyph;', '']

    for name, bms, size_weight in families:
        xm, ym = scale_plan.plan(bms, size_weight)
        out.append('static const uint64_t FAM_%s_X[] = {%s};' % (name, ', '.join('0x%xull' % v for v in xm)))
        out.append('static const uint64_t FAM_%s_Y[] = {%s};' % (name, ', '.join('0x%xull' % v for v in ym)))
    out.append('#define NUM_FAMILIES %d' % len(families))
    out.append('static const Family FAMILIES[] = {%s};' % ', '.join(
        '{%d, %d, FAM_%s_X, FAM_%s_Y}' % (bms[0].w, bms[0].h, n, n) for n, bms, _ in families))
    out.append('#define MAX_GLYPH_W %d' % max(b.w for _, bms, _ in families for b in bms))
    out.append('#define MAX_GLYPH_H %d' % max(b.h for _, bms, _ in families for b in bms))
    out.append('')

    def rows_of(b):
        vals = []
        for r in b.px:
            v = 0
            for on in r:
                v = (v << 1) | int(on)
            vals.append('0x%x' % v)
        return vals

    def art_comment(b):
        return ['//   ' + ''.join('#' if on else '.' for on in r) for r in b.px]

    def glyph(name, b):
        out.append('// %s' % name)
        out.extend(art_comment(b))
        out.append('static const uint32_t %s_ROWS[] = {%s};' % (name, ', '.join(rows_of(b))))
        return '{%d, %d, %d, %s_ROWS}' % (b.w, b.h, fam_of[id(b)], name)

    for arr, items in groups:
        inits = [glyph('%s_%s' % (arr, label), b) for label, b in items]
        out.append('static const Glyph %s[] = {%s};' % (arr, ', '.join(inits)))
        out.append('')
    out.append('static const Glyph SLASH = %s;' % glyph('SLASH', date['/']))
    out.append('')
    for k, b in sorted(letters.items()):
        out.append('static const Glyph LETTER_%s = %s;' % (k, glyph('LETTER_%s' % k, b)))
    out.append('')
    for k, b in icons.items():
        out.append('static const Glyph ICON_%s = %s;' % (k, glyph('ICON_%s' % k, b)))
    out.append('')
    for k, b in logo.items():
        out.append('static const Glyph LOGO_%s = %s;' % (k, glyph('LOGO_%s' % k, b)))
    for k, b in wr.items():
        out.append('static const Glyph WR_%s = %s;' % (k, glyph('WR_%s' % k, b)))
    out.append('')
    out.append('static const Glyph SEC_MINUS = %s;' % glyph('SEC_MINUS', sec_minus))
    out.append('static const Glyph DEGREE = %s;' % glyph('DEGREE', degree))
    tz_names = {}
    for k, b in tz.items():
        n = 'TZ_' + ({'+': 'PLUS', '-': 'MINUS'}.get(k, k))
        tz_names[k] = n
        out.append('static const Glyph %s = %s;' % (n, glyph(n, b)))
    for k, b in labels.items():
        out.append('static const Glyph LABEL_%s = %s;' % (k, glyph('LABEL_' + k, b)))
    out.append('')
    out.append('static const Glyph *tz_glyph(char c) {')
    out.append('  switch (c) {')
    for k, n in tz_names.items():
        out.append("    case '%s': return &%s;" % (k, n))
    out.append('    default: return NULL;')
    out.append('  }')
    out.append('}')
    out.append('')
    outline = rounded_outline(PANEL_CORNERS, PANEL_RADIUS, ARC_STEPS)
    out.append('// The LCD panel octagon with rounded corners, in 1/16 dots.')
    out.append('static const int16_t PANEL_OUTLINE[][2] = {%s};' % ', '.join(
        '{%d, %d}' % (round(x * 16), round(y * 16)) for x, y in outline))
    out.append('')
    out.append('static const Glyph *letter_glyph(char c) {')
    out.append('  switch (c) {')
    for k in sorted(letters):
        out.append("    case '%s': return &LETTER_%s;" % (k, k))
    out.append('    default: return NULL;')
    out.append('  }')
    out.append('}')
    with open(path, 'w') as f:
        f.write('\n'.join(out) + '\n')


if __name__ == '__main__':
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    emit(os.path.join(root, 'src', 'c', 'glyphs.auto.h'))
