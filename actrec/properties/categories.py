# region Imports
# blender modules
import bpy
from bpy.types import PropertyGroup
from bpy.props import BoolProperty, StringProperty, CollectionProperty

# relative imports
from . import shared
# endregion

__module__ = __package__.split(".")[0]

# region PropertyGroups
class AR_category_modes(PropertyGroup):
    def get_name(self):
        self['name'] = self.type
        return self['name']

    name : StringProperty(get= get_name)
    type : StringProperty()

class AR_category_areas(PropertyGroup):
    def get_name(self):
        self['name'] = self.type
        return self['name']

    name : StringProperty(get= get_name)
    type : StringProperty()
    modes : CollectionProperty(type= AR_category_modes)

class AR_category_actions(shared.id_system, PropertyGroup): # holds id's of actions
    pass

class AR_categories(shared.id_system, PropertyGroup):
    def get_selected(self) -> bool:
        return self.get("selected", False)
    def set_selected(self, value: bool) -> None:
        AR = bpy.context.preferences.addons[__module__].preferences
        selected_id = AR.get("categories.selected_id", "")
        if value:
            AR["categories.selected_id"] = self.id
            self['selected'] = value
            category = AR.categories.get(selected_id, None)
            if category:
                category.selected = False
        elif selected_id != self.id:
            self['selected'] = value

    label : StringProperty()
    selected : BoolProperty(description= 'Select this Category', name= 'Select', get= get_selected, set= set_selected)
    actions : CollectionProperty(type= AR_category_actions)
    areas : CollectionProperty(type= AR_category_areas)
# endregion

classes = [
    AR_category_modes,
    AR_category_areas,
    AR_category_actions,
    AR_categories
]

# region Registration
def register():
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)
# endregion