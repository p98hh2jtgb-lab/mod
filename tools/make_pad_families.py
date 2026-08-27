#!/usr/bin/env python3
"""Build the km/h pad family (100/200/300/1000) — each pad gets its own size,
design texture, flow animation texture, DAEs and selector thumbnail.
(500 km/h Cyber-Glass is NOT touched here.)"""
import math, random
from PIL import Image, ImageDraw, ImageFilter, ImageFont

OUT_V = '/home/user/mod/extracted/vehicles/dashplate_mathkuro'
OUT_S = f'{OUT_V}/skins'

SEG = {'0': ('111','101','101','101','111'), '1': ('010','010','010','010','010'),
       '2': ('111','001','111','100','111'), '3': ('111','001','111','001','111')}

PADS = [
  dict(kmh=100, tag='pulse',     name='Pulse',     hw=1.0,  hl=1.5,  nx=3,  ny=4,
       theme=(0,255,140),  accent=(170,255,215), chevrons=1, motif='rings',
       cam=6,  radius=2.5,  ramp=0.45, scrollDir=[0,1],   speed=0.35, vtile=1,
       cw=440, ch=660),
  dict(kmh=200, tag='strike',    name='Strike',    hw=1.25, hl=2.25, nx=3,  ny=6,
       theme=(255,190,0),  accent=(255,238,170), chevrons=2, motif='slash',
       cam=8,  radius=3.5,  ramp=0.5,  scrollDir=[0.25,1], speed=0.9, vtile=2,
       cw=400, ch=720),
  dict(kmh=300, tag='afterburn', name='Afterburn', hw=1.5,  hl=3.0,  nx=4,  ny=8,
       theme=(255,70,70),  accent=(255,175,175), chevrons=3, motif='hazard',
       cam=10, radius=4.5,  ramp=0.55, scrollDir=[1,0],    speed=1.2, vtile=2,
       cw=380, ch=760),
  dict(kmh=1000, tag='warp',    name='Warp',       hw=4.0,  hl=12.0, nx=10, ny=30,
       theme=(175,95,255), accent=(226,192,255), chevrons=4, motif='speedlines',
       cam=36, radius=13,   ramp=0.8,  scrollDir=[0,-1],   speed=2.6, vtile=8,
       cw=342, ch=1024),
]

Z_BODY, Z_DESIGN, Z_FLOW = 0.01665657, 0.025, 0.03

# ============================ DAE emitters =================================
def grid_dae(name, material, hw, hl, nx, ny, z):
    verts, uvs, idx = [], [], []
    for j in range(ny+1):
        for i in range(nx+1):
            verts.append((-hw + 2*hw*i/nx, -hl + 2*hl*j/ny, z))
            uvs.append((i/nx, 1.0 - j/ny))
    for j in range(ny):
        for i in range(nx):
            a=j*(nx+1)+i; b=a+1; c=a+nx+2; d=a+nx+1
            idx += [a,b,c,a,c,d]
    return _dae(name, material, verts, uvs, idx)

def quad_dae(name, material, hw, hl, z, vtile=1):
    verts = [(-hw,-hl,z),(hw,-hl,z),(hw,hl,z),(-hw,hl,z)]
    uvs = [(0,vtile),(1,vtile),(1,0),(0,0)]
    return _dae(name, material, verts, uvs, [0,1,2,0,2,3])

