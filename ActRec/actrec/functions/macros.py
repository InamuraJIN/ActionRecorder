# region Imports
# external modules
import numpy
from typing import Tuple, Union
import mathutils

# blender modules
import bpy
from bpy.app.handlers import persistent

# relative imports
from . import shared
from .. import shared_data
from ..log import logger
from .shared import get_preferences
# endregion


# region Functions


def get_local_macro_index(action: 'AR_local_actions', id: str, index: int) -> int:
    """
    get macro index of action based on the given id or index (checks if index in range)
    fallback to selection if macro doesn't exists

    Args:
        action (AR_local_actions): action to get macro index from
        id (str): id of the macro
        index (int): index for fallback (checks if index in range)

    Returns:
        int: found macro index or active macro index if not found
    """
    # REFACTOR indentation
    macro = action.macros.find(id)
    if macro == -1:
        if len(action.macros) > index and index >= 0:  # fallback to input index
            macro = index
        else:
            macro = action.active_macro_index  # fallback to selection
    return macro


def convert_value_to_python(value) -> tuple:
    """
    convert value of a Blender Property to a suitable python format
    converts: bpy_prop_array, mathutils.Vector, mathutils.Euler, mathutils.Quaternion, mathutils.Color, mathutils.Matrix

    Args:
        value (any): value to convert to python format

    Returns:
        tuple: python format of value
    """
    if value.__class__.__name__ == 'bpy_prop_array':
        return tuple(convert_value_to_python(x) for x in value)
    elif isinstance(value, mathutils.Vector):
        return value.to_tuple()
    elif (isinstance(value, mathutils.Euler)
          or isinstance(value, mathutils.Quaternion)
          or isinstance(value, mathutils.Color)):
        return tuple(x for x in value)
    elif isinstance(value, mathutils.Matrix):
        return tuple(row.to_tuple() for row in value)
    return value


def operator_to_dict(ops: bpy.types.Operator) -> dict:
    """
    converts an operator properties to a dictionary

    Args:
        ops (bpy.types.Operator): operator to extract data from

    Returns:
        dict: properties of operator
    """
    data = {}
    if hasattr(ops, 'macros') and ops.macros:
        for key, item in ops.macros.items():
            data[key] = operator_to_dict(item)
    else:
        props = ops.properties
        if not hasattr(props, 'bl_rna'):
            return props
        for key in props.bl_rna.properties.keys()[1:]:
            data[key] = convert_value_to_python(getattr(props, key))
    return data


@persistent
def track_scene(dummy: bpy.types.Scene = None):
    """
    tracks the scene to have more information for macro creation

    Args:
        dummy (bpy.types.Scene, optional): unused. Defaults to None.
    """
    # REFACTOR indentation
    context = bpy.context
    ActRec_pref = get_preferences(context)
    operators = context.window_manager.operators
    length = len(operators)
    if length:
        if length > ActRec_pref.operators_list_length:
            ActRec_pref.operators_list_length = length
            op = operators[-1]
            shared_data.tracked_actions.append(
                ['REGISTER' in op.bl_options, 'UNDO' in op.bl_options, op.bl_idname, operator_to_dict(op)]
            )
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
        ActRec_pref.operators_list_length = 0


def get_report_text(context: bpy.types.Context) -> str:
    """
    extract all reports from Blender

    Args:
        context (bpy.types.Context): active blender context

    Returns:
        str: report text
    """
    override = context.copy()
    area_type = override['area'].type
    clipboard_data = override['window_manager'].clipboard
    override['area'].type = 'INFO'
    bpy.ops.info.select_all(override, action='SELECT')
    bpy.ops.info.report_copy(override)
    bpy.ops.info.select_all(override, action='DESELECT')
    report_text = override['window_manager'].clipboard
    override['area'].type = area_type
    override['window_manager'].clipboard = clipboard_data
    return report_text


def compare_fstr_float(fstr: str, fnum: float) -> bool:
    """
    compare if float str is equal to a float number

    Args:
        fstr (str): float as str
        fnum (float): float to compare to

    Returns:
        bool: equal compare result
    """
    precision = len(fstr.split(".")[-1])
    return float(fstr) == round(fnum, precision)


