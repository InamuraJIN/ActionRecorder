# region Imports
# external modules
import os
import json
from collections import defaultdict

# blender modules
import bpy
from bpy.types import KeyMapItems, KeyMap

# relative imports
from .log import logger
# endregion

keymaps = {}
keymap_items = defaultdict(list)

# region functions


def load_action_keymap_data(data: list, items: KeyMapItems) -> None:
    """
    applies action keymap data in JSON format to Blender

    Args:
        data (dict): Keymap in JSON Format
        items (KeyMapItems): Keymap items to register data to
    """
    if not data:
        return
    for key in data.get('keymap', []):
        kmi = items.new(
            "ar.global_execute_action", key['type'],
            key['value'],
            any=key['any'],
            shift=key['shift'],
            ctrl=key['ctrl'],
            alt=key['alt'],
            oskey=key['oskey'],
            key_modifier=key['key_modifier'],
            repeat=key['repeat'],
            head=True
        )
        kmi.properties.id = key['id']
        kmi.active = key['active']
        kmi.map_type = key['map_type']


def append_keymap(data: dict, export_action_ids: list, km: KeyMap) -> None:
    """
    Appends the given keymap to the data dict with on the key 'keymap'
    wich holds a dict of the values 'id, active, type, value,
    any, shift, ctrl, alt, oskey, key_modifier, repeat, map_type'.

    Args:
        data (dict): The dict where the keymap gets appended.
        export_action_ids (list): The ids of the action that get exported i.e. are selected for export
        km (KeyMap): The keymap to append.
    """
    for kmi in km.keymap_items:
        if kmi.idname == "ar.global_execute_action" and kmi.properties.id in export_action_ids:
            data['keymap'].append({
                'id': kmi.properties['id'],
                'active': kmi.active,
                'type': kmi.type,
                'value': kmi.value,
                'any': kmi.any,
                'shift': kmi.shift,
                'ctrl': kmi.ctrl,
                'alt': kmi.alt,
                'oskey': kmi.oskey,
                'key_modifier': kmi.key_modifier,
                'repeat': kmi.repeat,
                'map_type': kmi.map_type
            })

# endregion

# region Registration


def register():
    addon = bpy.context.window_manager.keyconfigs.addon
    if addon:
        keymaps['temp'] = addon.keymaps.new(name='ActionButtons')
        km = addon.keymaps.new(name='Screen')
        keymaps['default'] = km
        save_items = keymap_items['default']
        items = km.keymap_items
        # operators
        kmi = items.new("ar.macro_add", 'COMMA', 'PRESS', alt=True)
        save_items.append(kmi)
        kmi = items.new("ar.local_play", 'PERIOD', 'PRESS', alt=True)
        save_items.append(kmi)
        kmi = items.new(
            "ar.local_selection_up",
            'WHEELUPMOUSE',
            'PRESS',
            shift=True,
            alt=True
        )
        save_items.append(kmi)
        kmi = items.new(
            "ar.local_selection_down",
            'WHEELDOWNMOUSE',
            'PRESS',
            shift=True,
            alt=True
        )
        save_items.append(kmi)
        # menu
        kmi = items.new("wm.call_menu_pie", 'A', 'PRESS', shift=True, alt=True)
        kmi.properties.name = 'AR_MT_action_pie'
        save_items.append(kmi)
        kmi = items.new("wm.call_menu", 'C', 'PRESS', shift=True, alt=True)
        kmi.properties.name = 'AR_MT_Categories'
        save_items.append(kmi)


def unregister():
    addon = bpy.context.window_manager.keyconfigs.addon
    if not addon:
        return
    for km in keymaps.values():
        if keymaps.get(km.name):
            addon.keymaps.remove(km)
    keymaps.clear()
    keymap_items.clear()
# endregion
