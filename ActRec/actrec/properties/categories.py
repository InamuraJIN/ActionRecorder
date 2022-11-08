# region Imports
# blender modules
import bpy
from bpy.types import PropertyGroup
from bpy.props import BoolProperty, StringProperty, CollectionProperty

# relative imports
from . import shared
from ..functions.shared import get_preferences
# endregion

# region PropertyGroups


class AR_category_modes(PropertyGroup):
    def get_name(self) -> str:
        """
        getter of name, same as type

        Returns:
            str: type of the category
        """
        # self['name'] needed because of Blender default implementation
        self['name'] = self.type
        return self['name']
    # needed for easier access to the mode of the category
    name: StringProperty(get=get_name)
    type: StringProperty()


class AR_category_areas(PropertyGroup):
    def get_name(self) -> str:
        """
        getter of name, same as type

        Returns:
            str: type of the category
        """
        # self['name'] needed because of Blender default implementation
        self['name'] = self.type
        return self['name']

    # needed for easier access to the types of the category
    name: StringProperty(get=get_name)
    type: StringProperty()
    modes: CollectionProperty(type=AR_category_modes)


class AR_category_actions(shared.Id_based, PropertyGroup):  # holds id's of actions
    pass


class AR_category(shared.Id_based, PropertyGroup):
    def get_selected(self) -> bool:
        """
        default Blender property getter

        Returns:
            bool: selection state of the category
        """
        return self.get("selected", False)

    def set_selected(self, value: bool):
        """
        set the category as active, False will not change anything

        Args:
            value (bool): state of category
        """
        ActRec_pref = get_preferences(bpy.context)
        selected_id = ActRec_pref.get("categories.selected_id", "")
        # implementation similar to a UIList (only one selection of all can be active)
        if value:
            ActRec_pref["categories.selected_id"] = self.id
            self['selected'] = value
            category = ActRec_pref.categories.get(selected_id, None)
            if category:
                category.selected = False
        elif selected_id != self.id:
            self['selected'] = value

    label: StringProperty()
    selected: BoolProperty(description='Select this Category',
                           name='Select', get=get_selected, set=set_selected)
    actions: CollectionProperty(type=AR_category_actions)
    areas: CollectionProperty(type=AR_category_areas)
# endregion


classes = [
    AR_category_modes,
    AR_category_areas,
    AR_category_actions,
    AR_category
]

# region Registration


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)
# endregion
