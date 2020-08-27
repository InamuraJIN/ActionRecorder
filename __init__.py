import bpy
from . import ActionRecorder as ActionRecorder

bl_info = {
    "name" : "ActionRecorder",
    "author" : "InamuraJIN, Rivin",
    "version": (3, 4, 0),
    "blender": (2, 83, 0),
    "location" : "View 3D",
    "warning" : "",
    "wiki_url" : "https://github.com/InamuraJIN/CommandRecorder/blob/master/README.md",# Documentation
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
    print("------- Registered Action Recorder -------")

def unregister():
    for cls in ActionRecorder.classes:
        bpy.utils.unregister_class(cls)
    for cls in ActionRecorder.categoriesclasses:
        try:
            bpy.utils.unregister_class(cls)
        except:
            continue
    for cls in ActionRecorder.classespanel:
        bpy.utils.unregister_class(cls)
    ActionRecorder.Clear_Props()
    print("------- Unregistered Action Recorder -------")
