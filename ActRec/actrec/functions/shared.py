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
import ensurepip
import subprocess

# blender modules
import bpy
import bl_math
from bpy.app.handlers import persistent

# relative imports
from ..log import logger
from .. import shared_data
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


def get_pointer_property_as_dict(property: bpy.types.PointerProperty, exclude: list, depth: int) -> dict:
    """
    converts a Blender PointerProperty to a python dict
    (used internal for property_to_python, pls use property_to_python to convert any Ble)

    Args:
        property (bpy.types.PointerProperty): Blender Property to convert
        exclude (list):
            property values to exclude, to exclude deeper values use form <value>.<sub-value>
            E.g. for AR_global_actions "actions.name" to excluded the names from the actions
            the <value>.<sub-value> can only be used if the value is of type CollectionProperty or PointerProperty
        depth (int): depth to extract the value, needed because some Properties have recursive definition

    Returns:
        dict: python dict based on property
    """
    # REFACTOR indentation
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
        if identifier not in main_exclude:
            data[identifier] = property_to_python(
                getattr(property, identifier),
                sub_exclude.get(identifier, []),
                depth - 1
            )
    return data


def property_to_python(property: bpy.types.Property, exclude: list = [], depth: int = 5) -> Union[list, dict, str]:
    """
    converts any Blender Property to a python object, only needed for Property with complex structure

    Args:
        property (bpy.types.Property): Blender Property to convert
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
    # REFACTOR indentation
    # CollectionProperty are a list of PointerProperties
    if depth <= 0:
        return "max depth"
    if hasattr(property, 'id_data'):
        id_object = property.id_data

        # exclude conversions of same property
        if property == id_object:
            return property

        class_name = property.__class__.__name__
        if class_name == 'bpy_prop_collection_idprop':
            # CollectionProperty
            return [property_to_python(item, exclude, depth) for item in property]
        elif class_name == 'bpy_prop_collection':
            # CollectionProperty
            if hasattr(property, "bl_rna"):
                data = get_pointer_property_as_dict(property, exclude, depth)
                data["items"] = [property_to_python(item, exclude, depth) for item in property]
                return data
            else:
                return [property_to_python(item, exclude, depth) for item in property]
        elif class_name == 'bpy_prop_array':
            # ArrayProperty
            return [property_to_python(item, exclude, depth) for item in property]
        else:
            # PointerProperty
            return get_pointer_property_as_dict(property, exclude, depth)
    return property


def apply_data_to_item(property: bpy.types.Property, data, key=""):
    """
    apply given python data to a property,
    used to convert python data (from property_to_python) to Blender Property.
    - list to CollectionsProperty or ArrayProperty (add new elements to the collection)
    - dict to PointerProperty
    - single data (like int, string, etc.) with a given key

    Args:
        property (bpy.types.Property): Blender Property to apply the data to
        data (any): data to apply
        key (str, optional): used to apply a single value of a given Blender Property dynamic. Defaults to "".
    """
    if isinstance(data, list):
        for element in data:
            if key:
                subitem = getattr(property, key).add()
            else:
                subitem = property.add()
            apply_data_to_item(subitem, element)
    elif isinstance(data, dict):
        for key, value in data.items():
            apply_data_to_item(property, value, key)
    elif hasattr(property, key):
        with suppress(AttributeError):  # catch Exception from read-only property
            setattr(property, key, data)


def add_data_to_collection(collection: bpy.types.CollectionProperty, data: dict):
    """
    creates new collection element and applies the data to it

    Args:
        collection (bpy.types.CollectionProperty): collection to apply to
        data (dict): data to apply
    """
    new_item = collection.add()
    apply_data_to_item(new_item, data)


def insert_to_collection(collection: bpy.types.CollectionProperty, index: int, data: dict):
    """
    inset a new element inside a collection and apply the given data to it
    if the index is out of bounds the element is insert at the end of the collection

    Args:
        collection (bpy.types.CollectionProperty): collection to apply to
        index (int): index where to insert
        data (dict): data to apply
    """

    add_data_to_collection(collection, data)
    if index < len(collection):
        collection.move(len(collection) - 1, index)


def swap_collection_items(collection: bpy.types.CollectionProperty, index_1: int, index_2: int):
    """
    swaps to collection items
    if the index is set to the last element of the collection

    Args:
        collection (bpy.types.CollectionProperty): collection to execute on
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
        dict: created identifier to name dict
    """
    return {identifier: name for identifier, name, *tail in enum_list}


def enum_items_to_enum_prop_list(items: bpy.types.CollectionProperty) -> list[tuple]:
    """
    converts enum items to an enum property list

    Args:
        items (enum_items): enum items to convert

    Returns:
        list[tuple]: list with elements of format (identifier, name, description, icon, value)
    """
    return [(item.identifier, item.name, item.description, item.icon, item.value) for item in items]


def get_name_of_command(context: bpy.types.Context, command: str) -> Optional[str]:
    """
    get the name of a given command

    Args:
        context (bpy.types.Context): active blender context
        command (str): Blender command to get name from

    Returns:
        Optional[str]: name or none if name not found
    """
    # REFACTOR indentation
    if command.startswith("bpy.ops."):
        try:
            return eval("%s.get_rna_type().name" % command.split("(")[0])
        except (KeyError):
            return None
    elif command.startswith("bpy.context."):
        split = command.split(' = ')
        if len(split) > 1:
            *path, prop = split[0].replace("bpy.context.", "").split(".")
            obj = context
            if obj:
                for x in path:
                    if hasattr(obj, x):
                        obj = getattr(obj, x)
                    else:
                        break
                else:
                    props = obj.bl_rna.properties
                    if prop in props:
                        prop = props[prop].name

            value = split[1]
            if value.startswith("bpy.data."):
                value = value.split("[")[-1].replace("]", "")[1:-1]

            return "%s = %s" % (prop, value)
        else:
            return ".".join(split[0].split('.')[-2:])
    else:
        return None


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
    # REFACTOR indentation
    if command.startswith("bpy.ops."):
        command, values = command.split("(", 1)
        values = extract_properties(values[:-1])  # values [:-1] remove closing bracket
        for i in range(len(values)):
            values[i] = values[i].split("=")
        try:
            props = eval("%s.get_rna_type().properties[1:]" % command)
        except (KeyError):
            return False
        inputs = []
        for prop in props:
            for value in values:
                if value[0] == prop.identifier:
                    inputs.append("%s=%s" % (value[0], value[1]))
                    values.remove(value)
                    break
        return "%s(%s)" % (command, ", ".join(inputs))
    else:
        return False


def run_queued_macros(context_copy: dict, action_type: str, action_id: str, start: int):
    """
    runs macros from a given index of a specific action

    Args:
        context_copy (dict): copy of the active context (bpy.context.copy())
        action_type (str): "global_actions" or "local_actions"
        action_id (str): id of the action with the macros to execute
        start (int): macro to start with in the macro collection
    """
    ActRec_pref = context_copy['preferences'].addons[__module__].preferences
    action = getattr(ActRec_pref, action_type)[action_id]
    play(context_copy, action.macros[start:], action, action_type)


def play(context_copy: dict, macros: bpy.types.CollectionProperty, action: 'AR_action', action_type: str
         ) -> Union[Exception, str]:
    """
    execute all given macros in the given context.
    action, action_type are used to run the macros of the given action with delay to the execution

    Args:
        context_copy (dict): copy of the active context (bpy.context.copy())
        macros (bpy.types.CollectionProperty): macros to execute
        action (AR_action): action to track
        action_type (str): action type of the given action

    Returns:
        Exception, str: error
    """
    # REFACTOR indentation
    macros = [macro for macro in macros if macro.active]

    # non-realtime events, execute before macros get executed
    for i, macro in enumerate(macros):
        split = macro.command.split(":")
        if split[0] == 'ar.event':
            data = json.loads(":".join(split[1:]))
            if data['Type'] == 'Render Init':
                shared_data.render_init_macros.append((action_type, action.id, i + 1))
                return
            elif data['Type'] == 'Render Complet':
                shared_data.render_complete_macros.append((action_type, action.id, i + 1))
                return

    base_window = context_copy['window']
    base_screen = context_copy['screen']
    base_area = context_copy['area']
    base_space_data = context_copy['space_data']

    for i, macro in enumerate(macros):  # realtime events
        split = macro.command.split(":")
        if split[0] == 'ar.event':
            data = json.loads(":".join(split[1:]))
            if data['Type'] == 'Timer':
                bpy.app.timers.register(
                    functools.partial(
                        run_queued_macros,
                        context_copy,
                        action_type,
                        action.id,
                        i + 1
                    ),
                    first_interval=data['Time']
                )
                return
            elif data['Type'] == 'Loop':
                end_index = i + 1
                loop_count = 1
                for j, process_macro in enumerate(macros[i + 1:], i + 1):
                    if process_macro.active:
                        split = process_macro.command.split(":")
                        if split[0] == 'ar.event':  # realtime events
                            process_data = json.loads(":".join(split[1:]))
                            if process_data['Type'] == 'Loop':
                                loop_count += 1
                            elif process_data['Type'] == 'EndLoop':
                                loop_count -= 1
                    if loop_count == 0:
                        end_index = j
                        break
                if loop_count != 0:
                    continue
                loop_macros = macros[i + 1: end_index]

                if data['StatementType'] == 'python':
                    try:
                        while eval(data["PyStatement"]):
                            play(context_copy, loop_macros, action, action_type)
                    except Exception as err:
                        logger.error(err)
                        action.alert = macro.alert = True
                        return err
                else:
                    for k in numpy.arange(data["Startnumber"], data["Endnumber"], data["Stepnumber"]):
                        err = play(context_copy, loop_macros, action, action_type)
                        if err:
                            return err

                return play(context_copy, macros[end_index + 1:], action, action_type)
            elif data['Type'] == 'Select Object':
                obj = bpy.data.objects[data['Object']]
                objs = context_copy['view_layer'].objects
                if obj in [o for o in objs]:
                    objs.active = obj
                    for o in context_copy['selected_objects']:
                        o.select_set(False)
                    obj.select_set(True)
                    context_copy['selected_objects'] = [obj]
                else:
                    action.alert = macro.alert = True
                    return "%s Object doesn't exist in the active view layer" % data['Object']
                continue
            elif data['Type'] == 'EndLoop':
                continue
        try:
            command = macro.command
            if (command.startswith("bpy.ops.ar.local_play")
                    and set(extract_properties(command.split("(")[1][: -1])) == {"id=\"\"", "index=-1"}):
                err = "Don't run Local Play with default properties, this can leads to a recursion"
                logger.error(err)
                action.alert = macro.alert = True
                return err

            area = context_copy['area']
            if area:
                area_type = area.ui_type
                if macro.ui_type:
                    windows = list(context_copy['window_manager'].windows)
                    windows.reverse()
                    for window in windows:
                        if window.screen.areas[0].ui_type == macro.ui_type:
                            context_copy['window'] = window
                            context_copy['screen'] = copy_screen = window.screen
                            context_copy['area'] = copy_area = copy_screen.areas[0]
                            context_copy['space_data'] = copy_area.spaces[0]
                            break
                    else:
                        area.ui_type = macro.ui_type
            if command.startswith("bpy.ops."):
                split = command.split("(")
                command = "%s(context_copy, %s" % (
                    split[0], "(".join(split[1:]))
            elif command.startswith("bpy.context."):
                split = command.replace("bpy.context.", "").split(".")
                command = "context_copy['%s'].%s" % (
                    split[0], ".".join(split[1:]))

            exec(command)

            if area and macro.ui_type:
                context_copy['window'] = base_window
                context_copy['screen'] = base_screen
                context_copy['area'] = base_area
                context_copy['space_data'] = base_space_data
                area.ui_type = area_type

            if bpy.context:
                context_copy = bpy.context.copy()

        except Exception as err:
            logger.error("%s; command: %s" % (err, command))
            action.alert = macro.alert = True
            if base_area:
                base_area.ui_type = area_type
            return err


@persistent
def execute_render_init(dummy: bpy.types.Scene = None):
    # https://docs.blender.org/api/current/bpy.app.handlers.html
    """
    execute macros, which are called after the event macro "Render Init"
    use bpy.app.handlers and therefore uses a dummy variable for the scene object

    Args:
        dummy (bpy.types.Scene, optional): unused. Defaults to None.
    """
    context = bpy.context
    ActRec_pref = get_preferences(context)
    for action_type, action_id, start in shared_data.render_init_macros:
        action = getattr(ActRec_pref, action_type)[action_id]
        play(context.copy(), action.macros[start:], action, action_type)


@persistent
def execute_render_complete(dummy=None):
    # https://docs.blender.org/api/current/bpy.app.handlers.html
    """
    execute macros, which are called after the event macro "Render Complete"
    use bpy.app.handlers and therefore uses a dummy variable for the scene object

    Args:
        dummy (bpy.types.Scene, optional): unused. Defaults to None.
    """
    context = bpy.context
    ActRec_pref = get_preferences(context)
    for action_type, action_id, start in shared_data.render_complete_macros:
        action = getattr(ActRec_pref, action_type)[action_id]
        play(context.copy(), action.macros[start:], action, action_type)


def get_font_path() -> str:
    """
    get the font path of the active font in Blender

    Returns:
        str: path to the font
    """
    if bpy.context.preferences.view.font_path_ui == '':
        dirc = "\\".join(sys.executable.split("\\")[:-3])
        if bpy.app.version >= (3, 4, 0):
            return os.path.join(dirc, "datafiles", "fonts", "DejaVuSans.woff2")
        return os.path.join(dirc, "datafiles", "fonts", "droidsans.ttf")
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
    p = chr(ord(max(text)) + 1)  # creates str, which isn't contained inside the text to uses as split separator
    for s in sep:
        text = text.replace(s, s + p)
    return text.split(p)


def text_to_lines(text: str, font: 'Font_analysis', limit: int, endcharacter: str = " ,") -> list[str]:
    """
    converts a one line text to multiple lines saved as a list
    (needed because Blender doesn't have text boxes)

    Args:
        text (str): text to convert
        font (Font_analysis): loaded font to work on
        limit (int): maximum size of one line
        endcharacter (str, optional): preferred characters to split the text apart. Defaults to " ,".

    Returns:
        list[str]: multiline text
    """
    # REFACTOR indentation
    if text == "" or not font.use_dynamic_text:
        return [text]
    characters_width = font.get_width_of_text(text)
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
        else:
            if sum(characters_width[total_line_length: total_length]) > limit:
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
                            i += 1
                    lines.append(psb[:i])
                    psb = psb[i:]
                    start += i
                    width = sum(characters_width[start: total_length])
            else:
                lines.append(psb)
                start += line_length + len(psb)
    if (lines[0] == ""):
        lines.pop(0)
    return lines


def install_package(package_name: str) -> tuple[bool, str]:
    """
    install a package and ask for user permission if needed

    Args:
        package_name (str): name of the package

    Returns:
        tuple[bool, str]: (success, installation output)
    """
    ensurepip.bootstrap()
    os.environ.pop("PIP_REQ_TRACKER", None)
    path = "%s\\test_easy_package_installation" % os.path.dirname(sys.executable)
    try:
        # creates and removes dir to check for writing permission to this path
        os.mkdir(path)
        os.rmdir(path)
        output = subprocess.check_output(
            [sys.executable, '-m', 'pip', 'install', package_name, '--no-color']
        ).decode('utf-8').replace("\r", "")
        return (True, output)
    except PermissionError as err:
        if sys.platform == "win32":
            logger.info("Need Admin Permissions to write to %s" % path)
            logger.info("Try again to install fontTools as admin")
            output = subprocess.check_output(
                [sys.executable, '-m', 'pip', 'uninstall', '-y', package_name, '--no-color'],
                stderr=subprocess.STDOUT
            ).decode('utf-8').replace("\r", "")
            logger.info(output)
            output = subprocess.check_output(
                ['powershell.exe', '-Command',
                    """& { Start-Process \'%s\' -Wait -ArgumentList \'-m\',
                    \'pip\', \'install\', \'%s\'-Verb RunAs}""" % (sys.executable, package_name)],
                stderr=subprocess.STDOUT
            ).decode('unicode_escape').replace("\r", "")
            if output != '':
                return (False, output)
        else:
            return (False, err)
    except subprocess.CalledProcessError as err:
        return (False, err.output)
    return (False, ":(")


def get_preferences(context: bpy.types.Context) -> bpy.types.AddonPreferences:
    """
    get addon preferences of this addon, which are stored in Blender

    Args:
        context (bpy.types.Context): active blender context

    Returns:
        bpy.types.AddonPreferences: preferences of this addon
    """
    return context.preferences.addons[__module__].preferences
# endregion
