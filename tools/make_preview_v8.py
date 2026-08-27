#!/usr/bin/env python3
"""Preview GIF for the XXL 6x18m 500km/h Cyber-Glass pad (V8) — speed 1.5, V-tiled flow."""
from PIL import Image, ImageDraw, ImageEnhance

SKINS = '/home/user/mod/extracted/vehicles/dashplate_mathkuro/skins'

PW, PH = 240, 720          # 6 x 18 m -> 1:3 aspect
FRAMES = 36
SPEED = 1.5
TILE = 2                   # flow repeats 2x along pad length
DUR = 40

TH = PH // TILE            # one flow tile height in px

design = Image.open(f'{SKINS}/dashplate_body_flat_dash_mark_500kmh_cyberglass_b.color.png').convert('RGBA')
design = design.transpose(Image.FLIP_TOP_BOTTOM).resize((PW, PH), Image.LANCZOS)
flow = Image.open(f'{SKINS}/dashplate_flat_500kmh_cyberglass_flow_b.color.png').convert('RGBA')
flow = flow.transpose(Image.FLIP_TOP_BOTTOM).resize((PW, TH), Image.LANCZOS)

# static thumbnail for the selector (design + one flow layer)
base = Image.new('RGBA', (PW, PH), (16, 16, 16, 255))
base.alpha_composite(design)
for k in range(TILE):
    base.alpha_composite(flow, (0, k * TH))
base.convert('RGB').resize((256, 768), Image.LANCZOS).save(
    '/home/user/mod/extracted/vehicles/dashplate_mathkuro/dashplate_fc_dash_500KMH.jpg', quality=90)
print('thumbnail saved')

shift_per_frame = SPEED * TH * (DUR / 1000.0)   # px per frame per tile
frames = []
acc = 0.0
for i in range(FRAMES):
    img = Image.new('RGBA', (PW, PH), (12, 14, 18, 255))
    ImageDraw.Draw(img).rectangle([0, 0, PW-1, PH-1], outline=(40, 44, 52, 255), width=3)
    img.alpha_composite(design)
    layer = Image.new('RGBA', (PW, PH), (0, 0, 0, 0))
    off = int(round(acc)) % TH
    acc += shift_per_frame
    y = off - TH
    while y < PH:
        layer.paste(flow, (0, y))
        y += TH
    img.alpha_composite(layer)
    img = ImageEnhance.Brightness(img).enhance(1.05)
    frames.append(img.convert('P', palette=Image.ADAPTIVE, colors=128))

out = '/home/user/mod/preview_500kmh_XXL_flow_fx.gif'
frames[0].save(out, save_all=True, append_images=frames[1:], duration=DUR, loop=0, optimize=True)
print('saved', out)
