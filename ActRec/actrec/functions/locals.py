# region Imports
# external modules
import json
from typing import TYPE_CHECKING

# blender modules
import bpy
from bpy.app.handlers import persistent
from bpy.types import AddonPreferences, Scene, PropertyGroup

# relative imports
from .. import shared_data
from . import shared
from .shared import get_preferences
if TYPE_CHECKING:
    from ..preferences import AR_preferences
    from ..properties.locals import AR_local_actions
else:
    AR_preferences = AddonPreferences
    AR_local_actions = PropertyGroup
# endregion


# region Functions


def save_local_to_scene(ActRec_pref: AR_preferences, scene: Scene) -> None:
    """
    saves all local actions to the given scene

    Args:
        ActRec_pref (AR_preferences): preferences of this addon
        scene (Scene): Blender scene to write to
    """
    scene.ar.local = json.dumps(shared.property_to_python(ActRec_pref.local_actions))


def load_local_action(ActRec_pref: AR_preferences, data: list) -> None:
    """
    load the given data to the local actions

    Args:
        ActRec_pref (AR_preferences): preferences of this addon
        data (list): data to apply
    """
    actions = ActRec_pref.local_actions
    actions.clear()
    for value in data:
        shared.add_data_to_collection(actions, value)


def local_action_to_text(action: AR_local_actions, text_name: str = None) -> None:
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


def remove_local_action_from_text(action: AR_local_actions, text_name: str = None) -> None:
    """
    remove the local action from the TextEditor

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


def get_local_action_index(ActRec_pref: AR_preferences, id: str, index: int) -> int:
    """
    get local action index based on the given id or index (checks if index is in range)

    Args:
        ActRec_pref (AR_preferences): preferences of this addon
        id (str): id to get index from
        index (int): index for fallback

    Returns:
        int: valid index of a local actions or active local action index on fallback
    """
    action = ActRec_pref.local_actions.find(id)
    if action != -1:
        return action
    if index >= 0 and len(ActRec_pref.local_actions) > index:  # fallback to input index
        return index
    else:
        return ActRec_pref.active_local_action_index  # fallback to selection


# endregion
