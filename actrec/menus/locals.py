# region Imports
# external modules
from contextlib import suppress

# blender modules
import bpy
from bpy.types import Menu
# endregion

__module__ = __package__.split(".")[0]

# region Menus
class AR_MT_action_pie(Menu):
    bl_idname = "AR_MT_action_pie"
    bl_label = "ActRec Pie Menu"

    def draw(self, context):
        AR = context.preferences.addons[__module__].preferences
        pie = self.layout.menu_pie()
        actions = AR.local_actions
        for i in range(len(actions)):
            if i >= 8:
                break
            action = actions[i]
            ops = pie.operator("ar.local_play", text= actions[i].label, icon_value= action.icon if action.icon else 101)
            ops.id = action.id
            ops.index = i

def menu_draw(self, context):
    layout = self.layout
    layout.separator()
    layout.operator("ar.copy_to_actrec")
    button_prop = getattr(context, "button_prop", None)
    if button_prop and hasattr(button_prop, 'is_array') and button_prop.is_array:
        layout.operator("ar.copy_to_actrec", text= "Copy to Action Recorder (Single)").copy_single = True


class WM_MT_button_context(Menu):
    bl_label = "Unused"

    def draw(self, context):
        pass
# endregion

classes = [
    AR_MT_action_pie
]
internal_classes = [
    WM_MT_button_context
]

# region Registration
def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    for cls in internal_classes:
        with suppress(Exception):
            bpy.utils.register_class(cls)
    with suppress(Exception):
        bpy.types.WM_MT_button_context.append(menu_draw)
def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)
    for cls in internal_classes:
        with suppress(Exception):
            bpy.utils.unregister_class(cls)
    with suppress(Exception):
        bpy.types.WM_MT_button_context.remove(menu_draw)
# endregion
