#!/usr/bin/env python3
"""Simulated top-down preview of the 500km/h Cyber-Glass pad with the
animated energy-flow layer (UV scroll) — approximates the in-game look."""
from PIL import Image, ImageDraw, ImageEnhance

SKINS = '/home/user/mod/extracted/vehicles/dashplate_mathkuro/skins'
OUT = '/home/user/mod/preview_500kmh_flow_fx.gif'

S = 512                 # preview size
FRAMES = 40
SHIFT = 512 // FRAMES   # seamless loop: total = exactly one tile
DUR = 40                # ms per frame (25 fps)

# ---- background: dark pad body with a subtle frame -------------------------
base = Image.new('RGBA', (S, S), (10, 14, 20, 255))
d = ImageDraw.Draw(base)
d.rectangle([6, 6, S-7, S-7], outline=(70, 90, 110, 255), width=6)
d.rectangle([14, 14, S-15, S-15], outline=(30, 42, 56, 255), width=4)

# ---- current cyber-glass look (user's texture) ------------------------------
glass = Image.open(f'{SKINS}/dashplate_body_flat_dash_mark_500kmh_cyberglass_b.color.png').convert('RGBA').resize((S, S), Image.LANCZOS)

# ---- flow layer (tileable) ---------------------------------------------------
flow = Image.open(f'{SKINS}/dashplate_flat_500kmh_cyberglass_flow_b.color.png').convert('RGBA').resize((S, S), Image.LANCZOS)

frames = []
for i in range(FRAMES):
    img = base.copy()
    img.alpha_composite(glass)
    off = (i * SHIFT) % S
    shifted = Image.new('RGBA', (S, S))
    shifted.paste(flow, (0, off - S))          # wrapped copy
    shifted.paste(flow, (0, off))
    img.alpha_composite(shifted)
    # gentle glow bloom feel: brighten slightly with a screen of the flow
    img = ImageEnhance.Brightness(img).enhance(1.03)
    frames.append(img.convert('P', palette=Image.ADAPTIVE, colors=128))

frames[0].save(OUT, save_all=True, append_images=frames[1:],
               duration=DUR, loop=0, optimize=True)
print('saved', OUT, '| frames:', FRAMES, '| shift/frame:', SHIFT)
