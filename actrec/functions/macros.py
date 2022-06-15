# region Imports
# external modules
import numpy
from typing import Optional, Tuple, Union
import mathutils

# blender modules
import bpy
from bpy.app.handlers import persistent

# relative imports
from . import shared
from .. import shared_data
from ..log import logger
# endregion

__module__ = __package__.split(".")[0]

# region Functions
def get_local_macro_index(action, id, index):
    macro = action.macros.find(id)
    if macro == -1:
        if len(action.macros) > index and index >= 0: # fallback to input index
            macro = index
        else:
            macro = action.active_macro_index # fallback to selection
    return macro

def convert_to_python(value):
    if value.__class__.__name__ == 'bpy_prop_array':
        return tuple(convert_to_python(x) for x in value)
    elif isinstance(value, mathutils.Vector):
        return value.to_tuple()
    elif isinstance(value, mathutils.Euler) or isinstance(value, mathutils.Quaternion) or isinstance(value, mathutils.Color):
        return tuple(x for x in value)
    elif isinstance(value, mathutils.Matrix):
        return tuple(row.to_tuple() for row in value)
    return value

def operator_to_dict(op) -> dict:
    data = {}
    if hasattr(op, 'macros') and op.macros:
        for key, item in op.macros.items():
            data[key] = operator_to_dict(item)
    else:
        props = op.properties
        if not hasattr(props, 'bl_rna'):
            logger.info(props)
            return props
        for key in props.bl_rna.properties.keys()[1: ]:
            data[key] = convert_to_python(getattr(props, key))
    return data
    
@persistent
def track_scene(dummy = None):
    context = bpy.context
    AR = context.preferences.addons[__module__].preferences
    operators = context.window_manager.operators
    length = len(operators)
    if length:
        if length > AR.operators_list_length:
            AR.operators_list_length = length
            op = operators[-1]
            shared_data.tracked_actions.append(['REGISTER' in op.bl_options, 'UNDO' in op.bl_options, op.bl_idname, operator_to_dict(op)])
        else:
            len_tracked = len(shared_data.tracked_actions)
            if not len_tracked:
                return
            i = 1
            op = operators[-1]
            operators_length = len(operators)
            while 'REGISTER' not in op.bl_options and operators_length > i:
                i += 1
                op = operators[-i]
            last_register_op = last_tracked = shared_data.tracked_actions[-1]
            i = 1
            while last_register_op[2] != op.bl_idname and len_tracked > i:
                i += 1
                last_register_op = shared_data.tracked_actions[-i]
            props = operator_to_dict(op)
            if last_register_op[2] == op.bl_idname and props != last_register_op[3]:
                last_register_op[3] = props
            else:
                if last_tracked[2] == "CONTEXT":
                    last_tracked[3] += 1 
                else:
                    shared_data.tracked_actions.append([True, True, "CONTEXT", 1])
    else:
        AR.operators_list_length = 0

def get_report_text(context) -> str:
    override = context.copy()
    area_type = override['area'].type
    clipboard_data = override['window_manager'].clipboard
    override['area'].type = 'INFO'
    bpy.ops.info.select_all(override, action= 'SELECT')
    bpy.ops.info.report_copy(override)
    bpy.ops.info.select_all(override, action= 'DESELECT')
    report_text = override['window_manager'].clipboard
    override['area'].type = area_type
    override['window_manager'].clipboard = clipboard_data
    return report_text

def compare_fstr_float(fstr: str, fnum: float) -> bool:
    precision = len(fstr.split(".")[-1])
    return float(fstr) == round(fnum, precision)

def compare_value(str_value, value) -> bool:
    return (isinstance(value, float) and compare_fstr_float(str_value, value)
        or isinstance(value, bool) and str_value == str(value)
        or isinstance(value, int) and str_value == str(value)
        or isinstance(value, str) and str_value[1: -1] == value)

def str_dict_to_dict(obj: str):
    "converts str in dict format to a dict with str as values"
    items = obj.strip()[1:-1].split(", ")
    data = {}
    last_key = None
    for item in items:
        split = item.split(":")
        if len(split) == 2:
            key, value = split
            last_key = key[1:-1]
            data[last_key] = value
        else:
            data[last_key] += ", %s" %split[0]
    return data

