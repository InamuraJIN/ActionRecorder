# region Imports
# external modules
import json
import os
from typing import Union

# blender modules
import bpy
from bpy.app.handlers import persistent

# relative imports
from ..log import logger
from .. import ui_functions, shared_data, keymap
from . import shared
from .shared import get_preferences
# endregion


# region Functions


def global_runtime_save(ActRec_pref: bpy.types.AddonPreferences, use_autosave: bool = True):
    """
    save global actions to the local temp (dict) while Blender is running

    Args:
        ActRec_pref (bpy.types.AddonPreferences): preferences of this addon
        use_autosave (bool, optional):
            include autosave to storage file (depend on AddonPreference autosave).
            Defaults to True.
    """
    shared_data.global_temp = shared.property_to_python(ActRec_pref.global_actions)
    if use_autosave and ActRec_pref.autosave:
        save(ActRec_pref)


@persistent
def global_runtime_load(dummy: bpy.types.Scene = None):
    """
    load global actions while Blender is running from the local temp (dict)

    Args:
        dummy (bpy.types.Scene, optional): unused. Defaults to None.
    """
    ActRec_pref = get_preferences(bpy.context)
    ActRec_pref.global_actions.clear()
    # needed otherwise all global actions get selected
    ActRec_pref["global_actions.selected_ids"] = []
    # Writes data from global_temp (JSON format) to global_actions (Blender Property)
    for action in shared_data.global_temp:
        shared.add_data_to_collection(ActRec_pref.global_actions, action)


def save(ActRec_pref: bpy.types.AddonPreferences):
    """
    save the global actions and categories to the storage file

    Args:
        ActRec_pref (bpy.types.AddonPreferences): preferences of this addon
    """
    data = {}
    data['categories'] = shared.property_to_python(
        ActRec_pref.categories,
        exclude=["name", "selected", "actions.name", "areas.name", "areas.modes.name"]
    )
    data['actions'] = shared.property_to_python(
        ActRec_pref.global_actions,
        exclude=["name", "selected", "alert", "macros.name", "macros.is_available", "macros.alert"]
    )
    with open(ActRec_pref.storage_path, 'w', encoding='utf-8') as storage_file:
        json.dump(data, storage_file, ensure_ascii=False, indent=2)
    logger.info('saved global actions')


def load(ActRec_pref: bpy.types.AddonPreferences) -> bool:
    """
    load the global actions and categories from the storage file

    Args:
        ActRec_pref (bpy.types.AddonPreferences): preferences of this addon

    Returns:
        bool: success
    """
    # REFACTOR indentation
    if os.path.exists(ActRec_pref.storage_path):
        with open(ActRec_pref.storage_path, 'r', encoding='utf-8') as storage_file:
            text = storage_file.read()
            if not text:
                text = "{}"
            data = json.loads(text)
        logger.info('load global actions')
        # cleanup
        for i in range(len(ActRec_pref.categories)):
            ui_functions.unregister_category(ActRec_pref, i)
        ActRec_pref.categories.clear()
        ActRec_pref.global_actions.clear()
        # load data
        if data:
            import_global_from_dict(ActRec_pref, data)
            return True
    return False


def import_global_from_dict(ActRec_pref: bpy.types.AddonPreferences, data: dict):
    """
    import the global actions and categories from a dict

    Args:
        ActRec_pref (bpy.types.AddonPreferences): preferences of this addon
        data (dict): dict to use
    """
    value = data.get('categories', None)
    if value:
        shared.apply_data_to_item(ActRec_pref.categories, value)
    value = data.get('actions', None)
    if value:
        shared.apply_data_to_item(ActRec_pref.global_actions, value)

    for i in range(len(ActRec_pref.categories)):
        ui_functions.register_category(ActRec_pref, i)
    if len(ActRec_pref.categories):
        ActRec_pref.categories[0].selected = True
    if len(ActRec_pref.global_actions):
        ActRec_pref.global_actions[0].selected = True


def get_global_action_id(ActRec_pref: bpy.types.AddonPreferences, id: str, index: int) -> Union[str, None]:
    """
    get global action id based on id (check for existence) or index

    Args:
        ActRec_pref (bpy.types.AddonPreferences): preferences of this addon
        id (str): id to check
        index (int): index of action

    Returns:
        Union[str, None]: str: action id; None: fail
    """
    # REFACTOR indentation
    if ActRec_pref.global_actions.find(id) == -1:
        if index >= 0 and len(ActRec_pref.global_actions) > index:
            return ActRec_pref.global_actions[index].id
        else:
            return None
    else:
        return id


def get_global_action_ids(ActRec_pref: bpy.types.AddonPreferences, id: str, index: int) -> list:
    """
    get global action is inside a list or selected global actions if not found

    Args:
        ActRec_pref (bpy.types.AddonPreferences): preferences of this addon
        id (str): id to check
        index (int): index of action

    Returns:
        list: list with ids of actions
    """
    id = get_global_action_id(ActRec_pref, id, index)
    if id is None:
        return ActRec_pref.get("global_actions.selected_ids", [])
    return [id]


def add_empty_action_keymap(id: str) -> bpy.types.KeyMapItem:
    """
    adds an empty keymap for a global action

    Args:
        id (str): id of the action

    Returns:
        bpy.types.KeyMapItem: created keymap or found keymap of action
    """
    logger.info("add empty action")
    kmi = get_action_keymap(id)
    if kmi is None:
        kmi = keymap.keymaps['default'].keymap_items.new("ar.global_execute_action", "NONE", "PRESS")
        kmi.properties.id = id
    return kmi


def get_action_keymap(id: str) -> Union[bpy.types.KeyMapItem, None]:
    """
    get the keymap of the action with the given id

    Args:
        id (str): id of the action

    Returns:
        Union[bpy.types.KeyMapItem, None]: KeyMapItem on success; None on fail
    """
    items = keymap.keymaps['default'].keymap_items
    for kmi in items:
        if kmi.idname == "ar.global_execute_action" and kmi.properties.id == id:
            return kmi
    return None


def is_action_keymap_empty(kmi: bpy.types.KeyMapItem) -> bool:
    """
    checks is the given keymapitem is empty

    Args:
        kmi (bpy.types.KeyMapItem): keymapitem to check

    Returns:
        bool: is empty
    """
    return kmi.type == "NONE"


def remove_action_keymap(id: str):
    """
    removes the keymapitem for the action with the given id

    Args:
        id (str): id of the action
    """
    kmi = get_action_keymap(id)
    items = keymap.keymaps['default'].keymap_items
    items.remove(kmi)
# endregion
