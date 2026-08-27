#!/usr/bin/env python3
"""Preview GIF + selector thumbnail for the XL 500km/h Cyber-Glass pad (3x9m)."""
from PIL import Image, ImageDraw, ImageEnhance

SKINS = '/home/user/mod/extracted/vehicles/dashplate_mathkuro/skins'
VDIR = '/home/user/mod/extracted/vehicles/dashplate_mathkuro'

# pad is 3m x 9m -> render at 3:9 aspect (top-down, front/forward = UP in preview)
PW, PH = 220, 660
FRAMES = 36
# scrollSpeed 0.65 UV/s -> 0.65 * PH px per second; at 25fps -> px per frame:
SPEED = 0.65
DUR = 40
shift_per_frame = SPEED * PH * (DUR / 1000.0)          # seamless: use fractional accumulate

design = Image.open(f'{SKINS}/dashplate_body_flat_dash_mark_500kmh_cyberglass_b.color.png').convert('RGBA')
# file bottom = pad front; preview wants front UP -> flip
design = design.transpose(Image.FLIP_TOP_BOTTOM).resize((PW, PH), Image.LANCZOS)
flow = Image.open(f'{SKINS}/dashplate_flat_500kmh_cyberglass_flow_b.color.png').convert('RGBA')
flow = flow.transpose(Image.FLIP_TOP_BOTTOM).resize((PW, PH), Image.LANCZOS)

# --- static flat thumbnail (selector) ---
base = Image.new('RGBA', (PW, PH), (16, 16, 16, 255))
base.alpha_composite(design)
base.alpha_composite(flow)
thumb = base.crop((0, 0, PW, PH)).convert('RGB')
thumb = thumb.resize((256, 768), Image.LANCZOS)
thumb.save(f'{VDIR}/dashplate_fc_dash_500KMH.jpg', quality=90)
print('thumbnail saved')

# --- animated gif on dark scene background ---
frames = []
acc = 0.0
for i in range(FRAMES):
    img = Image.new('RGBA', (PW, PH), (12, 14, 18, 255))
    dr = ImageDraw.Draw(img)
    # subtle ground
    dr.rectangle([0, 0, PW-1, PH-1], outline=(40, 44, 52, 255), width=3)
    img.alpha_composite(design)
    off = int(round(acc)) % PH
    acc += shift_per_frame
    layer = Image.new('RGBA', (PW, PH), (0, 0, 0, 0))
    layer.paste(flow, (0, off - PH))
    layer.paste(flow, (0, off))
    img.alpha_composite(layer)
    img = ImageEnhance.Brightness(img).enhance(1.04)
    frames.append(img.convert('P', palette=Image.ADAPTIVE, colors=128))

out = '/home/user/mod/preview_500kmh_XL_flow_fx.gif'
frames[0].save(out, save_all=True, append_images=frames[1:], duration=DUR, loop=0, optimize=True)
print('saved', out)
