bpy.context.space_data.uv_editor.lock_bounds = True
bpy.context.space_data.pivot_point = 'CURSOR'
bpy.ops.uv.select_linked()
bpy.ops.transform.translate(value=(-1000, -1000, 0))
bpy.ops.transform.resize(value=(1000, 1000, 1000))
