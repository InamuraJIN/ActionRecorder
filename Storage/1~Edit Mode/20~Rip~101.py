bpy.ops.mesh.tris_convert_to_quads(face_threshold=3.14159, shape_threshold=3.14159, uvs=True)
bpy.ops.uv.select_all(action='SELECT')
bpy.ops.uv.seams_from_islands()
