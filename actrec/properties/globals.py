# region Imports
# blender modules
import bpy
from bpy.types import PropertyGroup
from bpy.props import BoolProperty, StringProperty, CollectionProperty, EnumProperty

# relative Imports
from . import shared
# endregion

__module__ = __package__.split(".")[0]

# region PropertyGroups
class AR_global_actions(shared.AR_action, PropertyGroup):
    def get_value(self) -> bool:
        return self.get("selected", False)
    def set_value(self, value: bool) -> None:
        AR = bpy.context.preferences.addons[__module__].preferences
        selected_ids = list(AR.get("global_actions.selected_ids", []))
        if len(selected_ids) > 1:
            value = True
        if value:
            ctrl_value = bpy.ops.ar.check_ctrl('INVOKE_DEFAULT')
            if selected_ids and ctrl_value == {'CANCELLED'}:
                AR["global_actions.selected_ids"] = []
                for selected_id in selected_ids:
                    action = AR.global_actions.get(selected_id, None)
                    if action:
                        action.selected = False
                selected_ids.clear()
            selected_ids.append(self.id)
            AR["global_actions.selected_ids"] = selected_ids
            self['selected'] = value
        elif not (self.id in selected_ids):
            self['selected'] = value
    selected : BoolProperty(default= False, set= set_value, get= get_value, description= "Select this Action Button\n use ctrl to select muliple", name = 'Select')

class AR_global_import_action(PropertyGroup):
    def get_use(self):
        return self.get('use', True) and self.get('category.use', True)
    def set_use(self, value):
        if self.get('category.use', True):
            self['use'] = value
    
    label : StringProperty()
    identifier : StringProperty()
    use : BoolProperty(default= True, name= "Import Action", description= "Decide whether to import the action", get= get_use, set= set_use)

class AR_global_import_category(PropertyGroup):
    def get_use(self):
        return self.get("use", True)
    def set_use(self, value):
        self['use'] = value
        for action in self.actions:
            action['category.use'] = value

    label : StringProperty()
    identifier : StringProperty()
    actions : CollectionProperty(type= AR_global_import_action)
    show : BoolProperty(default= True)
    use : BoolProperty(default= True, name= "Import Category", description= "Decide whether to import the category", get= get_use, set= set_use)

class AR_global_export_action(shared.id_system, PropertyGroup):
    def get_use(self):
        return self.get("use", True) and self.get('category.use', True) or self.get('export_all', False)
    def set_use(self, value):
        if self.get('category.use', True) and not self.get('export_all', False):
            self['use'] = value
    
    label : StringProperty()
    use : BoolProperty(default= True, name= "Import Action", description= "Decide whether to export the action", get= get_use, set= set_use)

class AR_global_export_categories(shared.id_system, PropertyGroup):
    def get_use(self):
        return self.get("use", True) or self.get("export_all", False)
    def set_use(self, value):
        if not self.get("export_all", False):
            self['use'] = value
            for action in self.actions:
                action['category.use'] = value

    label : StringProperty()
    actions : CollectionProperty(type= AR_global_export_action)
    show : BoolProperty(default= True)
    use : BoolProperty(default= True, name= "Export Category", description= "Decide whether to export the category", get= get_use, set= set_use)
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