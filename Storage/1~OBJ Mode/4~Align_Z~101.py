bpy.context.scene.tool_settings.use_transform_pivot_point_align = True
bpy.ops.transform.resize(value=(1, 1, 0))
bpy.context.scene.tool_settings.use_transform_pivot_point_align = False
