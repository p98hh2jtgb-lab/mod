#!/usr/bin/env python3
"""Build the JUMP PAD (8x20m inclined ramp, ~19 deg) with byte-exact COLLADA <p> convention
(vertex normal uv per corner — matches the original working DAEs)."""
import math, re, json

V = '/home/user/mod/extracted/vehicles/dashplate_mathkuro'
HW, HL, RISE = 4.0, 10.0, 7.0     # 8m wide, 20m long, 7m rise => ~19.3 deg
def z_at(y): return RISE * (HL - y) / (2 * HL)
Z_BODY = 0.01665657

def dae(name, material, verts, uvs, tri_idx):
    """tri_idx = list of vertex indices (3 per triangle). <p> = 'v 0 v' per corner."""
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

# ============ 1) ALSO FIX the flat body_xl.dae (its <p> was short) ============
nx, ny = 4, 12
verts, uvs, idx = [], [], []
for j in range(ny+1):
    for i in range(nx+1):
        x = -3.0 + 6.0*i/nx; y = -9.0 + 18.0*j/ny
        verts.append((x, y, Z_BODY)); uvs.append((i/nx, 1.0 - j/ny))
for j in range(ny):
    for i in range(nx):
        a=j*(nx+1)+i; b=a+1; c=a+nx+2; d=a+nx+1
        idx += [a,b,c,a,c,d]
open(f'{V}/dashplate_flat_body_xl.dae','w').write(
    dae('dashplate_flat_body_xl', 'dashplate_flat_body_main', verts, uvs, idx))
print('body_xl.dae REGENERATED with correct <p> (48 tri x 9 =', len(idx)*3, 'values)')

# ============ 2) JUMP body grid (5x20, inclined) ============
nx, ny = 5, 20
verts, uvs, idx = [], [], []
for j in range(ny+1):
    for i in range(nx+1):
        x = -HW + 2*HW*i/nx; y = -HL + 2*HL*j/ny
        verts.append((x, y, z_at(y) + Z_BODY)); uvs.append((i/nx, 1.0 - j/ny))
for j in range(ny):
    for i in range(nx):
        a=j*(nx+1)+i; b=a+1; c=a+nx+2; d=a+nx+1
        idx += [a,b,c,a,c,d]
open(f'{V}/dashplate_flat_body_jump.dae','w').write(
    dae('dashplate_flat_body_jump', 'dashplate_flat_body_main', verts, uvs, idx))
print('jump body grid written')

# ============ 3) JUMP overlay + flow quads (own materials) ============
for mesh, mat, zoff, vtile in [
    ('dashplate_flat_jump_design', 'dashplate_flat_jump_design', 0.0083, 1),
    ('dashplate_flat_jump_flow',   'dashplate_flat_jump_flow',   0.0133, 2)]:
    qv = [(-HW,-HL,z_at(-HL)+Z_BODY+zoff),(HW,-HL,z_at(-HL)+Z_BODY+zoff),
          (HW, HL,z_at( HL)+Z_BODY+zoff),(-HW, HL,z_at( HL)+Z_BODY+zoff)]
    quv = [(0,vtile),(1,vtile),(1,0),(0,0)]
    open(f'{V}/{mesh}.dae','w').write(dae(mesh, mat, qv, quv, [0,1,2,0,2,3]))
    print(mesh, '.dae written (own material)')

# ============ 4) jbeam: jump body (text-clone of XL, node rows only) ============
src = open(f'{V}/dashplate_flat.jbeam').read()
i = src.index('"dashplate_flat_body_xl": {')
m = re.search(r'\n    "', src[i+10:])
xl = src[i:i+10+m.start()]
JUMP = {'dp_1':'-4.0,-10.0, 6.9','dp_3':'-4.0, 10.0, -0.1','dp_5':' 4.0,-10.0, 6.9','dp_7':' 4.0, 10.0, -0.1',
        'dp_0':'-4.0,-10.0, 7.2','dp_2':'-4.0, 10.0, 0.2','dp_4':' 4.0,-10.0, 7.2','dp_6':' 4.0, 10.0, 0.2'}
NODE_RE = re.compile(r'^(\s*\["(dp_\d)",)\s*-?[\d.]+,\s*-?[\d.]+,\s*-?[\d.]+(\],?\s*)$')
out = []
for line in xl.splitlines():
    mm = NODE_RE.match(line)
    out.append(f'{mm.group(1)}{JUMP[mm.group(2)]}{mm.group(3)}' if mm else line)
