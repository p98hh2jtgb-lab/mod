#!/usr/bin/env python3
"""STEEL STUNT LAUNCH RAMP — modular (3 segments: 8°/18°/30°), curved feel,
steel truss sides with cross-bracing + weld points, white centerline,
animated amber edge lights. Collision == visual (nodes at module seams)."""
import re, json, itertools

V = '/home/user/mod/extracted/vehicles/dashplate_mathkuro'
HW = 2.25                       # 4.5 m wide
# module rows: (y, surface z) — flush entry -> steep launch
ROWS = [(-8.0, 0.01), (-1.07, 0.99), (3.52, 2.54), (6.98, 4.54)]
BASE_Y = (-8.0, 7.0)            # ground plate ends
BASE_Z = -0.08
ZB = 0.01665657                 # visual offset above collision plane

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

# =================== 1) SURFACE GRID (3 modules, matches physics rows) ===================
cols = [-HW, -HW/3, HW/3, HW]
verts, uvs, idx = [], [], []
y0, y1 = ROWS[0][0], ROWS[-1][0]
for (ry, rz) in ROWS:
    for x in cols:
        verts.append((x, ry, rz + ZB))
        uvs.append(((x/HW+1)/2, (ry - y0)/(y1 - y0)))   # v: 0 exit .. 1 entry
for r in range(len(ROWS)-1):
    for c in range(len(cols)-1):
        a=r*4+c; b=a+1; c2=a+5; d=a+4
        idx += [a,b,c2, a,c2,d]
open(f'{V}/dashplate_flat_body_stunt.dae','w').write(
    dae('dashplate_flat_body_stunt', 'dashplate_flat_stuntramp_surface', verts, uvs, idx))
print('stunt surface grid (3 modules) written')

# =================== 2) SIDE TRUSS PANELS (both sides in one DAE) ===================
verts, uvs, idx = [], [], []
for k, xs in ((0,-HW),(1,HW)):
    base_i = len(verts)
    # top edge follows surface: A,B,C,D ; bottom edge on ground plate
    top = [(ry, rz+ZB) for (ry,rz) in ROWS]
    bot = [(BASE_Y[0], BASE_Z+0.02), (BASE_Y[1], BASE_Z+0.02)]
    poly = [(xs,*top[0]),(xs,*top[1]),(xs,*top[2]),(xs,*top[3]),(xs,bot[1][0],bot[1][1]),(xs,bot[0][0],bot[0][1])]
    ymin, ymax, zmax = BASE_Y[0], BASE_Y[1], 5.2
    for (x,y,z) in poly:
        verts.append((x,y,z)); uvs.append(((y-ymin)/(ymax-ymin), z/zmax))
    idx += [base_i,base_i+1,base_i+2, base_i,base_i+2,base_i+3, base_i,base_i+3,base_i+4, base_i,base_i+4,base_i+5]
open(f'{V}/dashplate_flat_stunt_sides.dae','w').write(
    dae('dashplate_flat_stunt_sides', 'dashplate_flat_stuntramp_sides', verts, uvs, idx))
print('side truss panels written (2 polygons, 8 tris)')

# =================== 3) EDGE LIGHT STRIPS (animated amber) ===================
verts, uvs, idx = [], [], []
for k, side in ((0,-1),(1,1)):
    for (xa, xb) in ((-HW+0.02, -HW+0.24), (HW-0.24, HW-0.02)):   # inner/outer thin strip per side
        base_i = len(verts)
        for (ry, rz) in ROWS:
            verts.append((xa, ry, rz + ZB + 0.012)); uvs.append((0, (ry-y0)/(y1-y0)))
        for (ry, rz) in ROWS:
            verts.append((xb, ry, rz + ZB + 0.012)); uvs.append((1, (ry-y0)/(y1-y0)))
        # rows: 4 top then 4 bottom (same order); quads between consecutive rows
        for r in range(3):
            a=base_i+r; b=a+4; c=a+5; d=a+1
            idx += [a,b,c, a,c,d]
open(f'{V}/dashplate_flat_stunt_edges.dae','w').write(
    dae('dashplate_flat_stunt_edges', 'dashplate_flat_stuntramp_edge', verts, uvs, idx))
print('edge light strips written (6 quads, animated)')

# =================== 4) PHYSICS BODY (modular nodes, collision == visual) ===================
N = {}
for r,(ry,rz) in zip('ABCD', ROWS):
    N[f's{r}_l'] = (-HW, ry, rz); N[f's{r}_r'] = (HW, ry, rz)
