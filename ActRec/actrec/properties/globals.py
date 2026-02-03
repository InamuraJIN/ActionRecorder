# region Imports
# blender modules
import bpy
from bpy.types import PropertyGroup
from bpy.props import BoolProperty, StringProperty, CollectionProperty, EnumProperty

# relative Imports
from . import shared
from .. import functions
from ..functions.shared import get_preferences
# endregion

# region PropertyGroups

class AR_global_actions(shared.AR_action, PropertyGroup):

    def get_selected(self) -> bool:
        """
        default Blender property getter
        """
        return self.get("selected", False)

    def set_selected(self, value: bool) -> None:
        """
        Updated for Blender 5.0 compatibility.
        Uses a comma-separated string stored in preferences to track multi-selection.
        """
        ActRec_pref = get_preferences(bpy.context)
        
        # BLENDER 5.0 FIX: Retrieve string and convert to list
        raw_ids = ActRec_pref.global_selected_ids_internal
        selected_ids = raw_ids.split(",") if raw_ids else []

        # implementation similar to a UIList (only one selection of all can be active),
        # with extra multi selection by pressing ctrl
        value |= (len(selected_ids) > 1) 
        if not value:
            self['selected'] = False
            # Remove self from the string if it exists
            if self.id in selected_ids:
                selected_ids.remove(self.id)
                ActRec_pref.global_selected_ids_internal = ",".join(selected_ids)
            return

        # uses check_ctrl operator to check for ctrl event
        ctrl_value = bpy.ops.ar.check_ctrl('INVOKE_DEFAULT')
        
        # {'CANCELLED'} == ctrl is not pressed
        if selected_ids and ctrl_value == {'CANCELLED'}:
            # Deselect others
            for selected_id in selected_ids:
                action = ActRec_pref.global_actions.get(selected_id, None)
                if action:
                    action['selected'] = False
            selected_ids.clear()

        if self.id not in selected_ids:
            selected_ids.append(self.id)
        
        # BLENDER 5.0 FIX: Save back as string
        ActRec_pref.global_selected_ids_internal = ",".join(selected_ids)
        self['selected'] = True

    selected: BoolProperty(
        default=False,
        set=set_selected,
        get=get_selected,
        description="Select this Action Button\nuse ctrl to select multiple",
        name='Select'
    )


class AR_global_import_action(PropertyGroup):
    def get_use(self) -> bool:
        return self.get('use', True) and self.get('category.use', True)

    def set_use(self, value: bool) -> None:
        if self.get('category.use', True):
            self['use'] = value

    label: StringProperty()
    identifier: StringProperty()
    use: BoolProperty(
        default=True,
        name="Import Action",
        description="Decide whether to import the action",
        get=get_use,
        set=set_use
    )
    shortcut: StringProperty()


class AR_global_import_category(PropertyGroup):
    def get_use(self) -> bool:
        return self.get("use", True)

    def set_use(self, value: bool) -> None:
        self['use'] = value
        for action in self.actions:
            action['category.use'] = value

    label: StringProperty()
    identifier: StringProperty()
    actions: CollectionProperty(type=AR_global_import_action)
    show: BoolProperty(default=True)
    use: BoolProperty(
        default=True,
        name="Import Category",
        description="Decide whether to import the category",
        get=get_use,
        set=set_use
    )


class AR_global_export_action(shared.Id_based, PropertyGroup):
    def get_use(self) -> bool:
        return self.get("use", True) and self.get('category.use', True) or self.get('export_all', False)

    def set_use(self, value: bool) -> None:
        if self.get('category.use', True) and not self.get('export_all', False):
            self['use'] = value

    label: StringProperty()
    use: BoolProperty(
        default=True,
        name="Export Action",
        description="Decide whether to export the action",
        get=get_use,
        set=set_use
    )
    shortcut: StringProperty()


class AR_global_export_categories(shared.Id_based, PropertyGroup):
    def get_use(self) -> bool:
        return self.get("use", True) or self.get("export_all", False)

    def set_use(self, value: bool) -> None:
        if self.get("export_all", False):
            return
        self['use'] = value
        for action in self.actions:
            action['category.use'] = value

    label: StringProperty()
    actions: CollectionProperty(type=AR_global_export_action)
    show: BoolProperty(default=True)
    use: BoolProperty(
        default=True,
        name="Export Category",
        description="Decide whether to export the category",
        get=get_use,
        set=set_use
    )
# endregion

classes = [
    AR_global_actions,
    AR_global_import_action,
    AR_global_import_category,
    AR_global_export_action,
    AR_global_export_categories
]

# region Registration

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)
# endregion