def compare_op_dict(op1_props: dict, op2_props: dict) -> bool:
    for key, str_value in op1_props.items():
        value = op2_props.get(key, None)
        if value is None:
            return False
        if "_OT_" in key:
            if compare_op_dict(str_dict_to_dict(str_value), value):
                continue
            return False
        elif isinstance(value, tuple):
            str_value = str_value[1: -1]
            if isinstance(value[0], tuple):
                value = [[value[i][j] for i in range(len(value[0]))] for j in range(len(value))] # switch column and row
                str_vectors = str_value.replace("(","").split(")")
                for str_vec, vec in zip(str_vectors, value):
                    str_vec = [x for x in str_vec.split(", ") if x]
                    for str_v, v in zip(str_vec, vec):
                        if not compare_value(str_v, v):
                            return False
            else:
                str_vec = [x for x in str_value.split(", ") if x]
                for str_v, v in zip(str_vec, value):
                    if not compare_value(str_v, v):
                        return False
        elif not compare_value(str_value, value):
            return False
    return True

def merge_report_tracked(reports, tracked_actions) -> list:
    """
    return: list of tuple (Type, Register, Undo, type, name, value[s])
        Type: 0 - Context, 1 Operator
    """
    reports = numpy.array(reports)
    tracked_actions = numpy.array(tracked_actions)
    data = []
    len_report = len(reports)
    len_tracked = len(tracked_actions)
    report_i = tracked_i = 0
    last_i = -1
    # calculate operator
    continue_report = len_report > report_i
    continue_tracked = len_tracked > tracked_i
    tracked = [True, True, "CONTEXT", 1]
    logger.info("reports: %s\ntracked:%s"%(reports, tracked_actions))
    while continue_report or continue_tracked:
        if continue_report:
            report = reports[report_i]
        if continue_tracked:
            tracked = tracked_actions[tracked_i]
        if report.startswith('bpy.ops.'):
            if last_i != report_i:
                ops_type, ops_name, ops_values = split_operator_report(report) # clean up reports first before merge with tracked actions!!!
            last_i = report_i
            if tracked[2] == "%s_OT_%s" %(ops_type.upper(), ops_name):
                if compare_op_dict(ops_values, tracked[3]):
                    if continue_report:
                        data.append((1, True, tracked[1], ops_type, ops_name, ops_values))
                    tracked_i += 1
                elif not continue_report: # no reports left use latest report
                    data.append((1, True, 'UNDO' in getattr(getattr(bpy.ops, ops_type), ops_name).bl_options, ops_type, ops_name, ops_values))
                    break
                report_i += 1
            else:
                if len_tracked <= tracked_i: # no tracked left but report operator exists
                    data.append((1, True, 'UNDO' in getattr(getattr(bpy.ops, ops_type), ops_name).bl_options, ops_type, ops_name, ops_values))
                    report_i += 1
                elif tracked[2] != 'CONTEXT': 
                    tracked_type, tracked_name = tracked[2].split("_OT_")
                    data.append((1, tracked[0], tracked[1], tracked_type.lower(), tracked_name, tracked[3]))
                tracked_i += 1
        elif report.startswith('bpy.context.'):
            if tracked[2] == 'CONTEXT':
                if continue_report:
                    source_path, attribute, value = split_context_report(report)
                    undo = not (any(x in source_path for x in ("screen", "area", "space_data")) or all(x in attribute for x in ("active", "index"))) # exclude index set of UIList
                    data.append((0, True, undo, source_path, attribute, value))
                    report_i += 1
                tracked[3] -= 1
                if tracked[3] == 0:
                    tracked_i += 1
            elif not continue_report or not tracked[0]:
                tracked_type, tracked_name = tracked[2].split("_OT_")
                data.append((1, tracked[0], tracked[1], tracked_type.lower(), tracked_name, tracked[3]))
                tracked_i += 1
            else:
                report_i += 1
        else:
            report_i += 1
            if not continue_report:
                break

        continue_report = len_report > report_i
        continue_tracked = len_tracked > tracked_i
    return data

def add_report_as_macro(context, AR, action, report: str, error_reports: list, ui_type= "") -> None:
    if report.startswith(("bpy.context.", "bpy.ops.")):
        macro = action.macros.add()
        label = shared.get_name_of_command(context, report)
        macro.id
        macro.label = AR.last_macro_label = label if label else report
        macro.command = AR.last_macro_command = report
        macro.ui_type = ui_type
        action.active_macro_index = -1
    else:
        error_reports.append(report)

