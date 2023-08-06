# region Imports
# blender modules
import bpy
from bpy.types import PropertyGroup
from bpy.props import BoolProperty, StringProperty, IntProperty, EnumProperty

# relative Imports
from . import shared
from ..functions import get_preferences
from .. import functions
# endregion

# region PropertyGroups


class AR_local_actions(shared.AR_action, PropertyGroup):
    def get_active_macro_index(self) -> int:
        """
        get the active index of the local macro.
        If the index is out of range the last index of all macros is passed on.

        Returns:
            int: macro index
        """
        value = self.get('active_macro_index', 0)
        macros_length = len(self.macros)
        return value if value < macros_length else macros_length - 1

    def set_active_macro_index(self, value: int) -> None:
        """
        sets the active index of the local macro.
        if value is out of range the last index of the macros is passed on.

        Args:
            value (int): index of the active macro
        """
        macros_length = len(self.macros)
        value = value if value < macros_length else macros_length - 1
        self['active_macro_index'] = value if value >= 0 else macros_length - 1

    active_macro_index: IntProperty(
        name="Select",
        min=0,
        get=get_active_macro_index,
        set=set_active_macro_index
    )


class AR_local_load_text(PropertyGroup):
    name: StringProperty()
    apply: BoolProperty(default=False)
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