def _dae(name, material, verts, uvs, idx):
    pos=' '.join(f'{x:.6g} {y:.6g} {z:.6g}' for x,y,z in verts)
    map_=' '.join(f'{u:.7g} {v:.7g}' for u,v in uvs)
    p=' '.join(map(str,idx)); nv=len(verts)
    return f'''<?xml version="1.0" encoding="utf-8"?>
<COLLADA xmlns="http://www.collada.org/2005/11/COLLADASchema" version="1.4.1">
  <asset><unit name="meter" meter="1"/><up_axis>Z_UP</up_axis></asset>
  <library_effects>
    <effect id="{name}-effect">
      <profile_COMMON><technique sid="common"><lambert><diffuse><color>1 1 1 1</color></diffuse></lambert></technique></profile_COMMON>
    </effect>
  </library_effects>
  <library_materials>
    <material id="{name}-material" name="{material}">
      <instance_effect url="#{name}-effect"/>
    </material>
  </library_materials>
  <library_geometries>
    <geometry id="{name}-mesh" name="{name}">
      <mesh>
        <source id="{name}-positions">
          <float_array id="{name}-positions-array" count="{nv*3}">{pos}</float_array>
          <technique_common><accessor source="#{name}-positions-array" count="{nv}" stride="3"><param name="X" type="float"/><param name="Y" type="float"/><param name="Z" type="float"/></accessor></technique_common>
        </source>
        <source id="{name}-normals">
          <float_array id="{name}-normals-array" count="3">0 0 1</float_array>
          <technique_common><accessor source="#{name}-normals-array" count="1" stride="3"><param name="X" type="float"/><param name="Y" type="float"/><param name="Z" type="float"/></accessor></technique_common>
        </source>
        <source id="{name}-map">
          <float_array id="{name}-map-array" count="{nv*2}">{map_}</float_array>
          <technique_common><accessor source="#{name}-map-array" count="{nv}" stride="2"><param name="S" type="float"/><param name="T" type="float"/></accessor></technique_common>
        </source>
        <vertices id="{name}-vertices"><input semantic="POSITION" source="#{name}-positions"/></vertices>
        <triangles material="{name}-material" count="{len(idx)//3}">
          <input semantic="VERTEX" source="#{name}-vertices" offset="0"/>
          <input semantic="NORMAL" source="#{name}-normals" offset="1"/>
          <input semantic="TEXCOORD" source="#{name}-map" offset="2" set="0"/>
          <p>{p}</p>
        </triangles>
      </mesh>
    </geometry>
  </library_geometries>
  <library_visual_scenes>
    <visual_scene id="Scene" name="Scene">
      <node id="{name}" name="{name}" type="NODE">
        <instance_geometry url="#{name}-mesh">
          <bind_material><technique_common><instance_material symbol="{name}-material" target="#{name}-material"/></technique_common></bind_material>
        </instance_geometry>
      </node>
    </visual_scene>
  </library_visual_scenes>
  <scene><instance_visual_scene url="#Scene"/></scene>
</COLLADA>
'''

