#!/usr/bin/env python3
"""Build the XL mesh DAEs for the 3x9m 500km/h Cyber-Glass pad.
- dashplate_flat_body_xl.dae  : top surface plane (3x9 grid), material maps to dashplate_flat_body_main (skinnable)
- stretches overlay + flow quads to X +/-1.5, Y +/-4.5 keeping proven UV orientation:
    v0=(minX,minY)->(0,1)  v1=(maxX,minY)->(1,1)  v2=(maxX,maxY)->(1,0)  v3=(minX,maxY)->(0,0)
"""
import re

HALF_W, HALF_L = 1.5, 4.5
Z_TOP = 0.01665657   # same as original body mesh surface

def grid_dae(name, material, nx, ny, z):
    verts, uvs, idx = [], [], []
    for j in range(ny + 1):
        for i in range(nx + 1):
            x = -HALF_W + (2 * HALF_W) * i / nx
            y = -HALF_L + (2 * HALF_L) * j / ny
            verts.append((x, y, z))
            u = i / nx
            v = 1.0 - j / ny          # back edge (minY) -> V=1, front edge -> V=0
            uvs.append((u, v))
    for j in range(ny):
        for i in range(nx):
            a = j * (nx + 1) + i
            b = a + 1
            c = a + (nx + 1) + 1
            d = a + (nx + 1)
            idx += [a, b, c, a, c, d]  # CCW seen from +Z
    pos = ' '.join(f'{x:.6f} {y:.6f} {z:.6f}' for x, y, z in verts)
    map_ = ' '.join(f'{u:.7f} {v:.7f}' for u, v in uvs)
    p = ' '.join(str(k) for k in idx)
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
        <triangles material="{name}-material" count="{len(idx)//6}">
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

with open('dashplate_flat_body_xl.dae', 'w') as f:
    f.write(grid_dae('dashplate_flat_body_xl', 'dashplate_flat_body_main', 3, 9, Z_TOP))
print('wrote dashplate_flat_body_xl.dae')

# --- stretch overlay + flow quads: swap the 4 corner positions ---
NEW = f'-{HALF_W} -{HALF_L} 0.025 {HALF_W} -{HALF_L} 0.025 {HALF_W} {HALF_L} 0.025 -{HALF_W} {HALF_L} 0.025'
for fn, z in [('dashplate_flat_500kmh_cyberglass_overlay.dae', '0.025'),
              ('dashplate_flat_500kmh_cyberglass_flow.dae', '0.03')]:
    s = open(fn).read()
    m = re.search(r'(<float_array id="[^"]*positions-array" count="12">)([^<]*)(</float_array>)', s)
    old = m.group(2)
    new = NEW.replace('0.025', z)
    s = s[:m.start(2)] + new + s[m.end(2):]
    open(fn, 'w').write(s)
    print(f'{fn}: {old.strip()} -> {new}')
