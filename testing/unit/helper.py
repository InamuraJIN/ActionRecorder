import bpy
from ActRec.actrec.functions.shared import get_preferences


def compare_with_dict(obj, compare_dict):
    for key, value in compare_dict.items():
        if isinstance(value, dict):
            check = compare_with_dict(getattr(obj, key), value)
        elif isinstance(value, list):
            check = all(compare_with_dict(getattr(obj, key)[i], x) for i, x in enumerate(value))
        else:
            check = getattr(obj, key) == value
        if not check:
            print(key, value, getattr(obj, key))
            return check
    return True


def get_pref_data(param):
    pref = get_preferences(bpy.context)
    params = param.split(".")
    prop = pref
    for param in params:
        att_sp = param.split("[")
        prop = getattr(prop, att_sp[0])
        if len(att_sp) == 2:
            prop = prop[att_sp[1][:-1].replace('"', "")]  # remove ]
    return prop


def load_global_actions_test_data(pref):
    action = pref.global_actions.add()
    action.id = "c7a1f271164611eca91770c94ef23b30"
    action.label = "Delete"
    macro = action.macros.add()
    macro.id = "c7a3dcba164611ecaaec70c94ef23b30"
    macro.label = "Delete"
    macro.command = "bpy.ops.object.delete(use_global=False)"
    action.icon = 3

    action = pref.global_actions.add()
    action.id = "c7a40353164611ecbaad70c94ef23b30"
    action.label = "Subd Smooth"
    macro = action.macros.add()
    macro.id = "c7a40354164611ecb05c70c94ef23b30"
    macro.label = "Subdivision Set"
    macro.command = "bpy.ops.object.subdivision_set(level=1, relative=False)"
    macro = action.macros.add()
    macro.id = "c7a40355164611ecb9cd70c94ef23b30"
    macro.label = "Shade Smooth"
    macro.command = "bpy.ops.object.shade_smooth()"
    macro = action.macros.add()
    macro.id = "c7a42aa4164611ecba6570c94ef23b30"
    macro.label = "Auto Smooth = True"
    macro.command = "bpy.context.object.data.use_auto_smooth = True"
    macro = action.macros.add()
    macro.id = "c7a6be1e164611ec8ede70c94ef23b30"
    macro.label = "Auto Smooth Angle = 3.14159"
    macro.command = "bpy.context.object.data.auto_smooth_angle = 3.14159"
    action.icon = 127

    action = pref.global_actions.add()
    action.id = "c7a6be1f164611ec9a5570c94ef23b30"
    action.label = "Align_X"
    macro = action.macros.add()
    macro.id = "c7a6e499164611ec927970c94ef23b30"
    macro.label = "Only Locations = True"
    macro.command = "bpy.context.scene.tool_settings.use_transform_pivot_point_align = True"
    macro = action.macros.add()
    macro.id = "c7a6e49a164611ec9f1370c94ef23b30"
    macro.label = "Resize"
    macro.command = "bpy.ops.transform.resize(value=(1, 0, 1))"
    macro = action.macros.add()
    macro.id = "c7a6e49b164611ecadb070c94ef23b30"
    macro.label = "Only Locations = False"
    macro.command = "bpy.context.scene.tool_settings.use_transform_pivot_point_align = False"
