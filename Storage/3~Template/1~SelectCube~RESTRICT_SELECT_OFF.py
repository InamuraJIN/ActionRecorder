bpy.context.scene.objects.get("Cube").select_set(True)
bpy.context.view_layer.objects.active = bpy.context.scene.objects.get("Cube")