def compare_value(str_value: str, value) -> bool:
    """
    compare if str value and value area equal

    Args:
        str_value (str): value as str
        value (any): value to compare to

    Returns:
        bool: equal compare result
    """
    return (isinstance(value, float) and compare_fstr_float(str_value, value)
            or isinstance(value, bool) and str_value == str(value)
            or isinstance(value, int) and str_value == str(value)
            or isinstance(value, str) and str_value[1: -1] == value)


def str_dict_to_dict(obj: str) -> dict:
    """
    converts str in dict format to an actual dict with values as str

    Args:
        obj (str): str to convert

    Returns:
        dict: converted string with str as values
    """
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
            data[last_key] += ", %s" % split[0]
    return data


def compare_op_dict(op1_props: dict, op2_props: dict) -> bool:
    """
    compares two operator dict
    (op_dict can be created with operator_to_dict)

    Args:
        op1_props (dict): first operator dict
        op2_props (dict): second operator dict

    Returns:
        bool: equal compare result
    """
    # REFACTOR indentation
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
                # switch column and row
                value = [[value[i][j] for i in range(len(value[0]))] for j in range(len(value))]
                str_vectors = str_value.replace("(", "").split(")")
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


def merge_report_tracked(reports: list, tracked_actions: list) -> list[tuple]:
    """
    merge reports together with the tracked actions to provide better data for macro creation

    Args:
        reports (list): reports from Blender
        tracked_actions (list): tracked actions from scene

    Returns:
        list[tuple]:
            list with elements format (Type, Register, Undo, type, name, value[s])
            Type: 0 - Context, 1 Operator
    """
    # REFACTOR indentation
    # REFACTOR rework this function because it's a mess
    # create numpy.array for efficient access
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
    logger.info("reports: %s\ntracked:%s" % (reports, tracked_actions))
    while continue_report or continue_tracked:
        if continue_report:
            report = reports[report_i]
        if continue_tracked:
            tracked = tracked_actions[tracked_i]
        if report.startswith('bpy.ops.'):
            if last_i != report_i:
                # clean up reports first before merge with tracked actions!!!
                ops_type, ops_name, ops_values = split_operator_report(report)
            last_i = report_i
            if tracked[2] == "%s_OT_%s" % (ops_type.upper(), ops_name):
                if compare_op_dict(ops_values, tracked[3]):
                    if continue_report:
                        data.append((1, True, tracked[1], ops_type, ops_name, ops_values))
                    tracked_i += 1
                elif not continue_report:  # no reports left use latest report
                    data.append((1, True, 'UNDO' in getattr(getattr(
                        bpy.ops, ops_type), ops_name).bl_options, ops_type, ops_name, ops_values))
                    break
                report_i += 1
            else:
                if len_tracked <= tracked_i:  # no tracked left but report operator exists
                    data.append(
                        (
                            1,
                            True,
                            'UNDO' in getattr(getattr(bpy.ops, ops_type), ops_name).bl_options,
                            ops_type,
                            ops_name,
                            ops_values
                        )
                    )
                    report_i += 1
                tracked_i += 1
        elif report.startswith('bpy.context.'):
            if continue_report:
                source_path, attribute, value = split_context_report(
                    report)
                undo = not (any(x in source_path for x in ("screen", "area", "space_data"))
                            or all(x in attribute for x in ("active", "index")))  # exclude index set of UIList
                data.append((0, True, undo, source_path, attribute, value))
                report_i += 1
            if tracked[2] == 'CONTEXT':
                tracked[3] -= 1
                if tracked[3] == 0:
                    tracked_i += 1
            elif not continue_report or not tracked[0]:
                tracked_i += 1
        else:
            report_i += 1
            if not continue_report:
                break

        continue_report = len_report > report_i
        continue_tracked = len_tracked > tracked_i
    return data


