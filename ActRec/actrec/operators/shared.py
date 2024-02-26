# region Imports
# blender modules
import bpy
from bpy.types import Operator, Context, Event
from bpy.props import StringProperty, IntProperty
# endregion


# region Operators


class AR_OT_check_ctrl(Operator):
    bl_idname = "ar.check_ctrl"
    bl_label = "Check Ctrl"
    bl_options = {'INTERNAL'}

    def invoke(self, context: Context, event: Event) -> set[str]:
        if event.ctrl:
            return {"FINISHED"}
        return {"CANCELLED"}

    def execute(self, context: Context) -> set[str]:
        return {"FINISHED"}


class Id_based(Operator):
    id: StringProperty(name="id", description="id of the action (1. indicator)")
    index: IntProperty(name="index", description="index of the action (2. indicator)", default=-1)

    def clear(self) -> None:
        self.id = ""
        self.index = -1


class AR_OT_copy_text(Operator):
    bl_idname = "ar.copy_text"
    bl_label = "Copy Text"
    bl_description = "Loads the given text in the clipboard"
    bl_options = {"INTERNAL"}

    text: StringProperty(name="copy text", description="Text to copy to clipboard")

    @classmethod
    def poll(cls, context: Context) -> bool:
        return context.window_manager is not None

    def execute(self, context: Context) -> set[str]:
        context.window_manager.clipboard = self.text
        return {"FINISHED"}

# endregion


classes = [
    AR_OT_check_ctrl,
    AR_OT_copy_text
]

# region Registration


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)
# endregion
