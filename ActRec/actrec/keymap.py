# region Imports
# external modules
import os
import json

# blender modules
import bpy
from bpy.types import KeyMapItems

# relative imports
from .log import logger
# endregion

keymaps = {}
keymap_path = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    "keymap.json"
)

# region functions


def load_action_keymap(items: KeyMapItems) -> None:
    """
    reads the global action keymap from file located inside the addon folder.

    Needed because shortcut of global actions can be added dynamically
    and therefore needed to be known while Blender register.

    Args:
        items (KeyMapItems): "Keymap items to register loaded keymap to"
    """
    if not os.path.exists(keymap_path):
        return
    with open(keymap_path, 'r', encoding='utf-8') as keymap_file:
        text = keymap_file.read()
        if not text:
            text = "{}"
        data = json.loads(text)
        logger.info('load actions keymap')

    load_action_keymap_data(data, items)


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
            repeat=key['repeat']
        )
        kmi.properties.id = key['id']
        kmi.active = key['active']
        kmi.map_type = key['map_type']


def action_keymap_to_data(items: KeyMapItems) -> dict:
    """
    converts an global action keymap into a dict of JSON Format

    Args:
        items (KeyMapItems): Keymap items to convert to dict

    Returns:
        dict: JSON Format
    """
    return {
        'keymap': [{
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
        } for kmi in items if kmi.idname == "ar.global_execute_action"]
    }


def save_action_keymap(items: KeyMapItems) -> None:
    """
    writes the global action keymap to a file located inside the addon folder.

    Needed because shortcut of global actions can be added dynamically
    and therefore needed to be known while Blender register.

    Args:
        items (KeyMapItems): "Keymap items to unregister loaded global keymaps from"
    """
    data = action_keymap_to_data(items)
    with open(keymap_path, 'w', encoding='utf-8') as storage_file:
        json.dump(data, storage_file, ensure_ascii=False, indent=2)
    logger.info('saved actions keymap')

# endregion

# region Registration


def register():
    addon = bpy.context.window_manager.keyconfigs.addon
    if addon:
        km = addon.keymaps.new(name='Screen')
        keymaps['default'] = km
        items = km.keymap_items
        # operators
        items.new("ar.macro_add", 'COMMA', 'PRESS', alt=True)
        items.new("ar.local_play", 'PERIOD', 'PRESS', alt=True)
        items.new("ar.local_selection_up", 'WHEELUPMOUSE',
                  'PRESS', shift=True, alt=True)
        items.new("ar.local_selection_down", 'WHEELDOWNMOUSE',
                  'PRESS', shift=True, alt=True)
        load_action_keymap(items)
        # menu
        kmi = items.new("wm.call_menu_pie", 'A', 'PRESS', shift=True, alt=True)
        kmi.properties.name = 'AR_MT_action_pie'
        kmi = items.new("wm.call_menu", 'C', 'PRESS', shift=True, alt=True)
        kmi.properties.name = 'AR_MT_Categories'


def unregister():
    addon = bpy.context.window_manager.keyconfigs.addon
    # REFACTOR indentation
    if addon:
        default_km = keymaps.get('default')
        if default_km:
            save_action_keymap(default_km.keymap_items)
        for km in keymaps.values():
            addon.keymaps.remove(km)
# endregion
