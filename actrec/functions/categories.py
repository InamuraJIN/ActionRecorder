# region Imports
# external modules
import json
import os
from typing import Optional

# blender modules
import bpy
from bpy.app.handlers import persistent

# relative imports
from . import globals, shared
from .. import shared_data
# endregion

__module__ = __package__.split(".")[0]

# region functions
def read_category_visbility(AR, id) -> Optional[list]:
    """return None on Fail, dict on Successes"""
    visibility = []
    category = AR.categories.get(id, None)
    if category:
        for area in category.areas:
            for mode in area.modes:
                visibility.append((area.type, mode.type))
            if len(area.modes) == 0:
                visibility.append((area.type, 'all'))
        return visibility

def category_runtime_save(AR, use_autosave: bool = True) -> None:
    """includes autosave"""
    shared_data.categories_temp = shared.property_to_python(AR.categories)
    if use_autosave and AR.autosave:
        globals.save(AR)

@persistent
def category_runtime_load(dummy = None):
    AR = bpy.context.preferences.addons[__module__].preferences
    AR.categories.clear()
    for category in shared_data.categories_temp:
        shared.add_data_to_collection(AR.categories, category)

def get_category_id(AR, id, index):
    if AR.categories.find(id) == -1:
        if index >= 0 and len(AR.categories) > index:
            return AR.categories[index].id
        else:
            return AR.selected_category
    else:
        return id
# endregion