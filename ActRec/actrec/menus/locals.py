# region Imports
# external modules
from contextlib import suppress

# blender modules
import bpy
from bpy.types import Menu, Context

# relative imports
from .. import keymap
from ..functions.shared import get_preferences
from .. import functions
# endregion


# region Menus


class AR_MT_action_pie(Menu):
    bl_idname = "AR_MT_action_pie"
    bl_label = "ActRec Pie Menu"

    def draw(self, context: Context) -> None:
        ActRec_pref = get_preferences(context)
        pie = self.layout.menu_pie()
        actions = ActRec_pref.local_actions
        for i in range(len(actions)):
            if i >= 8:
                break
            action = actions[i]
            ops = pie.operator("ar.local_play", text=actions[i].label, icon_value=action.icon if action.icon else 101)
            ops.id = action.id
            ops.index = i

# based on
# https://docs.blender.org/api/current/bpy.types.Menu.html?highlight=menu_draw#extending-the-button-context-menu


def menu_draw(self, context: Context) -> None:
    layout = self.layout
    layout.separator()
    layout.operator("ar.copy_to_actrec")
    button_prop = getattr(context, "button_prop", None)
    if button_prop and hasattr(button_prop, 'is_array') and button_prop.is_array:
        layout.operator("ar.copy_to_actrec", text="Copy to Action Recorder (Single)").copy_single = True
    button_operator = getattr(context, "button_operator", None)
    if button_operator and button_operator.bl_rna.identifier == "AR_OT_global_execute_action":
        km = context.window_manager.keyconfigs.user.keymaps['Screen']
        kmi = km.keymap_items.find_from_operator(
            "ar.global_execute_action",
            properties=button_operator
        )
        if kmi:
            layout.operator("ar.remove_ar_shortcut").id = button_operator.id
        else:
            layout.operator("ar.add_ar_shortcut").id = button_operator.id
        layout.operator("ar.global_edit").id = button_operator.id


class WM_MT_button_context(Menu):
    bl_label = "Unused"

    def draw(self, context: Context) -> None:
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

    with suppress(Exception):
        bpy.types.WM_MT_button_context.remove(menu_draw)
    for cls in internal_classes:
        with suppress(Exception):
            bpy.utils.unregister_class(cls)
# endregion
