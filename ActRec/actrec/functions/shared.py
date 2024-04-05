# region Imports
# external modules
from typing import Optional, Union
from contextlib import suppress
from collections import defaultdict
import json
import os
import sys
import numpy
import functools
import subprocess
import traceback
from typing import TYPE_CHECKING
from mathutils import Vector, Matrix, Color, Euler, Quaternion

# blender modules
import bpy
import bl_math
from bpy.app.handlers import persistent
from bpy.types import PointerProperty, Property, CollectionProperty, Context, AddonPreferences, PropertyGroup

# relative imports
from ..log import logger
from .. import shared_data
if TYPE_CHECKING:
    from ..preferences import AR_preferences
    from ..properties.shared import AR_action
    from ..operators.macros import Font_analysis
else:
    AR_preferences = AddonPreferences
    AR_action = PropertyGroup
    Font_analysis = object
# endregion

__module__ = __package__.split(".")[0]

# region functions


def check_for_duplicates(check_list: list, name: str, num: int = 1) -> str:
    """
    Check for the same name in check_list and append .001, .002 etc. if found

    Args:
        check_list (list): list to check against
        name (str): name to check
        num (int, optional): starting number to append. Defaults to 1.

    Returns:
        str: name with expansion if necessary
    """
    split = name.split(".")
    base_name = name
    if split[-1].isnumeric():
        base_name = ".".join(split[:-1])
    while name in check_list:
        name = "{0}.{1:03d}".format(base_name, num)
        num += 1
    return name


def get_pointer_property_as_dict(property: PointerProperty, exclude: list, depth: int) -> dict:
    """
    converts a Blender PointerProperty to a python dict
    (used internal for property_to_python, pls use property_to_python to convert any Blender Property)

    Args:
        property (PointerProperty): Blender Property to convert
        exclude (list):
            property values to exclude, to exclude deeper values use form <value>.<sub-value>
            E.g. for AR_global_actions "actions.name" to excluded the names from the actions
            the <value>.<sub-value> can only be used if the value is of type CollectionProperty or PointerProperty
        depth (int): depth to extract the value, needed because some Properties have recursive definition

    Returns:
        dict: python dict based on property
    """
    data = {}  # PointerProperty
    main_exclude = []
    sub_exclude = defaultdict(list)
    for x in exclude:
        prop = x.split(".")
        if len(prop) > 1:
            sub_exclude[prop[0]].append(".".join(prop[1:]))
        else:
            main_exclude.append(prop[0])
    main_exclude = set(main_exclude)
    for attr in property.bl_rna.properties[1:]:  # exclude rna_type
        identifier = attr.identifier
        if identifier in main_exclude:
            continue
        data[identifier] = property_to_python(
            getattr(property, identifier),
            sub_exclude.get(identifier, []),
            depth - 1
        )
    return data


def property_to_python(property: Property, exclude: list = [], depth: int = 5) -> Union[list, dict, str]:
    """
    converts any Blender Property to a python object, only needed for Property with complex structure

    Args:
        property (Property): Blender Property to convert
        exclude (list, optional):
            property values to exclude, to exclude deeper values use form <value>.<sub-value>
            E.g. for AR_global_actions "actions.name" to excluded the names from the actions
            the <value>.<sub-value> can only be used if the value is of type CollectionProperty or PointerProperty.
            Defaults to [].
        depth (int, optional):
            depth to extract the value, needed because some Properties have recursive definition.
            Defaults to 5.

    Returns:
        Union[list, dict, str]: converts Collection, Arrays to lists and PointerProperty to dict
    """
    # CollectionProperty are a list of PointerProperties
    if depth <= 0:
        return "max depth"
    if isinstance(property, set):  # Catch EnumProperty with EnumFlag
        return list(property)
    if not hasattr(property, 'id_data'):
        return property

    id_object = property.id_data

    # exclude conversions of same property
    if property == id_object:
        return property

    class_name = property.__class__.__name__
    if class_name == 'bpy_prop_collection_idprop':
        # CollectionProperty
        return [property_to_python(item, exclude, depth) for item in property]
    if class_name == 'bpy_prop_collection':
        # CollectionProperty
        if hasattr(property, "bl_rna"):
            data = get_pointer_property_as_dict(property, exclude, depth)
            data["items"] = [
                property_to_python(item, exclude, depth) for item in property
            ]
            return data
        else:
            return [property_to_python(item, exclude, depth) for item in property]
    if class_name == 'bpy_prop_array':
        # ArrayProperty
        return [property_to_python(item, exclude, depth) for item in property]
    # PointerProperty
    return get_pointer_property_as_dict(property, exclude, depth)


