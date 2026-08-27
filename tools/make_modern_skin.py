#!/usr/bin/env python3
"""New modern 'Cyber-Glass XL' design for the 500km/h pad overlay.
Design space = driver view (342x1024, 1:3 aspect like the 3x9m pad).
Final file = design upscaled to 1024x1024 and flipped vertically
(image bottom = pad front, matching the mod's UV orientation)."""
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps

W, H = 342, 1024
CYAN   = (0, 226, 255)
ELEC   = (0, 150, 255)
ICE    = (150, 245, 255)
WHITE  = (235, 255, 255)

design = Image.new('RGBA', (W, H), (0, 0, 0, 0))
d = ImageDraw.Draw(design)

# ---------- background: smoked glass with subtle vertical gradient ----------
_m, _cut = 12, 26
_frame = [(_m+_cut, _m), (W-_m-_cut, _m), (W-_m, _m+_cut), (W-_m, H-_m-_cut),
          (W-_m-_cut, H-_m), (_m+_cut, H-_m), (_m, H-_m-_cut), (_m, _m+_cut)]
_mask = Image.new('L', (W, H), 0)
ImageDraw.Draw(_mask).polygon(_frame, fill=255)
_mask = _mask.filter(ImageFilter.GaussianBlur(1.2))
_bg = Image.new('RGBA', (W, H), (0, 0, 0, 0))
_bd = ImageDraw.Draw(_bg)
for y in range(H):
    t = y / H                      # 0 = front (top in driver view), 1 = back
    base_a = 168 - int(24 * t)
    r, g, b = 12 + int(8 * (1 - t)), 22 + int(12 * (1 - t)), 34 + int(16 * (1 - t))
    _bd.line([(0, y), (W, y)], fill=(r, g, b, base_a))
_bg.putalpha(Image.composite(_bg.getchannel('A'), Image.new('L', (W, H), 0), _mask))
design.alpha_composite(_bg)

# micro tech grid
for y in range(0, H, 16):
    d.line([(0, y), (W, y)], fill=(0, 190, 220, 9))
for x in range(0, W, 16):
    d.line([(x, 0), (x, H)], fill=(0, 190, 220, 13))

glow = Image.new('RGBA', (W, H), (0, 0, 0, 0))   # shapes that get bloom
gd = ImageDraw.Draw(glow)

# ---------- neon frame with cut corners ----------
m, cut = 12, 26
frame = [(m+cut, m), (W-m-cut, m), (W-m, m+cut), (W-m, H-m-cut),
         (W-m-cut, H-m), (m+cut, H-m), (m, H-m-cut), (m, m+cut)]
gd.polygon(frame, outline=CYAN + (235,), width=3)

# HUD corner brackets (modern)
bl = 34
for cx, cy, dx, dy in [(m+6, m+6, 1, 1), (W-m-6, m+6, -1, 1), (m+6, H-m-6, 1, -1), (W-m-6, H-m-6, -1, -1)]:
    gd.line([(cx, cy), (cx + bl*dx, cy)], fill=WHITE + (255,), width=4)
    gd.line([(cx, cy), (cx, cy + bl*dy)], fill=WHITE + (255,), width=4)

# ---------- side rails (runway) ----------
rail_x = [26, W-26]
for x in rail_x:
    gd.line([(x, 96), (x, H-96)], fill=CYAN + (215,), width=6)
    for y in range(112, H-104, 44):          # energy dashes on rails
        gd.line([(x, y), (x, y+22)], fill=WHITE + (235,), width=6)

# ---------- front launch bar & back entry bar ----------
gd.line([(m+16, 46), (W-m-16, 46)], fill=ICE + (255,), width=10)
for x in range(m+20, W-m-18, 26):            # tick marks on launch bar
    gd.line([(x, 34), (x, 58)], fill=WHITE + (140,), width=2)
gd.line([(m+16, H-46), (W-m-16, H-46)], fill=ELEC + (200,), width=6)

# ---------- big '500' segment digits ----------
SEG = {'5': ('111', '100', '111', '001', '111'),
       '0': ('111', '101', '101', '101', '111')}
cell_w, cell_h, stroke = 24, 32, 8
digit_w = cell_w * 3 + stroke            # ~73
digit_h = cell_h * 5 + stroke            # ~147

def draw_digit(dr, ch, x0, y0, color):
    rows = SEG[ch]
    for r in range(5):
        for c in range(3):
            if rows[r][c] == '1':
                dr.rectangle([x0 + c*cell_w, y0 + r*cell_h,
                              x0 + c*cell_w + stroke, y0 + r*cell_h + stroke],
                             fill=color)

txt = '500'
gap = 20
total_w = 3*digit_w + 2*gap
x0 = (W - total_w) // 2
y0 = 150
for i, ch in enumerate(txt):
    draw_digit(gd, ch, x0 + i*(digit_w+gap), y0, WHITE + (255,))
    draw_digit(gd, ch, x0 + i*(digit_w+gap), y0, CYAN + (60,))   # tint bloom

# 'km/h' under the digits
try:
    font = ImageFont.load_default(size=40)
except TypeError:
    font = ImageFont.load_default()
bbox = d.textbbox((0, 0), 'km/h', font=font)
tw = bbox[2] - bbox[0]
gd.text(((W - tw)//2, y0 + digit_h + 26), 'km/h', font=font, fill=ICE + (255,))

# ---------- chevrons pointing forward (up in driver view) ----------
def chevron(dr, cy, span, color, width):
    hw = span // 2
    cx = W // 2
    dr.line([(cx - hw, cy + 26), (cx, cy - 26)], fill=color, width=width)
    dr.line([(cx, cy - 26), (cx + hw, cy + 26)], fill=color, width=width)

for cy, span in [(560, 214), (704, 232), (848, 250)]:
    chevron(gd, cy, span, CYAN + (245,), 17)
    chevron(gd, cy - 38, span - 30, ICE + (130,), 9)   # echo line above

# rail dots at chevron heights
for cy in (560, 700, 840):
    for x in rail_x:
        gd.ellipse([x-9, cy-9, x+9, cy+9], fill=WHITE + (230,))

# ---------- compose: bloom under sharp ----------
design.alpha_composite(glow.filter(ImageFilter.GaussianBlur(7)))
design.alpha_composite(glow.filter(ImageFilter.GaussianBlur(3)))
design.alpha_composite(glow)

# ---------- to final: upscale to 1024x1024, flip vertically ----------
final = design.resize((1024, 1024), Image.LANCZOS)
final = ImageOps.flip(final)
out = '/home/user/mod/extracted/vehicles/dashplate_mathkuro/skins/dashplate_body_flat_dash_mark_500kmh_cyberglass_b.color.png'
final.save(out, 'PNG', optimize=True)
print('saved', out)

chk = final.copy()
small = chk.resize((57, 57))
sp = small.load()
chars = ' .:*#@'
for y in range(0, 57, 2):
    print(''.join(chars[min(5, sp[x, y][3] * 6 // 256)] for x in range(57)))
