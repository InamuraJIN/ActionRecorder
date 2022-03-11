# region Imports
# externals modules
from contextlib import suppress

# blender modules
import bpy
from bpy.types import Panel

# relative imports
from . import globals
from .. import panels
# endregion

__module__ = __package__.split(".")[0]

classes = []
space_mode_attribute = {
    'IMAGE_EDITOR': 'ui_mode',
    'NODE_EDITOR': 'texture_type',
    'SEQUENCE_EDITOR': 'view_type',
    'CLIP_EDITOR': 'mode',
    'DOPESHEET_EDITOR': 'ui_mode'
}

# region Panel
def register_category(AR, index):
    register_unregister_category(index)

def unregister_category(AR, index):
    register_unregister_category(index, register = False)

def category_visible(AR, context, category):
    if AR.show_all_categories or not len(category.areas):
        return True
    area_type = context.area.ui_type
    area_space = context.area.type
    for area in category.areas:
        if area.type == area_type:
            if len(area.modes) == 0:
                return True
            if area_space == 'VIEW_3D':
                mode = ""
                if context.object:
                    mode = context.object.mode
            else:
                mode = getattr(context.space_data, space_mode_attribute[area_space])
            return mode in set(mode.type for mode in area.modes)
    return False

def get_visible_categories(AR, context):
    return [category for category in AR.categories if category_visible(AR, context, category)]

def register_unregister_category(index, space_types = panels.ui_space_types, register = True): #Register/Unregister one Category
    for spaceType in space_types:
        class AR_PT_category(Panel):
            bl_space_type = spaceType
            bl_region_type = 'UI'
            bl_category = 'Action Recorder'
            bl_label = ' '
            bl_idname = "AR_PT_category_%s_%s" %(index, spaceType)
            bl_parent_id = "AR_PT_global_%s" % spaceType
            bl_order = index + 1
            bl_options = {"INSTANCED", "DEFAULT_CLOSED"}

            @classmethod
            def poll(self, context):
                AR = context.preferences.addons[__module__].preferences
                index = int(self.bl_idname.split("_")[3])
                return index < len(get_visible_categories(AR, context))

            def draw_header(self, context):
                AR = context.preferences.addons[__module__].preferences
                index = int(self.bl_idname.split("_")[3])
                category = get_visible_categories(AR, context)[index]
                layout = self.layout
                row = layout.row()
                row.prop(category, 'selected', text= '', icon= 'LAYER_ACTIVE' if category.selected else 'LAYER_USED', emboss= False)
                row.label(text= category.label)

            def draw(self, context):
                AR = context.preferences.addons[__module__].preferences
                index = int(self.bl_idname.split("_")[3])
                category = get_visible_categories(AR, context)[index]
                layout = self.layout
                col = layout.column()
                for id in [x.id for x in category.actions]:
                    globals.draw_global_action(col, AR, id)
        AR_PT_category.__name__ = "AR_PT_category_%s_%s" %(index, spaceType)
        if register:
            bpy.utils.register_class(AR_PT_category)
            classes.append(AR_PT_category)
        else:
            with suppress(Exception):
                if hasattr(bpy.types, AR_PT_category.__name__):
                    panel = getattr(bpy.types, AR_PT_category.__name__)
                    bpy.utils.unregister_class(panel)
                    classes.remove(panel)
    AR = bpy.context.preferences.addons[__module__].preferences
    if AR.selected_category == '' and len(AR.categories):
        AR.categories[0].selected = True
# endregion