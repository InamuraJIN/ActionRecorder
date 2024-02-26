# region Imports
# blender modules
import bpy
from bpy.types import UIList
# endregion

# region UIList


class AR_UL_macros(UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index) -> None:
        self.use_filter_show = False
        self.use_filter_sort_lock = True
        row = layout.row(align=True)
        row.alert = item.alert
        row.prop(item, 'active', text="")
        ops = row.operator("ar.macro_edit", text=item.label, emboss=False)
        ops.id = item.id
        ops.index = index
# endregion


classes = [
    AR_UL_macros
]

# region Registration


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)
# endregion