def apply_data_to_item(property: Property, data, key="") -> None:
    """
    apply given python data to a property,
    used to convert python data (from property_to_python) to Blender Property.
    - list to CollectionsProperty or ArrayProperty (add new elements to the collection)
    - dict to PointerProperty
    - single data (like int, string, etc.) with a given key

    Args:
        property (Property): Blender Property to apply the data to
        data (any): data to apply
        key (str, optional): used to apply a single value of a given Blender Property dynamic. Defaults to "".
    """
    if isinstance(data, list):
        item = property
        if key:
            item = getattr(property, key)
            if isinstance(item, set):  # EnumProperty with EnumFlag
                setattr(property, key, set(data))
                return
            elif isinstance(item, bpy.types.bpy_prop_array):  # ArrayProperty
                setattr(property, key, data)
                return
        # EnumProperty with EnumFlag but no key
        if isinstance(item, (set, bpy.types.bpy_prop_array)):
            return
        for element in data:
            apply_data_to_item(item.add(), element)
    elif isinstance(data, dict):
        if key:
            property = getattr(property, key)
        for key, value in data.items():
            apply_data_to_item(property, value, key)
    elif hasattr(property, key):
        with suppress(AttributeError):  # catch Exception from read-only property
            setattr(property, key, data)


def add_data_to_collection(collection: CollectionProperty, data: dict) -> None:
    """
    creates new collection element and applies the data to it

    Args:
        collection (CollectionProperty): collection to apply to
        data (dict): data to apply
    """
    new_item = collection.add()
    apply_data_to_item(new_item, data)


def insert_to_collection(collection: CollectionProperty, index: int, data: dict) -> None:
    """
    inset a new element inside a collection and apply the given data to it
    if the index is out of bounds the element is insert at the end of the collection

    Args:
        collection (CollectionProperty): collection to apply to
        index (int): index where to insert
        data (dict): data to apply
    """

    add_data_to_collection(collection, data)
    if index < len(collection):
        collection.move(len(collection) - 1, index)


def swap_collection_items(collection: CollectionProperty, index_1: int, index_2: int) -> None:
    """
    swaps to collection items
    if the index is set to the last element of the collection

    Args:
        collection (CollectionProperty): collection to execute on
        index_1 (int): first index to swap with second
        index_2 (int): second index to swap with first
    """
    collection_length = len(collection)
    if index_1 >= collection_length:
        index_1 = collection_length - 1
    if index_2 >= collection_length:
        index_2 = collection_length - 1
    if index_1 == index_2:
        return
    if index_1 < index_2:
        index_1, index_2 = index_2, index_1
    collection.move(index_1, index_2)
    collection.move(index_2 + 1, index_1)


def enum_list_id_to_name_dict(enum_list: list) -> dict:
    """
    converts an enum list, used in EnumProperties,
    to a dict with the identifier as key and the corresponding name as value

    Args:
        enum_list (list): enum list to convert

    Returns:
        dict: identifier to name
    """
    return {identifier: name for identifier, name, *tail in enum_list}


def enum_items_to_enum_prop_list(items: CollectionProperty, value_offset: int = 0) -> list[tuple]:
    """
    converts enum items to an enum property list

    Args:
        items (enum_items): enum items to convert
        value_offset (int): offset to apply to the value of each element

    Returns:
        list[tuple]: list with elements of format (identifier, name, description, icon, value)
    """
    return [(item.identifier, item.name, item.description, item.icon, item.value + value_offset) for item in items]


def get_categorized_view_3d_modes(items: CollectionProperty, value_offset: int = 0) -> list[tuple]:
    """
    converts view_3d items to an enum property list with categories for General, Grease Pencil, Curves

    Args:
        items (enum_items): enum items to convert
        value_offset (int): offset to apply to the value of each element

    Returns:
        list[tuple]: list with elements of format (identifier, name, description, icon, value)
    """
    general = [("", "General", "")]
    grease_pencil = [("", "Grease Pencil", "")]
    curves = [("", "Curves", "")]
    modes = enum_items_to_enum_prop_list(items, value_offset)
    for mode in modes:
        if "GPENCIL" in mode[0]:
            grease_pencil.append(mode)
        elif "CURVES" in mode[0]:
            curves.append(mode)
        else:
            general.append(mode)
    return general + grease_pencil + curves


