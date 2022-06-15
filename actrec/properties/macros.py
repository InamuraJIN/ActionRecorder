# region Imports
# blender modules
import bpy
from bpy.types import PropertyGroup
from bpy.props import StringProperty, BoolProperty
# endregion

class AR_macro_multiline(PropertyGroup):
    def get_text(self):
        return self.get('text', '')
    def set_text(self, value):
        self['text'] = value
        self['update'] = True
    def get_update(self):
        value = self.get('update', False)
        self['update'] = False
        return value
    text : StringProperty(get= get_text, set= set_text)
    update : BoolProperty(get= get_update)

classes = [
    AR_macro_multiline
]

# region Registration
def register():
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)
# endregion