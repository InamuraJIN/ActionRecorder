# region Imports
# blender modules
import bpy
from bpy.types import PropertyGroup
from bpy.props import StringProperty, BoolProperty
# endregion


class AR_macro_multiline(PropertyGroup):
    def get_text(self) -> str:
        """
        default Blender property getter

        Returns:
            str: text of the multiline macro
        """
        return self.get('text', '')

    def set_text(self, value: str) -> None:
        """
        set the text of the multiline macro and update to True

        Args:
            value (str): text for the multiline macro
        """
        self['text'] = value
        self['update'] = True

    def get_update(self) -> bool:
        """
        reset update back to false but the previous value will be passed on

        Returns:
            bool: state of update
        """
        value = self.get('update', False)
        self['update'] = False
        return value
    text: StringProperty(get=get_text, set=set_text)
    update: BoolProperty(get=get_update)


class AR_event_object_name(PropertyGroup):
    name: StringProperty(
        name="Object",
        description="Choose an Object which get select when this Event is played",
        default=""
    )


classes = [
    AR_macro_multiline,
    AR_event_object_name
]

# region Registration


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)
# endregion