def add_report_as_macro(
        context: bpy.types.Context,
        ActRec_pref: bpy.types.AddonPreferences,
        action: 'AR_local_action',
        report: str,
        error_reports: list,
        ui_type: str = ""):
    """
    add a report as a new macro to the given action

    Args:
        context (bpy.types.Context): active blender context
        ActRec_pref (bpy.types.AddonPreferences): preferences of this addon
        action (AR_local_action): action to add macro to
        report (str): report to add as macro
        error_reports (list): error_report to add report if it doesn't match the pattern
        ui_type (str, optional): ui_type where macro get called. Defaults to "".
    """
    if report.startswith(("bpy.context.", "bpy.ops.")):
        macro = action.macros.add()
        label = shared.get_name_of_command(context, report)
        macro.id
        macro.label = ActRec_pref.last_macro_label = label if label else report
        macro.command = ActRec_pref.last_macro_command = report
        macro.ui_type = ui_type
        action.active_macro_index = -1
    else:
        error_reports.append(report)


def split_context_report(report: str) -> Tuple[list, str, str]:
    """
    split apart a context report in 3 types (source_path, attribute, value)

    Args:
        report (str): report to split apart

    Returns:
        Tuple[list, str, str]: format (source_path, attribute, value)
    """
    base, value = report.split(" = ")
    split = base.replace("bpy.context.", "").split(".")
    return split[:-1], split[-1], value  # source_path, attribute, value


def get_id_object(context: bpy.types.Context, source_path: list, attribute: str) -> str:
    """
    get the id property as Blender object from the given source path and attribute

    Args:
        context (bpy.types.Context): active blender context
        source_path (list): path from the context (excluded) to the attribute (excluded)
        attribute (str): attribute for the source path

    Returns:
        str: Blender id property
    """
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


def trace_object(base: 'blender_object', path: list) -> 'blender_object':
    """
    trace the base with the given path to a Blender object

    Args:
        base (blender_object): object to trace from
        path (list): path to trace

    Returns:
        blender_object: traced object
    """
    for x in path:
        base = getattr(base, x)
    return base


def get_copy_of_object(data: dict, obj: 'blender_object', attribute: str, depth=5) -> dict:
    """
    makes a copy of a given blender object

    Args:
        data (dict): data to write part of the copy to
        obj (blender_object): object to work on
        attribute (str): attribute of the object
        depth (int, optional): depth where to break the copy of the object. Defaults to 5.

    Returns:
        dict: copied blender object
    """
    # REFACTOR indentation
    if depth and obj:
        if hasattr(obj, attribute):
            return {attribute: getattr(obj, attribute)}
        if hasattr(obj, 'bl_rna'):
            for prop in obj.bl_rna.properties[1:]:
                if prop.type == 'COLLECTION' or prop.type == 'POINTER':
                    sub_obj = getattr(obj, prop.identifier)
                    if obj != sub_obj:
                        res = get_copy_of_object({}, sub_obj, attribute, depth - 1)
                        if res != {}:
                            data[prop.identifier] = res
    return data


def create_object_copy(context: bpy.types.Context, source_path: list, attribute: str) -> dict:
    """
    creates a copy of a given object based on it's source path and attribute from the context

    Args:
        context (bpy.types.Context): active blender context
        source_path (list): path from the context (excluded) to the attribute (excluded)
        attribute (str): attribute for the source path

    Returns:
        dict: copied object data
    """
    data = {}
    id_object = get_id_object(context, source_path, attribute)
    res = get_copy_of_object(data, id_object, attribute)
    if res and not isinstance(res, dict):
        data[attribute] = res
    return data


def compare_object_report(obj: 'blender_object', copy_dict: dict, source_path: list, attribute: str, value
                          ) -> Union[tuple, None]:
    """
    compare the copy dict values against the given obj

    Args:
        obj (blender_object): object to compare against
        copy_dict (dict): copy of an blender object
        source_path (list): path to trace for deeper compare,
            path from the context (excluded) to the attribute (excluded)
        attribute (str): attribute to compare
        value (any): value the return with

    Returns:
        Union[tuple, None]:
            tuple: format (object class, source_path as str, attribute, value)
            None: object couldn't be compared
    """
    # REFACTOR indentation
    if hasattr(obj, attribute) and getattr(obj, attribute) != copy_dict[attribute]:
        return (obj.__class__, ".".join(source_path), attribute, value)
    for key in copy_dict:
        if hasattr(obj, key):
            if isinstance(copy_dict[key], dict):
                res = compare_object_report(getattr(obj, key), copy_dict[key], [*source_path, key], attribute, value)
                if res:
                    return res
    return


