# region Imports

# blender modules
import bpy
# endregion

# region UI functions


def draw_global_action(layout: bpy.types.UILayout, ActRec_pref: bpy.types.AddonPreferences, id: str):
    """
    draws row of global action button.

    Args:
        layout (bpy.types.UILayout): UI context of Blender
        ActRec_pref (bpy.types.AddonPreferences): preferences of this addon
        id (str): UUID of the action, use action.id the get the UUID
    """
    action = ActRec_pref.global_actions[id]
    row = layout.row(align=True)
    row.alert = action.alert
    row.prop(action, 'selected', toggle=1,
             icon='LAYER_ACTIVE' if action.selected else 'LAYER_USED', text="", event=True)
    op = row.operator("ar.global_icon", text="",
                      icon_value=action.icon if action.icon else 101)
    op.id = id
    op = row.operator("ar.global_execute_action", text=action.label)
    op.id = id
# endregion
