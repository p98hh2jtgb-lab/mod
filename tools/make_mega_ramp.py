#!/usr/bin/env python3
"""MEGA RAMP (10x25m, ~20 deg, with animated side walls) — Hyperjump magenta.
Uses the corrected COLLADA emitter (p = count*9)."""
import re, json

V = '/home/user/mod/extracted/vehicles/dashplate_mathkuro'
HW, HL, RISE = 5.0, 12.5, 9.0        # 10m wide, 25m long, 9m rise => ~19.8 deg
Z_BODY = 0.01665657
def z_at(y): return RISE * (HL - y) / (2 * HL)

def dae(name, material, verts, uvs, tri_idx):
    pos = ' '.join(f'{x:.6g} {y:.6g} {z:.6g}' for x, y, z in verts)
    map_ = ' '.join(f'{u:.7g} {v:.7g}' for u, v in uvs)
    p = ' '.join(f'{vi} 0 {vi}' for vi in tri_idx)
    nv = len(verts)
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
        <triangles material="{name}-material" count="{len(tri_idx)//3}">
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

# ============ 1) inclined driving surface grid ============
nx, ny = 6, 25
verts, uvs, idx = [], [], []
for j in range(ny+1):
    for i in range(nx+1):
        x = -HW + 2*HW*i/nx; y = -HL + 2*HL*j/ny
        verts.append((x, y, z_at(y) + Z_BODY)); uvs.append((i/nx, 1.0 - j/ny))
for j in range(ny):
    for i in range(nx):
        a=j*(nx+1)+i; b=a+1; c=a+nx+2; d=a+nx+1
        idx += [a,b,c,a,c,d]
open(f'{V}/dashplate_flat_body_megaramp.dae','w').write(
    dae('dashplate_flat_body_megaramp', 'dashplate_flat_body_main', verts, uvs, idx))
print('megaramp body grid (10x25m inclined) written')

# ============ 2) surface quads (reuse Hyperjump magenta materials) ============
for mesh, mat, zoff, vtile in [
    ('dashplate_flat_megaramp_design', 'dashplate_flat_jump_design', 0.0083, 1),
    ('dashplate_flat_megaramp_flow',   'dashplate_flat_jump_flow',   0.0133, 3)]:
    qv = [(-HW,-HL,z_at(-HL)+Z_BODY+zoff),(HW,-HL,z_at(-HL)+Z_BODY+zoff),
          (HW, HL,z_at( HL)+Z_BODY+zoff),(-HW, HL,z_at( HL)+Z_BODY+zoff)]
    quv = [(0,vtile),(1,vtile),(1,0),(0,0)]
    open(f'{V}/{mesh}.dae','w').write(dae(mesh, mat, qv, quv, [0,1,2,0,2,3]))
    print(mesh, '-> material', mat)

# ============ 3) SIDE WALLS (animated magenta streaks!) ============
# left wall: x=-HW ; right wall: x=+HW ; top edge follows surface, bottom 2.5m below (or ground)
verts, uvs, idx = [], [], []
for k, xs in ((0, -HW), (1, HW)):
    top_a = z_at(-HL)+Z_BODY; bot_a = max(z_at(-HL)-2.5, -0.35)
    top_b = z_at( HL)+Z_BODY; bot_b = -0.35
    base = len(verts)
    # v0 top-exit, v1 bottom-exit, v2 bottom-entry, v3 top-entry
    verts += [(xs,-HL,top_a),(xs,-HL,bot_a),(xs,HL,bot_b),(xs,HL,top_b)]
    # UVs: V along ramp length (3 tiles), U across wall height
    uvs  += [(0,3),(1,3),(1,0),(0,0)]
    idx  += [base,base+1,base+2, base,base+2,base+3]
open(f'{V}/dashplate_flat_megaramp_walls.dae','w').write(
    dae('dashplate_flat_megaramp_walls', 'dashplate_flat_jump_flow', verts, uvs, idx))
print('side walls written (2 quads, animated flow material, V-tile 3)')

# ============ 4) jbeam: physics body (clone of XL, node rows only) ============
src = open(f'{V}/dashplate_flat.jbeam').read()
i = src.index('"dashplate_flat_body_xl": {')
m = re.search(r'\n    "', src[i+10:])
xl = src[i:i+10+m.start()]
MR = {'dp_1':'-5.0,-12.5, 8.83','dp_3':'-5.0, 12.5, -0.1','dp_5':' 5.0,-12.5, 8.83','dp_7':' 5.0, 12.5, -0.1',
      'dp_0':'-5.0,-12.5, 9.13','dp_2':'-5.0, 12.5, 0.2','dp_4':' 5.0,-12.5, 9.13','dp_6':' 5.0, 12.5, 0.2'}
