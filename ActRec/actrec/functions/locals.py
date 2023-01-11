# region Imports
# external modules
import json

# blender modules
import bpy
from bpy.app.handlers import persistent

# relative imports
from .. import shared_data
from . import shared
from .shared import get_preferences
# endregion


# region Functions


def local_runtime_save(ActRec_pref: bpy.types.AddonPreferences, scene: bpy.types.Scene, use_autosave: bool = True):
    """
    save local action to the local temp (dict) while Blender is running

    Args:
        ActRec_pref (bpy.types.AddonPreferences): preferences of this addon
        scene (bpy.types.Scene): Blender scene to write to
        use_autosave (bool, optional): include autosave to scene (depend on AddonPreference autosave). Defaults to True.
    """
    shared_data.local_temp = shared.property_to_python(ActRec_pref.local_actions)
    if use_autosave and ActRec_pref.autosave and scene:
        scene.ar.local = json.dumps(shared_data.local_temp)


@persistent
def local_runtime_load(dummy: bpy.types.Scene = None):
    """
    loads local actions from the local temp (dict) while Blender is running

    Args:
        dummy (bpy.types.Scene, optional): unused. Defaults to None.
    """
    ActRec_pref = get_preferences(bpy.context)
    ActRec_pref.local_actions.clear()
    for action in shared_data.local_temp:
        shared.add_data_to_collection(ActRec_pref.local_actions, action)


def save_local_to_scene(ActRec_pref: bpy.types.AddonPreferences, scene: bpy.types.Scene):
    """
    saves all local actions to the given scene

    Args:
        ActRec_pref (bpy.types.AddonPreferences): preferences of this addon
        scene (bpy.types.Scene): Blender scene to write to
    """
    scene.ar.local = json.dumps(shared.property_to_python(ActRec_pref.local_actions))


def load_local_action(ActRec_pref: bpy.types.AddonPreferences, data: list):
    """
    load the given data to the local actions

    Args:
        ActRec_pref (bpy.types.AddonPreferences): preferences of this addon
        data (list): data to apply
    """
    actions = ActRec_pref.local_actions
    actions.clear()
    for value in data:
        shared.add_data_to_collection(actions, value)


def local_action_to_text(action: 'AR_local_actions', text_name: str = None):
    """
    write the local action and it's macro to the TextEditor

    Args:
        action (AR_local_actions): action to write
        text_name (str, optional): name of the written text. Defaults to None.
    """
    if text_name is None:
        text_name = action.label
    texts = bpy.data.texts
    if texts.find(text_name) == -1:
        texts.new(text_name)
    text = texts[text_name]
    text.clear()
    text.write(
        "###ActRec_pref### id: '%s', icon: %i\n%s" % (
            action.id, action.icon, "\n".join(
                ["%s # id: '%s', label: '%s', icon: %i, active: %s, is_available: %s" % (
                    macro.command, macro.id, macro.label, macro.icon, macro.active, macro.is_available
                ) for macro in action.macros]
            )
        )
    )


def remove_local_action_from_text(action: 'AR_local_actions', text_name: str = None):
    """
    remove the local action from the TextEditro

    Args:
        action (AR_local_actions): action to remove
        text_name (str, optional): name of the text to remove. Defaults to None.
    """
    if text_name is None:
        text_name = action.label
    texts = bpy.data.texts
    text_index = texts.find(text_name)
    if text_index != -1:
        texts.remove(texts[text_index])
        return
    id = action.id
    for text in texts:
        if text.lines[0].body.strip().startswith("###ActRec_pref### id: '%s'" % id):
            texts.remove(text)
            return
            

def get_local_action_index(ActRec_pref: bpy.types.AddonPreferences, id: str, index: int) -> int:
    """
    get local action index based on the given id or index (checks if index is in range)

    Args:
        ActRec_pref (bpy.types.AddonPreferences): preferences of this addon
        id (str): id to get index from
        index (int): index for fallback

    Returns:
        int: valid index of a local actions or active local action index on fallback
    """
    # REFACTOR indentation
    action = ActRec_pref.local_actions.find(id)
    if action == -1:
        if index >= 0 and len(ActRec_pref.local_actions) > index:  # fallback to input index
            action = index
        else:
            action = ActRec_pref.active_local_action_index  # fallback to selection
    return action


# endregion