def get_name_of_command(context: Context, command: str) -> Optional[str]:
    """
    get the name of a given command

    Args:
        context (Context): active blender context
        command (str): Blender command to get name from

    Returns:
        Optional[str]: name or none if name not found
    """
    if command.startswith("bpy.ops."):
        try:
            return eval("%s.get_rna_type().name" % command.split("(")[0])
        except (KeyError):
            return None

    if not command.startswith("bpy.context."):
        return None

    split = command.split(' = ')
    if len(split) <= 1:
        return ".".join(split[0].split('.')[-2:])

    *path, prop = split[0].replace("bpy.context.", "").split(".")
    obj = context
    if obj:
        for x in path:
            if not hasattr(obj, x):
                break
            obj = getattr(obj, x)
        else:
            if obj:
                props = obj.bl_rna.properties
                if prop in props:
                    prop = props[prop].name

    value = split[1]
    if value.startswith("bpy.data."):
        value = value.split("[")[-1].replace("]", "")[1:-1]

    return "%s = %s" % (prop, value)


def extract_properties(properties: str) -> list:
    """
    extracts properties from a given string in the format "prop1, prop2, ..."

    Args:
        properties (str): format "prop1, prop2, ..."

    Returns:
        list: list of properties
    """
    properties = properties.split(",")
    new_props = []
    prop_str = ''
    for prop in properties:
        prop = prop.split('=')
        if prop[0].strip().isidentifier() and len(prop) > 1:
            new_props.append(prop_str.strip())
            prop_str = ''
            prop_str += "=".join(prop)
        else:
            prop_str += ",%s" % prop[0]
    new_props.append(prop_str.strip())
    return new_props[1:]


def update_command(command: str) -> Union[str, bool]:
    """
    update a command to the current Blender version,
    by getting the command and only passe on the existing properties
    if the command no longer exists False is returned

    Args:
        command (str): blender command to update

    Returns:
        Union[str, bool, None]: update string, return False if command doesn't exists anymore
    """
    if not command.startswith("bpy.ops."):
        return False
    command, values = command.split("(", 1)
    # values [:-1] remove closing bracket
    values = extract_properties(values[:-1])
    for i in range(len(values)):
        values[i] = values[i].split("=")
    try:
        props = eval("%s.get_rna_type().properties[1:]" % command)
    except (KeyError):
        return False
    inputs = []
    for prop in props:
        for value in values:
            if value[0] != prop.identifier:
                continue
            inputs.append("%s=%s" % (value[0], value[1]))
            values.remove(value)
            break
    return "%s(%s)" % (command, ", ".join(inputs))


def run_queued_macros(context_copy: dict, action_type: str, action_id: str, start: int) -> None:
    """
    runs macros from a given index of a specific action

    Args:
        context_copy (dict): copy of the active context (bpy.context.copy())
        action_type (str): "global_actions" or "local_actions"
        action_id (str): id of the action with the macros to execute
        start (int): macro to start with in the macro collection
    """
    context = bpy.context
    if context_copy is None:
        temp_override = context.temp_override()
    else:
        temp_override = context.temp_override(**context_copy)
    with temp_override:
        ActRec_pref = context.preferences.addons[__module__].preferences
        action = getattr(ActRec_pref, action_type)[action_id]
        play(context, action.macros, action, action_type, start)


def execute_individually(context: Context, command: str) -> None:
    """
    execute the given command on each selected object individually

    Args:
        context (Context): active blender context
        command (str): command to execute
    """
    old_selected_objects = context.selected_objects[:]
    for object in old_selected_objects:
        object.select_set(False)

    for object in old_selected_objects:
        object.select_set(True)
        context.view_layer.objects.active = object
        exec(command)
        with suppress(ReferenceError):
            object.select_set(False)

    for object in old_selected_objects:
        with suppress(ReferenceError):
            object.select_set(True)


# table to point from the end-loop macro (=key) to the start-loop macro (=value)
loop_table = {}

# table the holds the iterator (=value) of a loop accessed by the start-loop macro (=key)
loop_iterator = {}

# table the holds the loop size excluding start-loop macro but including end-loop macro (=value)
# accessed by the start-loop macro (=key)
loop_size = {}


