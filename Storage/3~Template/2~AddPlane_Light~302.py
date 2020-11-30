bpy.ops.mesh.primitive_plane_add(align='CURSOR', rotation=(-1.5708, 0, 0))
bpy.ops.object.transform_apply(location=False, rotation=True, scale=False)
bpy.context.active_object.name = 'Plane_Light'
bpy.ops.object.select_pattern(pattern="Empty")
bpy.ops.object.constraint_add_with_targets(type='TRACK_TO')
bpy.context.object.hide_render = True