N['sE_l'] = (-HW, BASE_Y[0], BASE_Z); N['sE_r'] = (HW, BASE_Y[0], BASE_Z)
N['sF_l'] = (-HW, BASE_Y[1], BASE_Z); N['sF_r'] = (HW, BASE_Y[1], BASE_Z)
surf_ids = ['sA_l','sA_r','sB_l','sB_r','sC_l','sC_r','sD_l','sD_r']
base_ids = ['sE_l','sE_r','sF_l','sF_r']
all_ids = surf_ids + base_ids
beams = [list(p) for p in itertools.combinations(all_ids, 2)]      # 66 fully-connected rigid
refs = ['ref','refback','refleft','refup','refleftCorner','refrightCorner']
for rf in refs:
    for t in ['sA_l','sA_r','sD_l','sD_r','sE_l','sE_r','sF_l','sF_r']:
        beams.append([rf, t])
tris = [
 ['sA_l','sA_r','sB_r'], ['sA_l','sB_r','sB_l'],
 ['sB_l','sB_r','sC_r'], ['sB_l','sC_r','sC_l'],
 ['sC_l','sC_r','sD_r'], ['sC_l','sD_r','sD_l'],
 ['sE_l','sE_r','sF_r'], ['sE_l','sF_r','sF_l']]

node_lines = []
for nid,(x,y,z) in N.items():
    node_lines.append(f'             ["{nid}",{x:g},{y:g},{z:g}],')
surf_sec = '\n'.join(node_lines[:8])
base_sec = '\n'.join(node_lines[8:])
beam_sec = '\n'.join(f'              ["{a}","{b}"],' for a,b in beams)
tri_sec = '\n'.join(f'               ["{a}", "{b}", "{c}"],' for a,b,c in tris)
body = f'''    "dashplate_flat_body_stunt": {{
        "information": {{
            "authors": "mathkuro (based on official Kick Plate)",
            "name": "Stunt Ramp Body (Steel 4.5x15m, 3 modules)"
        }},
        "slotType": "dashplate_body",
        "slots": [
            ["type", "default", "description"]
        ],
        "refNodes":[
            ["ref:", "back:", "left:", "up:", "leftCorner:", "rightCorner:"],
            ["ref", "refback", "refleft", "refup", "refleftCorner", "refrightCorner"]
        ],
        "cameraExternal":{{
            "distance":26,
            "distanceMin":8,
            "offset":{{"x":0, "y":1.5, "z":1}},
            "fov":65
        }},
        "flexbodies": [
            ["mesh", "[group]:", "nonFlexMaterials"]
        ],
        "nodes": [
             ["id", "posX", "posY", "posZ"],
             {{"frictionCoef":10.0}},
             {{"nodeMaterial":"|NM_METAL"}},

             //up refnode
             {{"collision":false}},
             ["ref", 0.0, 0.0, 0.0],
             ["refback", 0.0, 1.0, 0.0],
             ["refleft", 2.0, 0.0, 0.0],
             ["refup", 0.0, 0.0, 0.2],
             ["refleftCorner", 2.0, -2.0, 0.0],
             ["refrightCorner", -2.0, -2.0, 0.0],

             //stunt ramp surface modules (collision rows)
             {{"collision":true}},
             {{"selfCollision":false}},
             {{"group":"dp"}},
             {{"nodeWeight":500}},
{surf_sec}

             //ground plate
{base_sec}
            ],
        "beams": [
              ["id1:", "id2:"],
              {{"beamPrecompression":1, "beamType":"|NORMAL", "beamLongBound":1.0, "beamShortBound":1.0}},
              {{"beamSpring":50001000,"beamDamp":5000}},
              {{"beamDeform":"FLT_MAX","beamStrength":"FLT_MAX"}},
              // fully-connected rigid frame
{beam_sec},

              //refnode ties
              {{"beamSpring":100000,"beamDamp":10000}}
        ],
        "triangles": [
               ["id1:","id2:","id3:"],
               {{"groundModel":"dashplate"}},
               //surface modules
{tri_sec}
            ],
        "general": {{
         "enableTracking": false
        }}
    }},
'''
src = open(f'{V}/dashplate_flat.jbeam').read()
anchor = '"dashplate_flat_body_xl": {'
src = src.replace(anchor, body + '    ' + anchor, 1)
mesh_part = '''"dashplate_flat_mesh_stunt": {
        "information":{
            "authors":"Mathkuro",
            "name":"Dash Plate Mesh — Steel Stunt Ramp"
        },
        "slotType" : "dashplate_meshes",
        "flexbodies": [
            ["mesh", "[group]:"],
            ["dashplate_flat_body_stunt", ["dp"]],
            ["dashplate_flat_stunt_sides", ["dp"]],
            ["dashplate_flat_stunt_edges", ["dp"]]
        ]
    },
    '''
anchor2 = '"dashplate_flat_mesh_500kmh_cyberglass": {'
src = src.replace(anchor2, mesh_part + anchor2, 1)
open(f'{V}/dashplate_flat.jbeam','w').write(src)
print('jbeam: stunt body (12 nodes, %d beams, 8 tris) + mesh part' % len(beams))

