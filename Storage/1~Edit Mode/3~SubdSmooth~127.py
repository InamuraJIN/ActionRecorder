bpy.ops.object.subdivision_set(level=1, relative=False)
bpy.ops.object.editmode_toggle()
bpy.ops.object.shade_smooth()
bpy.ops.object.editmode_toggle()
bpy.context.object.data.use_auto_smooth = True
bpy.context.object.data.auto_smooth_angle = 3.14159