NODE_RE = re.compile(r'^(\s*\["(dp_\d)",)\s*-?[\d.]+,\s*-?[\d.]+,\s*-?[\d.]+(\],?\s*)$')
out = []
for line in xl.splitlines():
    mm = NODE_RE.match(line)
    out.append(f'{mm.group(1)}{MR[mm.group(2)]}{mm.group(3)}' if mm else line)
b = '\n'.join(out)
b = b.replace('"dashplate_flat_body_xl": {', '"dashplate_flat_body_megaramp": {', 1)
b = re.sub(r'"name":\s*"Dash Plate Body\(Flat XXL 6x18m\)"', '"name": "Dash Plate Body(MEGA Ramp 10x25m, 20°)"', b)
b = re.sub(r'"distance":\d+', '"distance":40', b)
b = re.sub(r'"distanceMin":\d+', '"distanceMin":12', b)
mesh_part = '''"dashplate_flat_mesh_megaramp": {
        "information":{
            "authors":"Mathkuro",
            "name":"Dash Plate Mesh — MEGA Ramp Hyperjump"
        },
        "slotType" : "dashplate_meshes",
        "flexbodies": [
            ["mesh", "[group]:"],
            ["dashplate_flat_body_megaramp", ["dp"]],
            ["dashplate_flat_megaramp_design", ["dp"]],
            ["dashplate_flat_megaramp_flow", ["dp"]],
            ["dashplate_flat_megaramp_walls", ["dp"]]
        ]
    },
    '''
anchor = '"dashplate_flat_mesh_500kmh_cyberglass": {'
src = src.replace(anchor, mesh_part + anchor, 1)
insert_at = src.index('"dashplate_flat_body_xl": {')
src = src[:insert_at] + b + '\n    ' + src[insert_at:]
open(f'{V}/dashplate_flat.jbeam','w').write(src)
print('jbeam: megaramp body + mesh part added')

# ============ 5) pc + info ============
p = json.load(open(f'{V}/dashplate_fc_dash_500KMH.pc'))
p['parts']['dashplate_body'] = 'dashplate_flat_body_megaramp'
p['parts']['dashplate_meshes'] = 'dashplate_flat_mesh_megaramp'
p['vars']['$dashplateTriggerRadius'] = 14
p['vars']['$dashplateDashRampSec'] = 0.6
json.dump(p, open(f'{V}/dashplate_fc_dash_500KMH_MEGARAMP.pc','w'), indent=2)
inf = json.load(open(f'{V}/info_dashplate_fc_dash_500KMH.json'))
inf['Configuration'] = 'MEGA Ramp (500km/h) — Hyperjump X'
inf['Description'] = 'Giant 10x25 m launch ramp (~20 deg) with animated magenta side walls. Hit it with a 500 km/h boost and FLY X-Games style.'
json.dump(inf, open(f'{V}/info_dashplate_fc_dash_500KMH_MEGARAMP.json','w'), indent=2)
print('pc + info written')

# ============ 6) validate ============
def loose(s):
    t = re.sub(r'^\s*//.*$','',s,flags=re.M)
    return json.loads(re.sub(r',(\s*[}\]])', r'\1', t))
j = loose(src)
part = j['dashplate_flat_body_megaramp']
NODEIDS = {f'dp_{k}' for k in range(8)} | {'ref','refback','refleft','refup','refleftCorner','refrightCorner'}
def is_hdr(row): return any(str(v).endswith(':') for v in row)
ids = {r[0] for r in part['nodes'] if isinstance(r,list)} | NODEIDS
beams = [r for r in part['beams'] if isinstance(r,list) and not is_hdr(r)]
assert len(beams)==52 and all(r[0] in ids and r[1] in ids for r in beams)
print('megaramp body validated: 52 beams ✓')
import glob, xml.dom.minidom as md
for f in glob.glob(f'{V}/*.dae'):
    md.parse(f)
    s = open(f).read()
    tri = re.search(r'<triangles[^>]*count="(\d+)"[^>]*>(.*?)</triangles>', s, re.S)
    cnt = int(tri.group(1))
    pv = len(re.search(r'<p>([^<]*)</p>', tri.group(2)).group(1).split())
    assert pv == cnt*9, (f, cnt, pv)
print('ALL DAEs valid (p = count*9) ✓')