def play(
        context: Context,
        macros: CollectionProperty,
        action: AR_action,
        action_type: str,
        start_index: int = 0) -> Union[Exception, str, None]:
    """
    execute all given macros in the given context.
    action, action_type are used to run the macros of the given action with delay to the execution

    Args:
        context (Context): active blender context
        macros (CollectionProperty): macros to execute
        action (AR_action): action to track
        action_type (str): action type of the given action
        start_index (int): the index of the macro where to start

    Returns:
        Exception, str: error
    """
    action.is_playing = True
    macros = [macro for macro in macros if macro.active]

    # non-realtime events, execute before macros get executed
    for i, macro in enumerate(macros[start_index:]):
        split = macro.command.split(":")
        if split[0] != 'ar.event':
            continue
        data = json.loads(":".join(split[1:]))
        if data['Type'] == 'Render Complete':
            # SKip only render complete macro
            if len(macros) <= i + 1:
                action.is_playing = False
                return "The 'Render Complete' macro was skipped because no additional macros follow!"
            shared_data.render_complete_macros.append(
                (action_type, action.id, macros[i + 1].id))
            break
        elif data['Type'] == 'Loop':
            loop_count = 1
            for j, process_macro in enumerate(macros[i + 1:], 1):
                if not process_macro.active:
                    continue
                split = process_macro.command.split(":")
                if split[0] != 'ar.event':
                    continue
                process_data = json.loads(":".join(split[1:]))
                loop_count += 2 * \
                    (process_data['Type'] == 'Loop') - \
                    (process_data['Type'] == 'EndLoop')  # 1 or -1
                if loop_count == 0:
                    loop_table[process_macro.id] = macro.id
                    loop_size[macro.id] = j
                    loop_iterator[macro.id] = 0
                    if data['StatementType'] == 'count':
                        # DEPRECATED used to support old count loop macros
                        loop_iterator[macro.id] = data["Startnumber"]
                    break

    base_area = context.area

    i = start_index
    while i < len(macros):
        macro = macros[i]
        split = macro.command.split(":")
        if split[0] == 'ar.event':  # Handle Ar Events
            data: dict = json.loads(":".join(split[1:]))
            if data['Type'] in {'Render Complete'}:
                return
            if data['Type'] == 'Timer':
                bpy.app.timers.register(
                    functools.partial(
                        run_queued_macros,
                        context.copy(),
                        action_type,
                        action.id,
                        i + 1
                    ),
                    first_interval=data['Time']
                )
                return
            if data['Type'] == 'Loop':
                # Skip because it is not a complete loop
                if macro.id not in loop_iterator:
                    i += 1
                    continue

                if data['StatementType'] == 'python':
                    try:
                        if eval(data["PyStatement"]):
                            i += 1
                        else:
                            i += loop_size[macro.id] + 1
                    except Exception as err:
                        logger.error(err)
                        action.alert = macro.alert = True
                        action.is_playing = False
                        return err
                elif data['StatementType'] == 'count':
                    # DEPRECATED used to support old count loop macros
                    if loop_iterator[macro.id] < data["Endnumber"]:
                        loop_iterator[macro.id] += data["Stepnumber"]
                        i += 1
                    else:
                        i += loop_size[macro.id] + 1
                else:
                    if loop_iterator[macro.id] < data["RepeatCount"]:
                        loop_iterator[macro.id] += 1
                        i += 1
                    else:
                        i += loop_size[macro.id] + 1
                continue
            elif data['Type'] == 'Select Object':
                selected_objects = context.selected_objects

                if not data.get('KeepSelection', False):
                    for object in selected_objects:
                        object.select_set(False)
                    selected_objects.clear()

                for object_name in data.get('Objects', []):
                    if object := bpy.data.objects.get(object_name):
                        object.select_set(True)
                        selected_objects.append(object)

                if data.get('Object', "") == "":
                    i += 1
                    continue

                objects = context.view_layer.objects
                main_object = bpy.data.objects.get(data['Object'])
                if main_object is None or main_object not in objects.values():
                    action.alert = macro.alert = True
                    action.is_playing = False
                    return "%s Object doesn't exist in the active view layer" % data['Object']

                objects.active = main_object
                main_object.select_set(True)
                selected_objects.append(main_object)
                i += 1
                continue
            elif data['Type'] == 'Run Script':
                text = bpy.data.texts.new(macro.id)
                text.clear()
                text.write(data['ScriptText'])
                try:
                    text.as_module()
                except Exception:
                    error = traceback.format_exception(*sys.exc_info())
                    # corrects the filename of the exception to the text name, otherwise "<string>"
                    error_split = error[3].replace('"<string>"', '').split(',')
                    error[3] = '%s "%s",%s' % (
                        error_split[0], text.name, error_split[1])
                    # removes exec(self.as_string(), mod.__dict__) in bpy_types.py
                    error.pop(2)
                    error.pop(1)  # removes text.as_module()
                    error = "".join(error)
                    logger.error("%s; command: %s" % (error, data))
                    action.alert = macro.alert = True
                    return error
                bpy.data.texts.remove(text)
                i += 1
                continue
            elif data['Type'] == 'EndLoop':
                start_id = loop_table[macro.id]
                i -= loop_size[start_id]
                continue

        try:
            command = macro.command
            if (command.startswith("bpy.ops.ar.local_play")
                    and set(extract_properties(command.split("(")[1][: -1])) == {"id=\"\"", "index=-1"}):
                err = "Don't run Local Play with default properties, this may cause recursion"
                logger.error(err)
                action.alert = macro.alert = True
                action.is_playing = False
                return err

            if command.startswith("bpy.ops."):
                split = command.split("(")
                command = "%s(\"%s\", %s" % (
                    split[0],
                    macro.operator_execution_context,
                    "(".join(split[1:]))
            elif command.startswith("bpy.context."):
                command = command.replace("bpy.context.", "context.")

            temp_window = context.window
            temp_screen = context.screen
            temp_area = context.area
            temp_region = context.region
            area_type = None
            if temp_area and macro.ui_type and temp_area.ui_type != macro.ui_type:
                windows = list(context.window_manager.windows)
                windows.reverse()
                for window in windows:
                    if window.screen.areas[0].ui_type == macro.ui_type:
                        temp_window = window
                        temp_screen = temp_window.screen
                        temp_area = temp_screen.areas[0]
                        break
                else:
                    area_type = temp_area.ui_type
                    temp_area.ui_type = macro.ui_type
            if temp_area:
                # mostly "WINDOW" is at the end of the list
                for region in reversed(temp_area.regions):
                    if region.type != "WINDOW":
                        continue
                    temp_region = region

            # Note: region need to be set when override area for temp_override
            # for more detail see https://projects.blender.org/blender/blender/issues/106373
            with context.temp_override(
                    window=temp_window,
                    screen=temp_screen,
                    area=temp_area,
                    region=temp_region):
                if action.execution_mode == "GROUP":
                    exec(command)
                else:
                    execute_individually(context, command)

            if temp_area and area_type:
                temp_area.ui_type = area_type

            if bpy.context and bpy.context.area:
                bpy.context.area.tag_redraw()
            i += 1

        except Exception as err:
            logger.error("%s; command: %s" % (err, command))
            action.alert = macro.alert = True
            if base_area and area_type:
                base_area.ui_type = area_type
            action.is_playing = False
            return err
    else:
        action.is_playing = False


