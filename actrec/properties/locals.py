# region Imports
# blender modules
import bpy
from bpy.types import PropertyGroup
from bpy.props import BoolProperty, StringProperty, IntProperty

# relative Imports
from . import shared
# endregion

# region PropertyGroups
class AR_local_actions(shared.AR_action, PropertyGroup):
    def get_active_macro_index(self):
        value = self.get('active_macro_index', 0)
        macors_length = len(self.macros)
        return value if value < macors_length else macors_length - 1
    def set_active_macro_index(self, value):
        macors_length = len(self.macros)
        value = value if value < macors_length else macors_length - 1
        self['active_macro_index'] = value if value >= 0 else macors_length - 1

    active_macro_index : IntProperty(name= "Select", min= 0, get= get_active_macro_index, set= set_active_macro_index)

class AR_local_load_text(PropertyGroup):
    name : StringProperty()
    apply : BoolProperty(default= False)
# endregion

classes = [
    AR_local_actions,
    AR_local_load_text
]

# region Registration
def register():
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)
# endregion