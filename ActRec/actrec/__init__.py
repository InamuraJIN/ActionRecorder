# region Imports
# external modules
import json

# blender modules
import bpy
from bpy.app.handlers import persistent
from bpy.props import PointerProperty

# relative imports
# unused import needed to give direct access to the modules
from . import functions, menus, operators, panels, properties, ui_functions, uilist
from . import config, icon_manager, keymap, log, preferences, update
from .functions.shared import get_preferences
from . import shared_data
# endregion


@persistent
def check_on_load(dummy=None):
    """
    used to load global actions if on_load wasn't called
    """
    if check_on_load in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.remove(check_on_load)
    if shared_data.data_loaded:
        return
    on_load()


@persistent
def on_load(dummy=None):
    shared_data.data_loaded = True
    log.logger.info("Start: Load ActRec Data")
    context = bpy.context
    ActRec_pref = get_preferences(context)
    ActRec_pref.operators_list_length = 0
    # load local actions
    if bpy.data.filepath == "":
        try:
            context.scene.ar.local = "{}"
        except AttributeError as err:
            log.logger.info(err)
    # load old local action data
    elif context.scene.ar.local == "{}" and context.scene.get('ar_local', None):
        try:
            data = []
            old_data = json.loads(context.scene.get('ar_local'))
            for i, old_action in enumerate(old_data[0]['Commands'], 1):
                data.append({
                    "label": old_action['cname'],
                    "macros": [{
                        "label": old_macro['cname'],
                        "command": old_macro['macro'],
                        "active": old_macro['active'],
                        "icon": old_macro['icon']
                    } for old_macro in old_data[i]['Commands']],
                    "icon": old_action['icon']
                })
            context.scene.ar.local = json.dumps(data)
        except json.JSONDecodeError as err:
            log.logger.info("old scene-data couldn't be parsed (%s)" % err)
    functions.load_local_action(ActRec_pref, json.loads(context.scene.ar.local))

    # update paths
    ActRec_pref.storage_path = ActRec_pref.storage_path
    ActRec_pref.icon_path = ActRec_pref.icon_path

    functions.load(ActRec_pref)
    icon_manager.load_icons(ActRec_pref)
    log.logger.info("Finished: Load ActRec Data")

# region Registration


def register():
    log.log_sys.append_file()
    properties.register()
    menus.register()
    operators.register()
    panels.register()
    uilist.register()
    icon_manager.register()
    update.register()
    preferences.register()
    keymap.register()

    handlers = bpy.app.handlers
    handlers.render_complete.append(functions.execute_render_complete)
    handlers.depsgraph_update_post.append(functions.track_scene)
    handlers.load_post.append(on_load)
    handlers.depsgraph_update_post.append(check_on_load)

    bpy.types.Scene.ar = PointerProperty(type=properties.AR_scene_data)

    shared_data.data_loaded = False
    log.logger.info("Registered Action Recorder")


def unregister():
    properties.unregister()
    menus.unregister()
    operators.unregister()
    panels.unregister()
    uilist.unregister()
    icon_manager.unregister()
    update.unregister()
    preferences.unregister()
    keymap.unregister()
    ui_functions.unregister()

    handlers = bpy.app.handlers
    handlers.render_complete.remove(functions.execute_render_complete)
    handlers.depsgraph_update_post.remove(functions.track_scene)
    handlers.load_post.remove(on_load)
    if check_on_load in bpy.app.handlers.depsgraph_update_post:
        handlers.depsgraph_update_post.remove(check_on_load)

    del bpy.types.Scene.ar
    log.logger.info("Unregistered Action Recorder")
    log.log_sys.detach_file()
# endregion
