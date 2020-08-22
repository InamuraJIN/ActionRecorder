import bpy
from . import ActionRecorder as ActionRecorder

bl_info = {
    "name" : "ActionRecorder",
    "author" : "InamuraJIN, Rivin",
    "version": (3, 3, 1),
    "blender": (2, 83, 0),
    "location" : "View 3D",
    "warning" : "",
    "wiki_url" : "https://inamurajin.wixsite.com/website/post/hint-help",# Documentation
    "tracker_url" : "https://twitter.com/Inamura_JIN",# Report Bug
    'link': 'https://twitter.com/Inamura_JIN',
    "category" : "System"
}

def register():
    for cls in ActionRecorder.classes:
        bpy.utils.register_class(cls)
    for cls in ActionRecorder.classespanel:
        bpy.utils.register_class(cls)
    ActionRecorder.Initialize_Props()
    print("Register")

def unregister():
    for cls in ActionRecorder.classes:
        bpy.utils.unregister_class(cls)
    for cls in ActionRecorder.categoriesclasses:
        bpy.utils.unregister_class(cls)
    for cls in ActionRecorder.classespanel:
        bpy.utils.unregister_class(cls)
    ActionRecorder.Clear_Props()
    print("UnRegister")