b = '\n'.join(out)
b = b.replace('"dashplate_flat_body_xl": {', '"dashplate_flat_body_jump": {', 1)
b = re.sub(r'"name":\s*"Dash Plate Body\(Flat XXL 6x18m\)"', '"name": "Dash Plate Body(JUMP Ramp 8x20m, 19°)"', b)
b = re.sub(r'"distance":\d+', '"distance":34', b)
b = re.sub(r'"distanceMin":\d+', '"distanceMin":10', b)
mesh_part = '''"dashplate_flat_mesh_jump": {
        "information":{
            "authors":"Mathkuro",
            "name":"Dash Plate Mesh — JUMP Ramp"
        },
        "slotType" : "dashplate_meshes",
        "flexbodies": [
            ["mesh", "[group]:"],
            ["dashplate_flat_body_jump", ["dp"]],
            ["dashplate_flat_jump_design", ["dp"]],
            ["dashplate_flat_jump_flow", ["dp"]]
        ]
    },
    '''
anchor = '"dashplate_flat_mesh_500kmh_cyberglass": {'
src = src.replace(anchor, mesh_part + anchor, 1)
insert_at = src.index('"dashplate_flat_body_xl": {')
src = src[:insert_at] + b + '\n    ' + src[insert_at:]
open(f'{V}/dashplate_flat.jbeam','w').write(src)
print('jbeam: jump body + mesh part added')

# ============ 5) materials (V11 pattern: own materials) ============
mj = json.load(open(f'{V}/main.materials.json'))
import copy
OV = copy.deepcopy(mj['dashplate_flat_500kmh_cyberglass_overlay'])
OV['name'] = OV['mapTo'] = 'dashplate_flat_jump_design'
OV['Stages'][0]['baseColorMap'] = '/vehicles/dashplate_mathkuro/skins/dashplate_jump_design_b.color.png'
OV['Stages'][0]['emissiveFactor'] = [0.35, 0.1, 0.3]
mj['dashplate_flat_jump_design'] = OV
FL = copy.deepcopy(mj['dashplate_flat_500kmh_cyberglass_flow'])
FL['name'] = FL['mapTo'] = 'dashplate_flat_jump_flow'
FL['Stages'][0]['diffuseMap'] = '/vehicles/dashplate_mathkuro/skins/dashplate_jump_flow_b.color.png'
FL['Stages'][0]['scrollDir'] = [0, -1]
FL['Stages'][0]['scrollSpeed'] = 2.0
mj['dashplate_flat_jump_flow'] = FL
json.dump(mj, open(f'{V}/main.materials.json','w'), indent=2)
print('jump materials added')

# ============ 6) pc + info ============
base_pc = json.load(open(f'{V}/dashplate_fc_dash_500KMH.pc'))
p = json.loads(json.dumps(base_pc))
p['parts']['dashplate_body'] = 'dashplate_flat_body_jump'
p['parts']['dashplate_meshes'] = 'dashplate_flat_mesh_jump'
p['vars']['$dashplateTriggerRadius'] = 12
p['vars']['$dashplateDashRampSec'] = 0.6
json.dump(p, open(f'{V}/dashplate_fc_dash_500KMH_JUMP.pc','w'), indent=2)
inf = json.load(open(f'{V}/info_dashplate_fc_dash_500KMH.json'))
inf['Configuration'] = 'JUMP Ramp (500km/h) — Hyperjump'
inf['Description'] = 'Physical launch ramp 8x20 m (~19 deg): hit it with a 500 km/h boost and FLY. Magenta Hyperjump style with animated FX.'
json.dump(inf, open(f'{V}/info_dashplate_fc_dash_500KMH_JUMP.json','w'), indent=2)
print('pc + info written')

# ============ 7) structural + <p> validation ============
def loose(s):
    t = re.sub(r'^\s*//.*$','',s,flags=re.M)
    return json.loads(re.sub(r',(\s*[}\]])', r'\1', t))
j = loose(open(f'{V}/dashplate_flat.jbeam').read())
part = j['dashplate_flat_body_jump']
NODEIDS = {f'dp_{k}' for k in range(8)} | {'ref','refback','refleft','refup','refleftCorner','refrightCorner'}
def is_hdr(row): return any(str(v).endswith(':') for v in row)
ids = {r[0] for r in part['nodes'] if isinstance(r,list)} | NODEIDS
beams = [r for r in part['beams'] if isinstance(r,list) and not is_hdr(r)]
assert len(beams)==52 and all(r[0] in ids and r[1] in ids for r in beams)
print('jump body validated: 52 beams ✓')
import xml.dom.minidom as md, glob
for f in glob.glob(f'{V}/*.dae'):
    md.parse(f)
    s = open(f).read()
    cnt = int(re.search(r'<triangles[^>]*count="(\d+)"', s).group(1))
    pv = len(re.search(r'<p>([^<]*)</p>', s).group(1).split())
    assert pv == cnt*9, (f, cnt, pv)
print('ALL DAEs: <p> has exactly count*9 values ✓ (byte-exact original convention)')
