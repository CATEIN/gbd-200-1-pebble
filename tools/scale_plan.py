"""Chooses, for each glyph family and each scale, which dot columns and rows
are drawn two pixels wide.

Scaling a dot bitmap by a non-integer factor means some dots get 2 pixels and
others 1. Picked badly, that makes twin strokes different widths or doubles one
step of a diagonal. This searches for the set that keeps every run of dots that
has the same length on the real watch at the same width on screen, without
bending the glyph's proportions, and may give a family a pixel less than the
exact scale when that is much more even (the glyph is then centered).
"""

PERCENTS = list(range(100, 137))  # custom/real-size scales, by percent
FILL = len(PERCENTS)              # index of the 4/3 fill-width scale
NUM_SCALES = len(PERCENTS) + 1


def target(n, scale_index):
    """Pixels for n dots at a scale; must match scale() in src/c/main.c."""
    if scale_index == FILL:
        return (n * 4 * 2 + 3) // 6
    p = PERCENTS[scale_index]
    return (n * p * 2 + 100) // 200


def _runs(lines):
    """Distinct (value, start, end, count) runs across a set of lines, where
    count is how many times that run occurs (a stroke spanning 30 rows counts
    30 times, so it outweighs a single diagonal step)."""
    out = {}
    for line in lines:
        i = 0
        while i < len(line):
            j = i
            while j < len(line) and line[j] == line[i]:
                j += 1
            key = (line[i], i, j)
            out[key] = out.get(key, 0) + 1
            i = j
    return sorted(k + (c,) for k, c in out.items())


def _score(runs, n, doubled, t, size_weight):
    m = [0]
    for i in range(n):
        m.append(m[-1] + (2 if i in doubled else 1))
    # Unevenness: runs whose width differs from the most common width of
    # runs with the same value and length. A run's weight is 1/length, since
    # a 1-dot line turning 2 pixels is far more visible than an 8-dot stroke
    # turning 9; gaps count half as much as lit strokes.
    groups = {}
    for v, i, j, count in runs:
        widths = groups.setdefault((v, j - i), {})
        w = m[j] - m[i]
        widths[w] = widths.get(w, 0) + count
    uneven = total = 0.0
    for (v, length), widths in groups.items():
        weight = (1.0 if v else 0.5) / length
        n_runs = sum(widths.values())
        uneven += weight * (n_runs - max(widths.values()))
        total += weight * n_runs
    # Proportions: how far any dot edge drifts from its ideal spot.
    k = len(doubled)
    drift = max(abs(m[i] - i * (n + k) / n) for i in range(n + 1))
    # Size: each pixel short of the exact scale, as a share of the glyph.
    short = size_weight * (t - n - k) / t
    return 100.0 * uneven / total + short + 3.0 * max(0.0, drift - 1.0)


def _search(runs, n, t, size_weight):
    extra = t - n
    if extra <= 0:
        return frozenset()
    best_set, best = None, None
    for k in range(max(0, extra - 2), extra + 1):
        # Start evenly spread, then improve by moving one doubled dot at a time.
        cur = frozenset((2 * j + 1) * n // (2 * k) for j in range(k)) if k else frozenset()
        cur_s = _score(runs, n, cur, t, size_weight)
        improved = True
        while improved:
            improved = False
            for a in sorted(cur):
                for b in range(n):
                    if b in cur:
                        continue
                    cand = (cur - {a}) | {b}
                    s = _score(runs, n, cand, t, size_weight)
                    if s < cur_s - 1e-9:
                        cur, cur_s, improved = cand, s, True
                        break
                if improved:
                    break
        if best is None or cur_s < best:
            best_set, best = cur, cur_s
    return best_set


# How much a pixel short of the exact size costs, per unit of glyph size.
# Text sits next to other scaled text, so it should keep its full size; a
# status icon can drop a pixel to stay crisp.
TEXT_SIZE_WEIGHT = 400.0
ICON_SIZE_WEIGHT = 60.0


def plan(bitmaps, size_weight):
    """Returns ([xmask per scale], [ymask per scale]) for one family."""
    w, h = bitmaps[0].w, bitmaps[0].h
    xruns = _runs([tuple(r) for b in bitmaps for r in b.px])
    yruns = _runs([tuple(r[c] for r in b.px) for b in bitmaps for c in range(b.w)])
    masks = []
    for n, runs in ((w, xruns), (h, yruns)):
        cache, per_scale = {}, []
        for s in range(NUM_SCALES):
            t = target(n, s)
            if t not in cache:
                cache[t] = sum(1 << i for i in _search(runs, n, t, size_weight))
            per_scale.append(cache[t])
        masks.append(per_scale)
    return masks[0], masks[1]
