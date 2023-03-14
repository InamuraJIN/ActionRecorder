# region Imports
# blender modules
import bpy
from bpy.types import Menu

# relative imports
from .. import keymap
from ..functions.shared import get_preferences
# endregion



class AR_MT_Categories(Menu):
    bl_label = "Categories"
    bl_idname = "AR_MT_Categories"

    def draw(self, context):
        layout = self.layout
        ActRec_pref = get_preferences(context)
        for category in ActRec_pref.categories:
            
            


def register():
    bpy.utils.register_class(SimpleCustomMenu)


def unregister():
    bpy.utils.unregister_class(SimpleCustomMenu)

if __name__ == "__main__":
    register()

    # The menu can also be called from scripts
    bpy.ops.wm.call_menu(name=SimpleCustomMenu.bl_idname)