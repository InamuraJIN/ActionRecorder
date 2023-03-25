# region Imports
# externals modules
from contextlib import suppress

# blender modules
import bpy
from bpy.types import Panel, Menu

# relative imports
from . import globals
from .. import panels
from ..functions.shared import get_preferences
from ..log import logger
# endregion

classes = []
space_mode_attribute = {
    'IMAGE_EDITOR': 'ui_mode',
    'NODE_EDITOR': 'texture_type',
    'SEQUENCE_EDITOR': 'view_type',
    'CLIP_EDITOR': 'mode',
    'DOPESHEET_EDITOR': 'ui_mode'
}


def category_visible(ActRec_pref: bpy.types.AddonPreferences,
                     context: bpy.types.Context,
                     category: 'AR_category') -> bool:
    """
    checks if category is visible based on the given context

    Args:
        ActRec_pref (bpy.types.AddonPreferences): preferences of this addon
        context (bpy.types.Context): active blender context
        category (AR_category): category to check

    Returns:
        bool: true if category is visible
    """
    # REFACTOR indentation
    if ActRec_pref.show_all_categories or not len(category.areas):
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
                mode = getattr(context.space_data,
                               space_mode_attribute[area_space])
            return mode in set(mode.type for mode in area.modes)
    return False


def get_visible_categories(ActRec_pref: bpy.types.AddonPreferences, context: bpy.types.Context) -> list['AR_category']:
    """
    get list of all visible categories

    Args:
        ActRec_pref (bpy.types.AddonPreferences): preferences of this addon
        context (bpy.types.Context): active blender context

    Returns:
        list[AR_category]: list of all visible categories
    """
    return [category for category in ActRec_pref.categories if category_visible(ActRec_pref, context, category)]


def register_category(ActRec_pref: bpy.types.AddonPreferences, index: int):
    """
    register a category based on the index in all spaces (panels.ui_space_types)

    Args:
        ActRec_pref (bpy.types.AddonPreferences): preferences of this addon
        index (int): index of category to register
    """
    register_unregister_category(index)


def unregister_category(ActRec_pref: bpy.types.AddonPreferences, index: int):
    """
    unregister a category based on the index in all spaces (panels.ui_space_types)

    Args:
        ActRec_pref (bpy.types.AddonPreferences): preferences of this addon
        index (int): index of category to unregister
    """
    register_unregister_category(index, register=False)


def register_unregister_category(index: int, space_types: list[str] = panels.ui_space_types, register: bool = True):
    """
    register or unregister a single category in all given spaces

    Args:
        index (int): index of the category
        space_types (list[str], optional): list of spaces to unregister the category from.
        Defaults to panels.ui_space_types.
        register (bool, optional): true: register category; false: unregister category. Defaults to True.
    """
    for spaceType in space_types:
        class AR_PT_category(Panel):
            bl_space_type = spaceType
            bl_region_type = 'UI'
            bl_category = 'Action Recorder'
            bl_label = ' '
            bl_idname = "AR_PT_category_%s_%s" % (index, spaceType)
            bl_parent_id = "AR_PT_global_%s" % spaceType
            bl_order = index + 1
            bl_options = {"INSTANCED", "DEFAULT_CLOSED"}

            @classmethod
            def poll(self, context):
                ActRec_pref = get_preferences(context)
                index = int(self.bl_idname.split("_")[3])
                return index < len(get_visible_categories(ActRec_pref, context))

            def draw_header(self, context):
                ActRec_pref = get_preferences(context)
                index = int(self.bl_idname.split("_")[3])
                category = get_visible_categories(ActRec_pref, context)[index]
                layout = self.layout
                row = layout.row()
                row.prop(category, 'selected', text='',
                         icon='LAYER_ACTIVE' if category.selected else 'LAYER_USED', emboss=False)
                row.label(text=category.label)

            def draw(self, context):
                ActRec_pref = get_preferences(context)
                index = int(self.bl_idname.split("_")[3])
                category = get_visible_categories(ActRec_pref, context)[index]
                layout = self.layout
                col = layout.column()
                for id in [x.id for x in category.actions]:
                    globals.draw_global_action(col, ActRec_pref, id)
        AR_PT_category.__name__ = "AR_PT_category_%s_%s" % (index, spaceType)

        if register:
            try:
                bpy.utils.register_class(AR_PT_category)
                classes.append(AR_PT_category)
            except RuntimeError as err:
                logger.error("Couldn't register Panel :(\n(%s)", err)
        else:
            with suppress(Exception):
                if hasattr(bpy.types, AR_PT_category.__name__):
                    panel = getattr(bpy.types, AR_PT_category.__name__)
                    bpy.utils.unregister_class(panel)
                    classes.remove(panel)

    class AR_MT_category(Menu):
        bl_idname = "AR_MT_category_%s" % index
        bl_label = "Category"

        @classmethod
        def poll(self, context):
            ActRec_pref = get_preferences(context)
            index = int(self.bl_idname.split("_")[3])
            return index < len(get_visible_categories(ActRec_pref, context))

        def draw(self, context):
            ActRec_pref = get_preferences(context)
            index = int(self.bl_idname.split("_")[3])
            category = get_visible_categories(ActRec_pref, context)[index]
            layout = self.layout
            col = layout.column()
            for id in [x.id for x in category.actions]:
                globals.draw_simple_global_action(col, ActRec_pref, id)
    AR_MT_category.__name__ = "AR_MT_category_%s" % index

    if register:
        try:
            bpy.utils.register_class(AR_MT_category)
            classes.append(AR_MT_category)
        except RuntimeError as err:
            logger.error("Couldn't register Menu :(\n(%s)", err)
    else:
        with suppress(Exception):
            if hasattr(bpy.types, AR_MT_category.__name__):
                menu = getattr(bpy.types, AR_MT_category.__name__)
                bpy.utils.unregister_class(menu)
                classes.remove(menu)

    ActRec_pref = get_preferences(bpy.context)
    if ActRec_pref.selected_category == '' and len(ActRec_pref.categories):
        ActRec_pref.categories[0].selected = True


def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)
    classes.clear()
