bpy.ops.mesh.subdivide(number_cuts=2)
ar.event:{"Type": "Timer", "Time": 1.0}
bpy.ops.mesh.bevel(offset=0.15, offset_pct=0, affect='EDGES')