@ persistent
def execute_render_complete(dummy=None) -> None:
    # https://docs.blender.org/api/current/bpy.app.handlers.html
    """
    execute macros, which are called after the event macro "Render Complete"
    use bpy.app.handlers and therefore uses a dummy variable for the scene object

    Args:
        dummy (bpy.types.Scene, optional): unused. Defaults to None.
    """
    context = bpy.context
    ActRec_pref = get_preferences(context)
    while len(shared_data.render_complete_macros):
        action_type, action_id, start_id = shared_data.render_complete_macros.pop(0)
        action = getattr(ActRec_pref, action_type)[action_id]
        if (start_index := action.macros.find(start_id)) < 0:
            continue

        bpy.app.timers.register(
            functools.partial(
                run_queued_macros,
                None,
                action_type,
                action_id,
                start_index
            ),
            first_interval=0.1
        )


def get_font_path() -> str:
    """
    get the font path of the active font in Blender

    Returns:
        str: path to the font
    """
    if bpy.context.preferences.view.font_path_ui == '':
        version = bpy.app.version
        font_directory = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(bpy.__file__)))),
            "datafiles",
            "fonts"
        )
        if version >= (4, 0, 0):
            return os.path.join(font_directory, "Inter.woff2")
        if version >= (3, 4, 0):
            return os.path.join(font_directory, "DejaVuSans.woff2")
        return os.path.join(font_directory, "droidsans.ttf")
    else:
        return bpy.context.preferences.view.font_path_ui


