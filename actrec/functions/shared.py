# region Imports
# external modules
from typing import Optional, Union
from contextlib import suppress
from collections import defaultdict
import json
import time
import os
import sys
import random, math, numpy
import functools

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
def check_for_dublicates(l: list, name: str, num = 1) -> str: #Check for name duplicates and append .001, .002 etc.
    split = name.split(".")
    base_name = name
    if split[-1].isnumeric():
        base_name = ".".join(split[:-1])
    while name in l:
        name = "{0}.{1:03d}".format(base_name, num)
        num += 1
    return name

def get_pointer_as_dict(property, exclude, depth):
    data = {} # PointerProperty
    main_exclude = []
    sub_exclude = defaultdict(list)
    for x in exclude:
        prop = x.split(".")
        if len(prop) > 1:
            sub_exclude[prop[0]].append(".".join(prop[1:]))
        else:
            main_exclude.append(prop[0])
    main_exclude = set(main_exclude)
    for attr in property.bl_rna.properties[1:]:
        identifier = attr.identifier
        if identifier not in main_exclude:
            data[identifier] = property_to_python(getattr(property, identifier), sub_exclude.get(identifier, []), depth - 1)
    return data

def property_to_python(property, exclude: list = [], depth= 5):
    if depth <= 0:
        return "max depth"
    if hasattr(property, 'id_data'):
        id_property = property.id_data
        if property == id_property:
            return property
        class_name = property.__class__.__name__
        if class_name =='bpy_prop_collection_idprop':
            return [property_to_python(item, exclude, depth) for item in property] # ColllectionProperty
        elif class_name =='bpy_prop_collection':
            if hasattr(property, "bl_rna"):
                data = get_pointer_as_dict(property, exclude, depth)
                data["items"] = [property_to_python(item, exclude, depth) for item in property]
                return data
            else:
                return [property_to_python(item, exclude, depth) for item in property]
        elif class_name == 'bpy_prop_array':
            return [property_to_python(item, exclude, depth) for item in property]
        else:
            return get_pointer_as_dict(property, exclude, depth)
    return property

def apply_data_to_item(item, data, key = "") -> None:
    if isinstance(data, list):
        for element in data:
            if key:
                subitem = getattr(item, key).add()
            else:
                subitem = item.add()
            apply_data_to_item(subitem, element)
    elif isinstance(data, dict):
        for key, value in data.items():
            apply_data_to_item(item, value, key)
    elif hasattr(item, key):
        with suppress(AttributeError): # catch Exception from read-only property
            setattr(item, key, data)

def add_data_to_collection(collection, data: dict) -> None:
    new_item = collection.add()
    apply_data_to_item(new_item, data)
                
def insert_to_collection(collection, index: int, data: dict) -> None:
    add_data_to_collection(collection, data)
    collection.move(len(collection) - 1, index)

def enum_list_id_to_name_dict(data: list) -> dict:
    return {identifier: name for identifier, name, *tail in data}

def swap_collection_items(collection, index_1: int, index_2: int) -> None:
    if index_1 == index_2:
        return
    if index_1 < index_2:
        index_1, index_2 = index_2, index_1
    collection.move(index_1, index_2)
    collection.move(index_2 + 1, index_1)

def get_name_of_command(context, command: str) -> Optional[str]:
    if command.startswith("bpy.ops."):
        try:
            return eval("%s.get_rna_type().name" %command.split("(")[0])
        except:
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

            return "%s = %s" %(prop, value)
        else:
            return ".".join(split[0].split('.')[-2:])
    else:
        return None

