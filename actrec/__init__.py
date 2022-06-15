# region Imports
# external modules
import json

# blender modules
import bpy
from bpy.app.handlers import persistent
from bpy.props import PointerProperty

# relative imports
from . import functions, menus, operators, panels, properties, ui_functions, uilist
from . import config, icon_manager, keymap, log, preferences, shared_data, update
# endregion

__module__ = __package__.split(".")[0]

@persistent
def on_load(dummy= None):
    log.logger.info("Start: Load ActRec Data")
    context = bpy.context
    AR = context.preferences.addons[__module__].preferences
    # load local actions
    if bpy.data.filepath == "":
        context.scene.ar.local = "{}"
    elif context.scene.ar.local == "{}" and context.scene.get('ar_local', None): # load old local action data
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
            log.logger.info("old scene-data couldn't be parsed (%s)" %err)
    functions.load_local_action(AR, json.loads(context.scene.ar.local))
    # update paths
    AR.storage_path
    AR.icon_path
    functions.load(AR)
    icon_manager.load_icons(AR)

    functions.local_runtime_save(AR, None, False)
    functions.global_runtime_save(AR, False)
    functions.category_runtime_save(AR, False)
    log.logger.info("Finished: Load ActRec Data")

# region Registration
def register():
    properties.register()
    menus.register()
    operators.register()
    panels.register()
    uilist.register()
    icon_manager.register()
    update.register()
    keymap.register()
    preferences.register()

    handlers = bpy.app.handlers
    handlers.undo_post.append(functions.category_runtime_load)
    handlers.undo_post.append(functions.global_runtime_load)
    handlers.undo_post.append(functions.local_runtime_load)
    handlers.redo_post.append(functions.category_runtime_load)
    handlers.redo_post.append(functions.global_runtime_load)
    handlers.redo_post.append(functions.local_runtime_load)
    handlers.render_init.append(functions.execute_render_init)
    handlers.render_complete.append(functions.execute_render_complete)
    handlers.depsgraph_update_post.append(functions.track_scene)
    handlers.load_post.append(on_load)
    
    bpy.types.Scene.ar = PointerProperty(type= properties.AR_scene_data)
    log.logger.info("Registered Action Recorder")

def unregister():
    properties.unregister()
    menus.unregister()
    operators.unregister()
    panels.unregister()
    uilist.unregister()
    icon_manager.unregister()
    update.unregister()
    keymap.unregister()
    preferences.unregister()
    
    handlers = bpy.app.handlers
    handlers.undo_post.remove(functions.category_runtime_load)
    handlers.undo_post.remove(functions.global_runtime_load)
    handlers.undo_post.remove(functions.local_runtime_load)
    handlers.redo_post.remove(functions.category_runtime_load)
    handlers.redo_post.remove(functions.global_runtime_load)
    handlers.redo_post.remove(functions.local_runtime_load)
    handlers.render_init.remove(functions.execute_render_init)
    handlers.render_complete.remove(functions.execute_render_complete)
    handlers.depsgraph_update_post.remove(functions.track_scene)
    handlers.load_post.remove(on_load)

    del bpy.types.Scene.ar
    log.logger.info("Unregistered Action Recorder")
    log.log_sys.unregister()
# endregion