def split_context_report(report) -> Tuple[list, str, str]:
    base, value = report.split(" = ")
    split = base.replace("bpy.context.", "").split(".")
    return split[:-1], split[-1], value # source_path, attribute, value

def get_id_object(context, source_path, attribute):
    if source_path[0] == 'area':
        for area in context.screen.areas:
            if hasattr(trace_object(area, source_path[1:]), attribute):
                return area
    elif source_path[0] == 'space_data':
        for area in context.screen.areas:
            for space in area.spaces:
                if hasattr(trace_object(space, source_path[1:]), attribute):
                    return space
    return trace_object(context, source_path)

def trace_object(base, path):
    for x in path:
        base = getattr(base, x)
    return base

def get_copy_of_object(data, obj, attribute, depth= 5):
    if depth and obj:
        if hasattr(obj, attribute):
            return {attribute : getattr(obj, attribute)}
        if hasattr(obj, 'bl_rna'):
            for prop in obj.bl_rna.properties[1: ]:
                if prop.type == 'COLLECTION' or prop.type == 'POINTER':
                    sub_obj = getattr(obj, prop.identifier)
                    if obj != sub_obj:
                        res = get_copy_of_object({}, sub_obj, attribute, depth - 1)
                        if res != {}:
                            data[prop.identifier] = res
    return data

def create_object_copy(context, source_path: list, attribute: str) -> dict:
    data = {}
    id_object = get_id_object(context, source_path, attribute)
    res = get_copy_of_object(data, id_object, attribute)
    if res and not isinstance(res, dict):
        data[attribute] = res
    return data

def check_object_report(obj, copy_dict, source_path, attribute: str, value):
    if hasattr(obj, attribute) and getattr(obj, attribute) != copy_dict[attribute]:
        return obj.__class__, ".".join(source_path), attribute, value
    for key in copy_dict:
        if hasattr(obj, key):
            if isinstance(copy_dict[key], dict):
                res = check_object_report(getattr(obj, key), copy_dict[key], [*source_path, key], attribute, value)
                if res:
                    return res
    return

def improve_context_report(context, copy_dict: dict, source_path: list, attribute: str, value: str) -> str:
    id_object = get_id_object(context, source_path, attribute)
    if hasattr(id_object, attribute):
        object_class = id_object.__class__
        res = [".".join(source_path), attribute, value]
    else:
        res = check_object_report(id_object, copy_dict, source_path, attribute, value)
        if res:
            object_class, *res = res
        else:
            object_class, *res = id_object.__class__, ".".join(source_path), attribute, value
    for attr in context.__dir__():
        if (attr not in set(
            "button_pointer", "id", "texture_slot", "mesh", "armature", "lattice", "curve", "meta_ball", "speaker",
            "lightprobe", "camera", "material_slot", "texture", "texture_user", "texture_user_property", "bone", "edit_bone", 
            "pose_bone", 
            ) and isinstance(getattr(bpy.context, attr), object_class)): # exclude Buttons Context https://docs.blender.org/api/current/bpy.context.html#buttons-context
            res[0] = attr
            break
    return "bpy.context.%s.%s = %s" %tuple(res)

def split_operator_report(operator_str: str) -> Tuple[str, str, dict]:
    ops_type, ops_name = operator_str.replace("bpy.ops.", "").split("(")[0].split(".")
    ops_values = {}
    key = ""
    for x in "(".join(operator_str.split("(")[1:])[:-1].split(", "):
        if x:
            split = x.split("=")
            if split[0].strip().isidentifier() and len(split) > 1:
                key = split[0]
                ops_values[key] = split[1]
            else:
                ops_values[key] += ", %s"%(split[0])
    return ops_type, ops_name, ops_values

def dict_to_kwarg_str(values: dict) -> str:
    return ", ".join(f"{key}={value}" for key, value in values.items())

def create_operator_based_copy(context, ops_type: str, ops_name: str, ops_values: dict) -> Union[dict, bool, None]:
    if ops_type == "outliner":
        if ops_name in {"item_activate", "item_rename"}:
            return False
        elif ops_name in {"collection_drop"}:
            return True

def imporve_operator_report(context, ops_type: str, ops_name: str, ops_values: dict, copy_data):
    if copy_data:
        if ops_type == "outliner":
            if ops_name == "collection_drop":
                return "bpy.ops.ar.helper_object_to_collection()"
    return "bpy.ops.%s.%s(%s)" %(ops_type, ops_name, dict_to_kwarg_str(ops_values))

# endregion