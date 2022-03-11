# region Imports
# blender modules
import bpy
# endregion

keymaps = {}

# region Registration
def register():
    addon = bpy.context.window_manager.keyconfigs.addon
    if addon:
        km = addon.keymaps.new(name='Screen')
        keymaps['default'] = km
        items = km.keymap_items
        # operators
        items.new("ar.macro_add", 'COMMA', 'PRESS', alt= True)
        items.new("ar.local_play", 'PERIOD', 'PRESS', alt= True)
        items.new("ar.local_selection_up", 'WHEELUPMOUSE', 'PRESS', shift= True, alt= True)
        items.new("ar.local_selection_down", 'WHEELDOWNMOUSE', 'PRESS', shift= True, alt= True)
        # menu
        kmi = items.new("wm.call_menu_pie", 'A', 'PRESS', shift= True, alt= True)
        kmi.properties.name = 'AR_MT_action_pie'

def unregister():
    addon = bpy.context.window_manager.keyconfigs.addon
    if addon:
        for km in keymaps.values():
            addon.keymaps.remove(km)
# endregion