def split_and_keep(sep: str, text: str) -> list[str]:
    """
    split's the given text with the separator but doesn't delete the separator from the text

    Args:
        sep (str): separator
        text (str): text to split

    Returns:
        list[str]: list of splitted str
    """
    # creates str, which isn't contained inside the text to uses as split separator
    p = chr(ord(max(text)) + 1)
    for s in sep:
        text = text.replace(s, s + p)
    return text.split(p)


def get_attribute(obj: object, name: str) -> object:
    """
    Call getattr to get attribute from an object but it can reach attributes of attributes
    E.g.: x.y.z with the input get_attribute(x, 'y.z')

    Args:
        obj (object): object to get attributes from
        name (str): attribute of this object. Can be of format 'attribute.subattribute.subsub.' etc.

    Returns:
        Any: attribute of the object
    """
    for arg_name in name.split("."):
        obj = getattr(obj, arg_name)
    return obj


def get_attribute_default(obj: object, name: str, default: None) -> object | None:
    """
    Call getattr to get attribute from an object but it can reach attributes of attributes
    E.g.: x.y.z with the input get_attribute(x, 'y.z')

    Args:
        obj (object): object to get attributes from
        name (str): attribute of this object. Can be of format 'attribute.subattribute.subsub.' etc.
        default (None): returned when one attribute doesn't exist

    Returns:
        Any: attribute of the object
    """
    for arg_name in name.split("."):
        obj = getattr(obj, arg_name, default)
    return obj


def text_to_lines(context: Context, text: str, font: Font_analysis, limit: int, endcharacter: str = " ,") -> list[str]:
    """
    converts a one line text to multiple lines saved as a list
    (needed because Blender doesn't have text boxes)

    Args:
        context (Context): active blender context
        text (str): text to convert
        font (Font_analysis): loaded font to work on
        limit (int): maximum size of one line
        endcharacter (str, optional): preferred characters to split the text apart. Defaults to " ,".

    Returns:
        list[str]: multiline text
    """
    if text == "" or not font.use_dynamic_text:
        return [text]
    characters_width = font.get_width_of_text(context, text)
    possible_breaks = split_and_keep(endcharacter, text)
    lines = [""]
    start = 0
    for psb in possible_breaks:
        line_length = len(lines[-1])
        total_line_length = start + line_length
        total_length = total_line_length + len(psb)
        width = sum(characters_width[start: total_length])
        if width <= limit:
            lines[-1] += psb
            continue
        if sum(characters_width[total_line_length: total_length]) <= limit:
            lines.append(psb)
            start += line_length + len(psb)
            continue
        start += line_length
        while psb != "":
            i = int(bl_math.clamp(limit / width * len(psb), 0, len(psb)))
            if len(psb) != i:
                if sum(characters_width[start: start + i]) <= limit:
                    while sum(characters_width[start: start + i]) <= limit:
                        i += 1
                    i -= 1
                else:
                    while sum(characters_width[start: start + i]) >= limit:
                        i -= 1
            lines.append(psb[:i])
            psb = psb[i:]
            start += i
            width = sum(characters_width[start: total_length])
    if (lines[0] == ""):
        lines.pop(0)
    return lines


def install_packages(*package_names: list[str]) -> tuple[bool, str]:
    """
    install the listed packages and ask for user permission if needed

    Args:
        package_names list[str]: name of the package

    Returns:
        tuple[bool, str]: (success, installation output)
    """
    try:
        # install package
        output = subprocess.check_output(
            [sys.executable, '-m', 'pip', 'install', *package_names, '--no-color']
        ).decode('utf-8').replace("\r", "")

        # get sys.path from pip after installation to update the current sys.path
        output_paths = subprocess.check_output(
            [sys.executable, '-m', 'site']
        ).decode('utf-8').replace("\r", "")

        # parse the output to get all sys.path paths
        in_path_list = False
        for line in output_paths.splitlines():
            if line.strip() == "sys.path = [":
                in_path_list = True
                continue
            elif not in_path_list:
                continue
            if line.strip() == "]":
                break

            path = line.strip(" \'\",\t").replace("\\\\", "\\")
            if path not in sys.path:
                sys.path.append(path)

        return (True, output)

    except (PermissionError, OSError, subprocess.CalledProcessError) as err:
        logger.error(err)
        return (False, err.output)
    return (False, ":(")


def get_preferences(context: Context) -> AR_preferences:
    """
    get addon preferences of this addon, which are stored in Blender

    Args:
        context (Context): active blender context

    Returns:
        AR_preferences: preferences of this addon
    """
    return context.preferences.addons[__module__].preferences

# endregion
