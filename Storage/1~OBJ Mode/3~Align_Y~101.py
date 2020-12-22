bpy.context.scene.tool_settings.use_transform_pivot_point_align = True
bpy.ops.transform.resize(value=(0, 1, 1))
bpy.context.scene.tool_settings.use_transform_pivot_point_align = False