def extract_properties(properties :str) -> list:
    """
    Input Properties as "prop1, prop2, ..."
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
            prop_str += ",%s" %prop[0]
    new_props.append(prop_str.strip())
    return new_props[1:]

def update_command(command: str) -> Union[str, bool, None]:
    if command.startswith("bpy.ops."):
        command, values = command.split("(", 1)
        values = extract_properties(values[:-1])
        for i in range(len(values)):
            values[i] = values[i].split("=")
        try:
            props = eval("%s.get_rna_type().properties[1:]" %command)
        except:
            return None
        inputs = []
        for prop in props:
            for value in values:
                if value[0] == prop.identifier:
                    inputs.append("%s=%s" %(value[0], value[1]))
                    values.remove(value)
                    break
        return "%s(%s)" %(command, ", ".join(inputs))
    else:
        return False

def run_queued_macros(context_copy, action_type, action_id, start):
    AR = context_copy['preferences'].addons[__module__].preferences
    action = getattr(AR, action_type)[action_id]
    play(context_copy, action.macros[start: ], action, action_type)

def play(context_copy, macros, action, action_type: str): 
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
                
    for i, macro in enumerate(macros): # realtime events
        split = macro.command.split(":")
        if split[0] == 'ar.event': 
            data = json.loads(":".join(split[1:]))
            if data['Type'] == 'Timer':
                bpy.app.timers.register(functools.partial(run_queued_macros, context_copy, action_type, action.id, i + 1), first_interval= data['Time'])
                return
            elif data['Type'] == 'Loop':
                end_index = i + 1
                loop_count = 1
                for j, process_macro in enumerate(macros[i + 1:], i + 1):
                    if process_macro.active:
                        split = process_macro.command.split(":")
                        if split[0] == 'ar.event': # realtime events
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
                
                return play(context_copy, macros[end_index + 1: ], action, action_type)
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
                    return "%s Object doesn't exist in the active view layer" %data['Object']
                continue
            elif data['Type'] == 'EndLoop':
                continue
        try:
            command = macro.command
            if command.startswith("bpy.ops.ar.local_play") and set(extract_properties(command.split("(")[1][:-1])) == {"id=\"\"", "index=-1"}:
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
                command = "%s(context_copy, %s" %(split[0], "(".join(split[1: ]))
            elif command.startswith("bpy.context."):
                split = command.replace("bpy.context.", "").split(".")
                command = "context_copy['%s'].%s" %(split[0], ".".join(split[1: ]))

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
            logger.error("%s; command: %s" %(err, command))
            action.alert = macro.alert = True
            if base_area:
                base_area.ui_type = area_type
            return err

@persistent
def execute_render_init(dummy = None):
    context = bpy.context
    AR = context.preferences.addons[__module__].preferences
    for action_type, action_id, start in shared_data.render_init_macros:
        action = getattr(AR, action_type)[action_id]
        play(context.copy(), action.macros[start: ], action, action_type)

@persistent
def execute_render_complete(dummy = None):
    context = bpy.context
    AR = context.preferences.addons[__module__].preferences
    for action_type, action_id, start in shared_data.render_complete_macros:
        action = getattr(AR, action_type)[action_id]
        play(context.copy(), action.macros[start: ], action, action_type)

def get_font_path():
    if bpy.context.preferences.view.font_path_ui == '':
        dirc = "\\".join(sys.executable.split("\\")[:-3])
        return os.path.join(dirc, "datafiles", "fonts", "droidsans.ttf")
    else:
        return bpy.context.preferences.view.font_path_ui

def split_and_keep(sep, text):
    p=chr(ord(max(text))+1)
    for s in sep:
        text = text.replace(s, s+p)
    return text.split(p)

def text_to_lines(text, font_text, limit, endcharacter = " ,"):
    if text == "" or not font_text.use_dynamic_text:
        return [text]
    characters_width = font_text.get_width_of_text(text)
    possible_breaks = split_and_keep(endcharacter, text)
    lines = [""]
    start = 0
    for psb in possible_breaks:
        line_length = len(lines[-1])
        total_line_length = start + line_length
        total_length = total_line_length + len(psb)
        width = sum(characters_width[start : total_length])
        if width <= limit:
            lines[-1] += psb
        else:
            if sum(characters_width[total_line_length : total_length]) > limit:
                start += line_length
                while psb != "":
                    i = int(bl_math.clamp(limit / width * len(psb), 0, len(psb)))
                    if len(psb) != i:
                        if sum(characters_width[start : start + i]) <= limit:
                            while sum(characters_width[start : start + i]) <= limit:
                                i += 1
                            i -= 1
                        else:
                            while sum(characters_width[start : start + i]) >= limit:
                                i -= 1
                            i += 1
                    lines.append(psb[:i])
                    psb = psb[i:]
                    start += i
                    width = sum(characters_width[start : total_length])
            else:
                lines.append(psb)
                start += line_length + len(psb)
    if(lines[0] == ""):
        lines.pop(0)
    return lines
# endregion
