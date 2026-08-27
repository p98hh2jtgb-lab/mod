#!/usr/bin/env python3
"""Combined animated preview of the whole 5-pad km/h family (V10)."""
from PIL import Image, ImageDraw, ImageFont

SKINS = '/home/user/mod/extracted/vehicles/dashplate_mathkuro/skins'
COLW, GAP, TOP = 150, 12, 26
FRAMES, DUR = 40, 40
DT = DUR / 1000.0

PADS = [
    ('100',  'pulse',     1.5, 1, (0, 1),    0.35),
    ('200',  'strike',    1.8, 2, (0.25, 1), 0.9),
    ('300',  'afterburn', 2.0, 2, (1, 0),    1.2),
    ('500',  'cyber',     3.0, 2, (0, -1),   1.5),
    ('1000', 'warp',      3.0, 8, (0, -1),   2.6),
]
designs = {'cyber': 'dashplate_body_flat_dash_mark_500kmh_cyberglass_b.color.png'}

cols = []
for label, tag, ratio, vtile, (dx, dy), speed in PADS:
    h = int(COLW * ratio)
    dtex = f'{SKINS}/dashplate_{tag}_design_b.color.png' if tag != 'cyber' else f'{SKINS}/dashplate_body_flat_dash_mark_500kmh_cyberglass_b.color.png'
    ftex = f'{SKINS}/dashplate_flat_500kmh_cyberglass_flow_b.color.png' if tag == 'cyber' else f'{SKINS}/dashplate_{tag}_flow_b.color.png'
    design = Image.open(dtex).convert('RGBA').resize((COLW, h), Image.LANCZOS)
    flow = Image.open(ftex).convert('RGBA').resize((COLW, h // vtile), Image.LANCZOS)
    cols.append(dict(label=label, h=h, vtile=vtile, dx=dx, dy=dy, speed=speed,
                     design=design, flow=flow))

W = 5 * COLW + 6 * GAP
H = TOP + max(c['h'] for c in cols) + 10
try: font = ImageFont.load_default(size=15)
except TypeError: font = ImageFont.load_default()

acc = [0.0, 0.0]
frames = []
for f in range(FRAMES):
    img = Image.new('RGBA', (W, H), (10, 12, 16, 255))
    dr = ImageDraw.Draw(img)
    x = GAP
    for c in cols:
        dr.text((x + COLW // 2 - 18, 5), c['label'] + ' km/h', fill=(220, 230, 240, 255), font=font)
        pad = Image.new('RGBA', (COLW, c['h']), (14, 16, 20, 255))
        pd = ImageDraw.Draw(pad)
        pd.rectangle([0, 0, COLW - 1, c['h'] - 1], outline=(46, 50, 58, 255), width=2)
        pad.alpha_composite(c['design'])
        th = c['h'] // c['vtile']
        ox = int(round(acc[0] * c['dx'] * c['speed'] * COLW)) % COLW
        oy = int(round(acc[1] * c['dy'] * c['speed'] * th)) % th
        layer = Image.new('RGBA', (COLW, c['h']), (0, 0, 0, 0))
        fl = c['flow']
        for yy in range(oy - th, c['h'] + th, th):
            for xx in range(ox - COLW, COLW + COLW, COLW):
                layer.paste(fl, (xx, yy))
        pad.alpha_composite(layer)
        img.paste(pad, (x, TOP))
        x += COLW + GAP
    acc[0] += DT; acc[1] += DT
    frames.append(img.convert('P', palette=Image.ADAPTIVE, colors=128))

out = '/home/user/mod/preview_pad_family_V10.gif'
frames[0].save(out, save_all=True, append_images=frames[1:], duration=DUR, loop=0, optimize=True)
print('saved', out)
