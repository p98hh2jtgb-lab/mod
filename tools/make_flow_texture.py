#!/usr/bin/env python3
"""Generate seamless vertical 'energy flow' texture for the 500km/h Cyber-Glass pad.
Outputs RGBA PNG 1024x1024, transparent background, cyber-glass palette.
All elements wrap vertically => perfect seamless UV scroll.
"""
import math, random
from PIL import Image

random.seed(500500)

W = H = 1024
CYAN      = (41, 255, 255)
ELECTRIC  = (0, 186, 255)
ICE       = (140, 240, 255)
AQUA      = (0, 255, 208)
WHITE     = (205, 255, 255)
PALETTE   = [CYAN, ELECTRIC, ICE, AQUA, WHITE, CYAN, ELECTRIC, ICE]

# working buffers (float)
r = [[0.0]*W for _ in range(H)]
g = [[0.0]*W for _ in range(H)]
b = [[0.0]*W for _ in range(H)]
a = [[0.0]*W for _ in range(H)]

def add_col(x, y, color, alpha):
    """add with vertical wrap"""
    yy = y % H
    r[yy][x] += color[0] * alpha
    g[yy][x] += color[1] * alpha
    b[yy][x] += color[2] * alpha
    a[yy][x] += alpha

def draw_streak(xc, y0, length, width, color, peak):
    """vertical glowing streak: gaussian across x, smooth fade along y"""
    sigma = max(1.2, width / 2.6)
    fade = min(length * 0.28, 210.0)          # fade-in/out zone
    for dy in range(int(length)):
        t = dy / max(1.0, length - 1)
        # smooth envelope: sin^2 ramps at both ends
        env = 1.0
        if fade > 0:
            f = min(1.0, min(t, 1.0 - t) * length / fade)
            env = math.sin(min(1.0, f) * math.pi / 2.0) ** 2
        y = int(y0 + dy)
        xr = int(math.ceil(width * 2.5))
        for dx in range(-xr, xr + 1):
            x = xc + dx
            if x < 0 or x >= W:
                continue
            aa = peak * env * math.exp(-(dx * dx) / (2.0 * sigma * sigma))
            if aa > 0.001:
                add_col(x, y, color, aa)

def draw_aurora(xc, y0, length, width, color, peak):
    """wide soft band of light"""
    sigma = width / 2.0
    fade = min(length * 0.35, 260.0)
    step = 2
    for dy in range(0, int(length), step):
        t = dy / max(1.0, length - 1)
        f = min(1.0, min(t, 1.0 - t) * length / fade)
        env = math.sin(min(1.0, f) * math.pi / 2.0) ** 2
        xr = int(width * 2.2)
        for dx in range(-xr, xr + 1, step):
            x = xc + dx
            if x < 0 or x >= W:
                continue
            aa = peak * env * math.exp(-(dx * dx) / (2.0 * sigma * sigma))
            if aa > 0.0005:
                for _ in range(step):           # fill step gap
                    pass
                add_col(x, int(y0 + dy), color, aa)

def draw_dot(xc, y, radius, color, peak):
    for dy in range(-int(radius*2), int(radius*2) + 1):
        for dx in range(-int(radius*2), int(radius*2) + 1):
            d2 = dx*dx + dy*dy
            aa = peak * math.exp(-d2 / (2.0 * radius * radius))
            x = xc + dx
            if 0 <= x < W:
                add_col(x, y + dy, color, aa)

# ---- composition ----------------------------------------------------------
MARGIN = 78        # keep clear of the pad frame

# 1) two soft aurora bands (background energy)
draw_aurora(300, -150, H + 300, 150, (0, 120, 200), 26)
draw_aurora(724,  H - 80, H + 300, 190, (0, 150, 210), 22)

# 2) main streaks – two "lanes" of speed-lines
main_streaks = [
    # xc, y0, len, w, color, peak
    (206,  -80, 620, 7, PALETTE[0], 235),
    (214, 560, 380, 5, PALETTE[4], 175),
    (318, 220, 700, 9, PALETTE[1], 245),
    (336,  -40, 330, 4, PALETTE[4], 140),
    (452, 470, 560, 7, PALETTE[2], 220),
    (512,  60, 840, 12, PALETTE[0], 265),   # central beam – brightest
    (578, 380, 500, 7, PALETTE[3], 215),
    (690, 140, 720, 9, PALETTE[1], 240),
    (702, 880, 300, 5, PALETTE[4], 150),
    (812,  -60, 640, 7, PALETTE[2], 225),
    (826, 640, 360, 5, PALETTE[0], 160),
]
for s in main_streaks:
    draw_streak(*s)

# 3) data-stream dots along a few lines
for (xc, y0, n, spacing, color) in [
    (512,   0, 14, 73, WHITE),
    (318, 100,  9, 96, ICE),
    (690,  40, 11, 84, WHITE),
    (206,  30,  8, 105, ICE),
]:
    for i in range(n):
        yy = y0 + i * spacing
        xx = xc + int(math.sin(i * 1.7) * 6)
        draw_dot(xx, yy, 3.2, color, 165)

# ---- horizontal edge fade (keep frame clean) ------------------------------
for x in range(W):
    if x < MARGIN:
        f = max(0.0, (x - 18) / (MARGIN - 18)) ** 1.5
    elif x > W - MARGIN:
        f = max(0.0, ((W - x) - 18) / (MARGIN - 18)) ** 1.5
    else:
        f = 1.0
    if f < 1.0:
        for y in range(H):
            a[y][x] *= f

# ---- normalize & write -----------------------------------------------------
img = Image.new('RGBA', (W, H))
px = img.load()
for y in range(H):
    for x in range(W):
        aa = a[y][x]
        if aa <= 0.5:
            px[x, y] = (0, 0, 0, 0)
        else:
            aa = min(255.0, aa)
            rr = min(255, int(r[y][x] / aa + 0.5))
            gg = min(255, int(g[y][x] / aa + 0.5))
            bb = min(255, int(b[y][x] / aa + 0.5))
            px[x, y] = (rr, gg, bb, int(aa + 0.5))

out = '/home/user/mod/extracted/vehicles/dashplate_mathkuro/skins/dashplate_flat_500kmh_cyberglass_flow_b.color.png'
img.save(out, 'PNG', optimize=True)
print('saved', out)

# verify vertical seamlessness: compare row 0 vs row H-1 stats
row_top = [px[x, 0] for x in range(0, W, 37)]
row_bot = [px[x, H-1] for x in range(0, W, 37)]
print('top/bot alpha sums:', sum(p[3] for p in row_top), sum(p[3] for p in row_bot))
