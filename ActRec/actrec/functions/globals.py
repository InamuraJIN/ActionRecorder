# region Imports
# external modules
import json
import os
from typing import Union, TYPE_CHECKING, Iterable

# blender modules
import bpy
from bpy.types import AddonPreferences, Context, KeyMapItem, KeyMap

# relative imports
from ..log import logger
from .. import ui_functions, keymap
from . import shared
if TYPE_CHECKING:
    from ..preferences import AR_preferences
else:
    AR_preferences = AddonPreferences
# endregion


# region Functions


def save(ActRec_pref: AR_preferences) -> None:
    """
    save the global actions and categories to the storage file

    Args:
        ActRec_pref (AR_preferences): preferences of this addon
    """
    data = {}
    data['categories'] = shared.property_to_python(
        ActRec_pref.categories,
        exclude=[
            "name",
            "selected",
            "actions.name",
            "areas.name",
            "areas.modes.name"
        ]
    )
    data['actions'] = shared.property_to_python(
        ActRec_pref.global_actions,
        exclude=[
            "name",
            "selected",
            "alert",
            "execution_mode",
            "macros.name",
            "macros.is_available",
            "macros.is_playing",
            "macros.alert",
            "is_playing"
        ]
    )
    with open(ActRec_pref.storage_path, 'w', encoding='utf-8') as storage_file:
        json.dump(data, storage_file, ensure_ascii=False, indent=2)
    logger.info('saved global actions')


def load(ActRec_pref: AR_preferences) -> bool:
    """
    load the global actions and categories from the storage file

    Args:
        ActRec_pref (AR_preferences): preferences of this addon

    Returns:
        bool: success
    """
    if not os.path.exists(ActRec_pref.storage_path):
        return False
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


def import_global_from_dict(ActRec_pref: AR_preferences, data: dict) -> None:
    """
    import the global actions and categories from a dict

    Args:
        ActRec_pref (AR_preferences): preferences of this addon
        data (dict): dict to use
    """
    existing_category_len = len(ActRec_pref.categories)
    value = data.get('categories', None)
    if value:
        shared.apply_data_to_item(ActRec_pref.categories, value)
    value = data.get('actions', None)
    if value:
        shared.apply_data_to_item(ActRec_pref.global_actions, value)

    for i in range(existing_category_len, len(ActRec_pref.categories)):
        ui_functions.register_category(ActRec_pref, i)
    if len(ActRec_pref.categories):
        ActRec_pref.categories[0].selected = True
    if len(ActRec_pref.global_actions):
        ActRec_pref.global_actions[0].selected = True


def get_global_action_id(ActRec_pref: AR_preferences, id: str, index: int) -> Union[str, None]:
    """
    get global action id based on id (check for existence) or index

    Args:
        ActRec_pref (AR_preferences): preferences of this addon
        id (str): id to check
        index (int): index of action

    Returns:
        Union[str, None]: str: action id; None: fail
    """
    if ActRec_pref.global_actions.find(id) != -1:
        return id
    if index >= 0 and len(ActRec_pref.global_actions) > index:
        return ActRec_pref.global_actions[index].id
    else:
        return None


def get_global_action_ids(ActRec_pref, id, index):
    # BLENDER 5.0 FIX: Convert the internal string back to a list for the operators
    raw_ids = ActRec_pref.global_selected_ids_internal
    if raw_ids:
        return raw_ids.split(",")
    return []


def add_empty_action_keymap(id: str, km: KeyMap) -> KeyMapItem:
    """
    adds an empty keymap for a global action

    Args:
        id (str): id of the action
        context (Context): active blender context

    Returns:
        KeyMapItem: created keymap or found keymap of action
    """
    logger.info("add empty action")
    kmi = get_action_keymap(id, km)
    if kmi is None:
        kmi = km.keymap_items.new(
            "ar.global_execute_action",
            "NONE",
            "PRESS",
            head=True
        )
        kmi.properties.id = id
    return kmi


def get_action_keymap(id: str, km: KeyMap) -> Union[KeyMapItem, None]:
    """
    get the keymap of the action with the given id

    Args:
        id (str): id of the action
        context (Context): active blender context

    Returns:
        Union[KeyMapItem, None]: KeyMapItem on success; None on fail
    """
    for kmi in km.keymap_items:
        if kmi.idname == "ar.global_execute_action" and kmi.properties.id == id:
            return kmi
    return None


def is_action_keymap_empty(kmi: KeyMapItem) -> bool:
    """
    checks is the given keymapitem is empty

    Args:
        kmi (KeyMapItem): keymapitem to check

    Returns:
        bool: is empty
    """
    return kmi.type == "NONE"


def remove_action_keymap(id: str, km: KeyMap) -> None:
    """
    removes the keymapitem for the action with the given id

    Args:
        id (str): id of the action
        context (Context): active blender context
    """
    kmi = get_action_keymap(id, km)
    km.keymap_items.remove(kmi)


def get_all_action_keymaps(km: KeyMap) -> Iterable[KeyMapItem]:
    return filter(lambda x: x.idname == "ar.global_execute_action", km.keymap_items)
# endregion
