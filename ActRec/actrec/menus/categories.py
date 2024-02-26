# region Imports
# blender modules
import bpy
from bpy.types import Menu, Context

# relative imports
from ..functions.shared import get_preferences
from .. import ui_functions
# endregion

# region Menus


class AR_MT_Categories(Menu):
    bl_label = "Categories"
    bl_idname = "AR_MT_Categories"

    @classmethod
    def poll(cls, context: Context) -> bool:
        return (context.area is not None)

    def draw(self, context: Context) -> None:
        layout = self.layout
        ActRec_pref = get_preferences(context)
        if not ActRec_pref.is_loaded:  # loads the actions if not already done
            ActRec_pref.is_loaded = True
        for index, category in enumerate(ui_functions.get_visible_categories(ActRec_pref, context)):
            layout.menu("AR_MT_category_%s" % index, text=category.label)
# endregion


def register():
    bpy.utils.register_class(AR_MT_Categories)


def unregister():
    bpy.utils.unregister_class(AR_MT_Categories)
