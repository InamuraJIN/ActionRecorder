# region Imports
# external modules
import json

# blender modules
import bpy
from bpy.app.handlers import persistent

# relative imports
from .. import shared_data
from . import shared
# endregion

__module__ = __package__.split(".")[0]

# region Functions
def local_runtime_save(AR, scene: bpy.types.Scene, use_autosave: bool = True) -> None:
    """includes autosave to scene (depend on AddonPreference autosave)"""
    shared_data.local_temp = shared.property_to_python(AR.local_actions)
    if use_autosave and AR.autosave and scene:
        scene.ar.local = json.dumps(shared_data.local_temp)

@persistent
def local_runtime_load(dummy = None):
    AR = bpy.context.preferences.addons[__module__].preferences
    AR.local_actions.clear()
    for action in shared_data.local_temp:
        shared.add_data_to_collection(AR.local_actions, action)

def save_local_to_scene(AR, scene):
    scene.ar.local = json.dumps(shared.property_to_python(AR.local_actions))

def get_local_action_index(AR, id, index):
    action = AR.local_actions.find(id)
    if action == -1:
        if index >= 0 and len(AR.local_actions) > index: # fallback to input index
            action = index
        else:
            action = AR.active_local_action_index # fallback to selection
    return action

def load_local_action(AR, data: list):
    actions = AR.local_actions
    actions.clear()
    for value in data:
        shared.add_data_to_collection(actions, value)

def local_action_to_text(action, text_name = None):
    if text_name is None:
        text_name = action.label
    texts = bpy.data.texts
    if texts.find(text_name) == -1:
        texts.new(text_name)
    text = texts[text_name]
    text.clear()
    text.write("###AR### id: '%s', icon: %i\n%s" %(action.id, action.icon, 
        "\n".join(["%s # id: '%s', label: '%s', icon: %i, active: %s, is_available: %s"
        %(macro.command, macro.id, macro.label, macro.icon, macro.active, macro.is_available) for macro in action.macros])
        )
    )
# endregion
