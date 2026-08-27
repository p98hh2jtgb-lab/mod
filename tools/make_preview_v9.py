#!/usr/bin/env python3
"""Preview GIF for V9 — correct orientation (chevrons point UP = launch direction,
same as the liked V5 skin), flow moves UP toward the chevrons, speed 1.5, V-tiled x2."""
from PIL import Image, ImageDraw, ImageEnhance

SKINS = '/home/user/mod/extracted/vehicles/dashplate_mathkuro/skins'
PW, PH = 240, 720
FRAMES, SPEED, TILE, DUR = 36, 1.5, 2, 40
TH = PH // TILE

design = Image.open(f'{SKINS}/dashplate_body_flat_dash_mark_500kmh_cyberglass_b.color.png').convert('RGBA').resize((PW, PH), Image.LANCZOS)
flow = Image.open(f'{SKINS}/dashplate_flat_500kmh_cyberglass_flow_b.color.png').convert('RGBA').resize((PW, TH), Image.LANCZOS)

# thumbnail (design + one flow layer, no flips — texture space = correct)
base = Image.new('RGBA', (PW, PH), (16, 16, 16, 255))
base.alpha_composite(design)
for k in range(TILE):
    base.alpha_composite(flow, (0, k * TH))
base.convert('RGB').resize((256, 768), Image.LANCZOS).save(
    '/home/user/mod/extracted/vehicles/dashplate_mathkuro/dashplate_fc_dash_500KMH.jpg', quality=90)
print('thumbnail saved')

shift = SPEED * TH * (DUR / 1000.0)
frames, acc = [], 0.0
for i in range(FRAMES):
    img = Image.new('RGBA', (PW, PH), (12, 14, 18, 255))
    ImageDraw.Draw(img).rectangle([0, 0, PW-1, PH-1], outline=(40, 44, 52, 255), width=3)
    img.alpha_composite(design)
    layer = Image.new('RGBA', (PW, PH), (0, 0, 0, 0))
    off = (-int(round(acc))) % TH          # negative => content moves UP (forward)
    acc += shift
    y = off - TH
    while y < PH:
        layer.paste(flow, (0, y))
        y += TH
    img.alpha_composite(layer)
    img = ImageEnhance.Brightness(img).enhance(1.05)
    frames.append(img.convert('P', palette=Image.ADAPTIVE, colors=128))

out = '/home/user/mod/preview_500kmh_V9_smooth.gif'
frames[0].save(out, save_all=True, append_images=frames[1:], duration=DUR, loop=0, optimize=True)
print('saved', out)
