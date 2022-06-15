# region Imports
# external modules
import webbrowser
import time

# blender modules
import bpy
from bpy.types import Operator
from bpy.props import StringProperty, IntProperty

# relative import
from .. import shared_data, functions
# endregion

__module__ = __package__.split(".")[0]

# region Operators
class AR_OT_check_ctrl(Operator):
    bl_idname = "ar.check_ctrl"
    bl_label = "Check Ctrl"
    bl_options = {'INTERNAL'}

    def execute(self, context):
        return {"FINISHED"}

    def invoke(self, context, event):
        if event.ctrl:
            return {"FINISHED"}
        return {"CANCELLED"}

class id_based(Operator):
    id : StringProperty(name= "id", description= "id of the action (1. indicator)")
    index : IntProperty(name= "index", description= "index of the action (2. indicator)", default= -1)

    def clear(self):
        self.id = ""
        self.index = -1
# endregion

classes = [
    AR_OT_check_ctrl
]

# region Registration
def register():
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)
# endregion