def improve_context_report(context: bpy.types.Context, copy_dict: dict, source_path: list, attribute: str, value: str
                           ) -> str:
    """
    improve the context report(<source_path>.<attribute>) with the active context to get accurate results

    Args:
        context (bpy.types.Context): active blender context
        copy_dict (dict): copy of an blender object
        source_path (list): path from the context (excluded) to the attribute (excluded)
        attribute (str): attribute for the source path
        value (str): value to assign to the attribute

    Returns:
        str: format bpy.context.<source_path>.<attribute> = <value>
    """
    id_object = get_id_object(context, source_path, attribute)
    if hasattr(id_object, attribute):
        object_class = id_object.__class__
        res = [".".join(source_path), attribute, value]
    else:
        res = compare_object_report(id_object, copy_dict, source_path, attribute, value)
        if res:
            object_class, *res = res
        else:
            object_class, *res = id_object.__class__, ".".join(source_path), attribute, value
    for attr in context.__dir__():
        # exclude Buttons Context https://docs.blender.org/api/current/bpy.context.html#buttons-context
        if (attr not in
                set([
                    "button_pointer", "id", "texture_slot", "mesh", "armature", "lattice", "curve", "meta_ball",
                    "speaker", "lightprobe", "camera", "material_slot", "texture", "texture_user",
                    "texture_user_property", "bone", "edit_bone", "pose_bone",
                ]) and isinstance(getattr(bpy.context, attr), object_class)):
            res[0] = attr
            break
    return "bpy.context.%s.%s = %s" % tuple(res)


def split_operator_report(operator_str: str) -> Tuple[str, str, dict]:
    """
    split apart the given operator string to ops_type, ops_name, ops_values

    Args:
        operator_str (str): str starting with "bpy.ops."

    Returns:
        Tuple[str, str, dict]: format (ops_type, ops_name, ops_values)
    """
    # REFACTOR indentation
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
                ops_values[key] += ", %s" % (split[0])
    return ops_type, ops_name, ops_values


def dict_to_kwarg_str(value_dict: dict) -> str:
    """
    converts a dict to a string with the format <key1>=<value1>, <key2>=<value2>, ...
    only first level of dict is converted

    Args:
        value_dict (dict): dict to convert

    Returns:
        str: format "<key1>=<value1>, <key2>=<value2>, ..."
    """
    property_str_list = []
    for key, value in value_dict.items():
        if isinstance(value, str):
            value = "\'%s\'" % value
        property_str_list.append(f"{key}={value}")
    return ", ".join(property_str_list)


def evaluate_operator(ops_type: str, ops_name: str, ops_values: dict) -> bool:
    """
    evaluate weather a operator need to be improved or not
    bpy.ops.<type>.<name>(values)

    Args:
        ops_type (str): type of the operator
        ops_name (str): name of the operator
        ops_values (dict): values of the operator

    Returns:
        bool: need to be improved
    """
    if ops_type == "outliner":
        if ops_name in {"item_activate", "item_rename"}:
            return False
        elif ops_name in {"collection_drop"}:
            return True


def improve_operator_report(
        context: bpy.types.Context, ops_type: str, ops_name: str, ops_values: dict, ops_evaluation: bool) -> str:
    """
    improve the operator if needed
    bpy.ops.<type>.<name>(values)

    Args:
        context (bpy.types.Context): active blender context
        ops_type (str): type of the operator
        ops_name (str): name of the operator
        ops_values (dict): values of the operator
        ops_evaluation (bool): need improvement

    Returns:
        str: format bpy.ops.<type>.<name>(values)
    """
    # REFACTOR indentation, use dict
    if ops_evaluation:
        if ops_type == "outliner":
            if ops_name == "collection_drop":
                return "bpy.ops.ar.helper_object_to_collection()"
    return "bpy.ops.%s.%s(%s)" % (ops_type, ops_name, dict_to_kwarg_str(ops_values))

# endregion
