bpy.ops.mesh.mark_seam(clear=True)
bpy.ops.uv.unwrap()
bpy.ops.uv.seams_from_islands()
bpy.ops.mesh.select_linked(delimit=set())
bpy.ops.uv.unwrap()
