bpy.ops.object.camera_add()
bpy.context.active_object.name = 'Camera'
bpy.ops.object.select_pattern(pattern="Empty")
bpy.context.scene.objects.get("Empty").select_set(True)
bpy.context.view_layer.objects.active = bpy.context.scene.objects.get("Empty")
bpy.ops.object.track_set(type='TRACKTO')
