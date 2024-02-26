# region Imports
# blender modules
import bpy
from bpy.types import UIList
# endregion

# region UIList


class AR_UL_locals(UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index) -> None:
        self.use_filter_show = False
        self.use_filter_sort_lock = True
        row = layout.row(align=True)
        row.alert = item.alert
        ops = row.operator(
            "ar.local_icon",
            text="",
            icon_value=item.icon if item.icon else 286,
            emboss=False
        )
        ops.id = item.id
        ops.index = index
        col = row.column()
        col.ui_units_x = 0.5
        row.prop(item, 'label', text='', emboss=False)
        row.prop(item, 'execution_mode', text="", icon_only=True)
# endregion


classes = [
    AR_UL_locals
]

# region Registration


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)
# endregion