# =================== 5) MATERIALS ===================
mj = json.load(open(f'{V}/main.materials.json'))
mj['dashplate_flat_stuntramp_surface'] = {
  "name":"dashplate_flat_stuntramp_surface","mapTo":"dashplate_flat_stuntramp_surface","class":"Material",
  "Stages":[{"baseColorMap":"/vehicles/dashplate_mathkuro/skins/dashplate_stunt_surface_b.color.png",
              "metallicFactor":0.72,"clearCoatFactor":0.3,"clearCoatRoughnessFactor":0.35,
              "emissiveFactor":[0.03,0.03,0.04]},{},{},{}],
  "activeLayers":1,"castShadows":False,"doubleSided":True,"invertBackFaceNormals":True,"version":1.5}
mj['dashplate_flat_stuntramp_sides'] = {
  "name":"dashplate_flat_stuntramp_sides","mapTo":"dashplate_flat_stuntramp_sides","class":"Material",
  "Stages":[{"baseColorMap":"/vehicles/dashplate_mathkuro/skins/dashplate_stunt_sides_b.color.png",
              "metallicFactor":0.8,"clearCoatFactor":0.2,"clearCoatRoughnessFactor":0.4,
              "emissiveFactor":[0.02,0.02,0.03]},{},{},{}],
  "activeLayers":1,"castShadows":False,"doubleSided":True,"invertBackFaceNormals":True,"version":1.5}
import copy
FL = copy.deepcopy(mj['dashplate_flat_500kmh_cyberglass_flow'])
FL['name'] = FL['mapTo'] = 'dashplate_flat_stuntramp_edge'
FL['Stages'][0]['diffuseMap'] = '/vehicles/dashplate_mathkuro/skins/dashplate_stunt_edge_flow_b.color.png'
FL['Stages'][0]['scrollDir'] = [0, -1]
FL['Stages'][0]['scrollSpeed'] = 1.1
mj['dashplate_flat_stuntramp_edge'] = FL
json.dump(mj, open(f'{V}/main.materials.json','w'), indent=2)
print('materials written')

# =================== 6) PC + INFO ===================
p = json.load(open(f'{V}/dashplate_fc_dash_500KMH.pc'))
p['parts']['dashplate_body'] = 'dashplate_flat_body_stunt'
p['parts']['dashplate_meshes'] = 'dashplate_flat_mesh_stunt'
p['vars']['$dashplateTriggerRadius'] = 9
p['vars']['$dashplateDashRampSec'] = 0.6
json.dump(p, open(f'{V}/dashplate_fc_dash_500KMH_STUNT.pc','w'), indent=2)
inf = json.load(open(f'{V}/info_dashplate_fc_dash_500KMH.json'))
inf['Configuration'] = 'Stunt Ramp (500km/h) — Steel Launch Curve'
inf['Description'] = 'Heavy-duty steel stunt launch ramp: modular 3-segment curve (8/18/30 deg) with truss sides, cross-bracing and animated amber edge lights. Boost 500 km/h and launch.'
json.dump(inf, open(f'{V}/info_dashplate_fc_dash_500KMH_STUNT.json','w'), indent=2)
print('pc + info written')

# =================== 7) VALIDATE ===================
def loose(s):
    t = re.sub(r'^\s*//.*$','',s,flags=re.M)
    return json.loads(re.sub(r',(\s*[}\]])', r'\1', t))
j = loose(src)
part = j['dashplate_flat_body_stunt']
def is_hdr(row): return any(str(v).endswith(':') for v in row)
ids = {r[0] for r in part['nodes'] if isinstance(r,list)}
assert len(ids) == 18, ids   # 12 + 6 refs
beams_v = [r for r in part['beams'] if isinstance(r,list) and not is_hdr(r)]
assert all(len(r)==2 and r[0] in ids and r[1] in ids for r in beams_v), 'bad beams'
tris_v = [r for r in part['triangles'] if isinstance(r,list) and not is_hdr(r)]
assert all(len(r)==3 and all(n in ids for n in r) for r in tris_v)
print(f'stunt body validated: {len(ids)} nodes, {len(beams_v)} beams, {len(tris_v)} tris ✓')
import glob, xml.dom.minidom as md
for f in glob.glob(f'{V}/*.dae'):
    md.parse(f)
    s = open(f).read()
    tri = re.search(r'<triangles[^>]*count="(\d+)"[^>]*>(.*?)</triangles>', s, re.S)
    cnt = int(tri.group(1))
    pv = len(re.search(r'<p>([^<]*)</p>', tri.group(2)).group(1).split())
    assert pv == cnt*9, (f, cnt, pv)
print('ALL DAEs valid (p = count*9) ✓')