# ======================= design textures ====================================
def draw_design(cfg):
    W,H = cfg['cw'], cfg['ch']
    theme, accent = cfg['theme'], cfg['accent']
    design = Image.new('RGBA',(W,H),(0,0,0,0))
    d = ImageDraw.Draw(design)
    glow = Image.new('RGBA',(W,H),(0,0,0,0))
    gd = ImageDraw.Draw(glow)

    m, cut = max(10,W//30), W//13
    frame = [(m+cut,m),(W-m-cut,m),(W-m,m+cut),(W-m,H-m-cut),(W-m-cut,H-m),(m+cut,H-m),(m,H-m-cut),(m,m+cut)]
    # glass background clipped to frame
    tr,tg,tb = theme
    for y in range(H):
        t = y/H
        d.line([(0,y),(W,y)], fill=(10+tr//14, 16+tg//14, 20+tb//14, 252-int(30*t)))
    # micro grid
    for y in range(0,H,16): d.line([(0,y),(W,y)],fill=(tr//2,tg//2,tb//2,10))
    for x in range(0,W,16): d.line([(x,0),(x,H)],fill=(tr//2,tg//2,tb//2,10))

    gd.polygon(frame, outline=theme+(235,), width=3)
    bl = W//10
    for cx,cy,dx,dy in [(m+5,m+5,1,1),(W-m-5,m+5,-1,1),(m+5,H-m-5,1,-1),(W-m-5,H-m-5,-1,-1)]:
        gd.line([(cx,cy),(cx+bl*dx,cy)],fill=accent+(255,),width=4)
        gd.line([(cx,cy),(cx,cy+bl*dy)],fill=accent+(255,),width=4)

    # rails
    rx = [m+14, W-m-14]
    for x in rx:
        gd.line([(x,int(H*.09)),(x,int(H*.91))],fill=theme+(215,),width=max(4,W//70))
        for y in range(int(H*.11), int(H*.89), H//22):
            gd.line([(x,y),(x,y+H//44)],fill=accent+(235,),width=max(4,W//70))
    # launch bar (front/top) + entry bar
    gd.line([(m+14,int(H*.055)),(W-m-14,int(H*.055))],fill=accent+(255,),width=max(6,W//45))
    gd.line([(m+14,int(H*.945)),(W-m-14,int(H*.945))],fill=theme+(200,),width=max(4,W//90))

    # chevrons (apex UP = forward, texture space)
    n = cfg['chevrons']
    cy0, cy1 = int(H*0.14), int(H*0.42)
    span0 = int(W*0.62)
    for i in range(n):
        cy = cy0 + (cy1-cy0)*i//max(1,n-1) if n>1 else (cy0+cy1)//2
        span = span0 - i*(int(W*0.09))
        hw2 = span//2; cx = W//2; vw = max(9,W//30)
        gd.line([(cx-hw2, cy+span//3),(cx,cy-span//3)],fill=theme+(245,),width=vw)
        gd.line([(cx,cy-span//3),(cx+hw2,cy+span//3)],fill=theme+(245,),width=vw)
    # motif extras
    if cfg['motif']=='rings':
        cx,cy = W//2,(cy0+cy1)//2
        for r,w,a in [(W//4,4,150),(W//3,3,100),(W//2.4,2,70)]:
            gd.ellipse([cx-r,cy-r,cx+r,cy+r],outline=accent+(a,),width=w)
    elif cfg['motif']=='slash':
        for k in range(3):
            x0 = m+30+k*26
            gd.line([(x0,H-m-40),(x0+40,H-m-90)],fill=accent+(180,),width=5)
            gd.line([(W-x0,H-m-40),(W-x0-40,H-m-90)],fill=accent+(180,),width=5)
    elif cfg['motif']=='hazard':
        for yy in (m+8, H-m-8):
            x = m+cut
            while x < W-m-cut:
                gd.line([(x,yy+(0 if (x//28)%2==0 else 10)),(x+28,yy+(10 if (x//28)%2==0 else 0))],fill=theme+(220,),width=6)
                x += 28
    elif cfg['motif']=='speedlines':
        for k in range(5):
            x0 = W//2 + (k-2)*W//7
            gd.line([(x0,int(H*.46)),(x0,int(H*.50))],fill=accent+(200,),width=4)

    # digits
    num = str(cfg['kmh'])
    cell_w = max(12, int(W*0.052)); cell_h = cell_w*4//3; stroke = max(5,cell_w//3)
    digit_w, digit_h = cell_w*3+stroke, cell_h*5+stroke
    gap = cell_w
    total = len(num)*digit_w + (len(num)-1)*gap
    while total > W-2*(m+22):
        cell_w -= 1; cell_h = cell_w*4//3; stroke = max(4,cell_w//3)
        digit_w, digit_h = cell_w*3+stroke, cell_h*5+stroke
        total = len(num)*digit_w + (len(num)-1)*gap
    x0 = (W-total)//2; y0 = int(H*0.52)
    for i,ch in enumerate(num):
        rows = SEG[ch]
        for r in range(5):
            for c in range(3):
                if rows[r][c]=='1':
                    xx = x0+i*(digit_w+gap)+c*cell_w; yy = y0+r*cell_h
                    gd.rectangle([xx,yy,xx+stroke,yy+stroke],fill=accent+(255,))
                    gd.rectangle([xx,yy,xx+stroke,yy+stroke],fill=theme+(70,))
    try: font = ImageFont.load_default(size=max(22,W//12))
    except TypeError: font = ImageFont.load_default()
    bb = gd.textbbox((0,0),'km/h',font=font); tw = bb[2]-bb[0]
    gd.text(((W-tw)//2, y0+digit_h+H//40), 'km/h', font=font, fill=accent+(255,))

    design.alpha_composite(glow.filter(ImageFilter.GaussianBlur(7)))
    design.alpha_composite(glow.filter(ImageFilter.GaussianBlur(3)))
    design.alpha_composite(glow)
    return design.resize((1024,1024), Image.LANCZOS)

# ======================= flow textures ======================================
def _buf():
    W=H=1024
    return W,H,[[0.0]*W for _ in range(H)],[[0.0]*W for _ in range(H)],[[0.0]*W for _ in range(H)],[[0.0]*W for _ in range(H)]

def _write(bufs, color, path, xfade=70):
    W,H,r,g,b,a = bufs
    img = Image.new('RGBA',(W,H)); px = img.load()
    for y in range(H):
        for x in range(W):
            aa = a[y][x]
            if x<xfade: aa *= (x/xfade)**1.5
            elif x>W-xfade: aa *= ((W-x)/xfade)**1.5
            if aa<=0.5: px[x,y]=(0,0,0,0)
            else:
                aa=min(255.0,aa)
                px[x,y]=(min(255,int(r[y][x]/aa+.5)),min(255,int(g[y][x]/aa+.5)),min(255,int(b[y][x]/aa+.5)),int(aa+.5))
    img.save(path,'PNG',optimize=True)

def flow_pulse(color):   # horizontal soft bands traveling along V
    W,H,r,g,b,a=_buf(); random.seed(101)
    bands=[(60,560,300,150),(400,900,380,120),(760,420,260,160),(200,-100,340,110),(880,880,300,100)]
    for y0,length,wd,peak in bands:
        fade=length*0.35
        for dy in range(length):
            t=dy/max(1,length-1)
            f=min(1.0,min(t,1-t)*length/fade)
            env=(math.sin(min(1,f)*math.pi/2))**2
            for x in range(W):
                aa=peak*env*(0.75+0.25*math.sin(x/W*math.pi))
                yy=(y0+dy)%H
                r[yy][x]+=color[0]*aa; g[yy][x]+=color[1]*aa; b[yy][x]+=color[2]*aa; a[yy][x]+=aa
    return (W,H,r,g,b,a)

def flow_diag(color):    # diagonal streaks, tileable both axes
    W,H,r,g,b,a=_buf(); random.seed(202)
    def plot(x,y,aa,sigma2):
        for oy in (0,-H,H):
            for ox in (0,-W,W):
                xx,yy=x+ox,y+oy
                if 0<=xx<W and 0<=yy<H:
                    r[yy][xx]+=color[0]*aa; g[yy][xx]+=color[1]*aa; b[yy][xx]+=color[2]*aa; a[yy][xx]+=aa
    for i in range(26):
        x0=random.randint(0,W); y0=random.randint(0,H)
        L=random.randint(260,560); w=random.uniform(3.5,7); peak=random.uniform(140,230)
        dx,dy=0.28,1.0; n=int(L/math.hypot(dx,dy))
        for t in range(n):
            tt=t/max(1,n-1)
            f=min(1.0,min(tt,1-tt)*4)
            env=(math.sin(min(1,f)*math.pi/2))**2
            x=(x0+dx*t)%W; y=(y0+dy*t)%H
            for dxx in range(-int(w*2),int(w*2)+1):
                aa=peak*env*math.exp(-(dxx*dxx)/(2*(w/2)**2))
                if aa>1: plot(int(x)+dxx,int(y),aa,0)
    return (W,H,r,g,b,a)

def flow_lanes(color):   # horizontal dash lanes, scroll along U (sideways)
    W,H,r,g,b,a=_buf(); random.seed(303)
    lanes=7
    for ln in range(lanes):
        y=int((ln+0.5)*H/lanes)
        # guide line
        for x in range(W):
            aa=36
            r[y][x]+=color[0]*aa; g[y][x]+=color[1]*aa; b[y][x]+=color[2]*aa; a[y][x]+=aa
        off=(ln*137)%220
        x=-off
        while x<W+220:
            for t in range(110):
                tt=t/109; f=min(1.0,min(tt,1-tt)*5)
                env=(math.sin(min(1,f)*math.pi/2))**2
                for dy in range(-9,10):
                    aa=200*env*math.exp(-(dy*dy)/(2*4.5**2))
                    if aa>1:
                        xx=(x+t)%W; yy=(y+dy)%H
                        r[yy][xx]+=color[0]*aa; g[yy][xx]+=color[1]*aa; b[yy][xx]+=color[2]*aa; a[yy][xx]+=aa
            x+=220
    return (W,H,r,g,b,a)

def flow_warp(color):    # dense thin vertical streaks (like 500 but denser)
    W,H,r,g,b,a=_buf(); random.seed(1000)
    accent=(min(255,color[0]+70),min(255,color[1]+70),min(255,color[2]+70))
    def streak(xc,y0,length,w,col,peak):
        sigma=max(1.0,w/2.6); fade=min(length*0.28,200)
        for dy in range(int(length)):
            t=dy/max(1,length-1)
            f=min(1.0,min(t,1-t)*length/fade)
            env=(math.sin(min(1,f)*math.pi/2))**2
            yy=(y0+dy)%H
            for dx in range(-int(w*2.5),int(w*2.5)+1):
                x=xc+dx
                if 0<=x<W:
                    aa=peak*env*math.exp(-(dx*dx)/(2*sigma*sigma))
                    if aa>0.001:
                        r[yy][x]+=col[0]*aa; g[yy][x]+=col[1]*aa; b[yy][x]+=col[2]*aa; a[yy][x]+=aa
    xs=[90,150,210,262,330,378,440,512,570,628,700,760,822,890,946]
    for i,xc in enumerate(xs):
        streak(xc, random.randint(-300,900), random.randint(400,900), random.uniform(4,8),
               color if i%3 else accent, random.uniform(190,250))
    for xc,ln in [(512,1000),(330,700),(700,700),(150,600),(890,600)]:
        streak(xc, random.randint(-200,600), ln, 10, accent, 160)
    return (W,H,r,g,b,a)

FLOWS={'pulse':flow_pulse,'strike':flow_diag,'afterburn':flow_lanes,'warp':flow_warp}

# ======================= thumbnails =========================================
def thumbnail(cfg, design1024, flow1024):
    ratio = cfg['ch']/cfg['cw']
    tw = 200; th = int(tw*ratio)
    design = design1024.resize((tw,th), Image.LANCZOS)
    flow = flow1024.resize((tw,max(1,th//cfg['vtile'])), Image.LANCZOS)
    base = Image.new('RGBA',(tw,th),(14,16,20,255))
    base.alpha_composite(design)
    for k in range(cfg['vtile']):
        base.alpha_composite(flow,(0,k*th//cfg['vtile']))
    base.convert('RGB').resize((256,max(1,int(256*ratio))), Image.LANCZOS).save(
        f"{OUT_V}/dashplate_fc_dash_{cfg['kmh']}KMH.jpg", quality=90)

# ======================= run =================================================
manifest = []
for cfg in PADS:
    tag=cfg['tag']
    design = draw_design(cfg)
    dp = f'{OUT_S}/dashplate_{tag}_design_b.color.png'
    design.save(dp,'PNG',optimize=True)
    bufs = FLOWS[tag](cfg['theme'])
    fp = f'{OUT_S}/dashplate_{tag}_flow_b.color.png'
    _write(bufs, cfg['theme'], fp, 0 if tag in ('strike','afterburn') else 70)
    flow1024 = Image.open(fp).convert('RGBA')
    # DAEs
    body_name = {'pulse':'dashplate_flat_body_s','strike':'dashplate_flat_body_m',
                 'afterburn':'dashplate_flat_body_l','warp':'dashplate_flat_body_mega'}[tag]
    open(f'{OUT_V}/{body_name}.dae','w').write(
        grid_dae(body_name,'dashplate_flat_body_main',cfg['hw'],cfg['hl'],cfg['nx'],cfg['ny'],Z_BODY))
    open(f'{OUT_V}/dashplate_flat_{tag}_design.dae','w').write(
        quad_dae(f'dashplate_flat_{tag}_design', f'dashplate_flat_{tag}_design', cfg['hw'],cfg['hl'],Z_DESIGN))
    open(f'{OUT_V}/dashplate_flat_{tag}_flow.dae','w').write(
        quad_dae(f'dashplate_flat_{tag}_flow', f'dashplate_flat_{tag}_flow', cfg['hw'],cfg['hl'],Z_FLOW,cfg['vtile']))
    thumbnail(cfg, design, flow1024)
    manifest.append((cfg['kmh'], tag, body_name, cfg['radius'], cfg['ramp'], cfg['scrollDir'], cfg['speed']))
    print('built pad', cfg['kmh'], tag)

import json
json.dump(manifest, open('/tmp/pad_manifest.json','w'))
print('manifest -> /tmp/pad_manifest.json')
