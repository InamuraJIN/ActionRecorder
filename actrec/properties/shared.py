# region Imports
# external modules
import uuid

# blender modules
import bpy
from bpy.types import PropertyGroup
from bpy.props import StringProperty, IntProperty, CollectionProperty, BoolProperty

# relative imports
from .. import shared_data, functions
# endregion

__module__ = __package__.split(".")[0]

# region PropertyGroups
class id_system: 
    def get_id(self):
        self['name'] = self.get('name', uuid.uuid1().hex)
        return self['name']
    def set_id(self, value: str):
        try:
            self['name'] = uuid.UUID(value).hex
        except ValueError as err:
            raise ValueError("%s with %s" %(err, value))

    name : StringProperty(get= get_id) # id and name are the same, because CollectionProperty use property 'name' as key
    id : StringProperty(get= get_id, set= set_id)   # create id by calling get-function of id

class alert_system:
    def get_alert(self):
        return self.get('alert', False)
    def set_alert(self, value):
        self['alert'] = value
        if value:
            def reset():
                self['alert'] = False
            bpy.app.timers.register(reset, first_interval= 1, persistent= True)
    def update_alert(self, context):
        if hasattr(context, 'area') and context.area:
            context.area.tag_redraw()

    alert : BoolProperty(default= False, description= "Internal use", get= get_alert, set= set_alert, update= update_alert)

class AR_macro(id_system, alert_system, PropertyGroup):
    def get_active(self):
        return self.get('active', True) and self.is_available
    def set_active(self, value):
        if self.is_available:
            context = bpy.context
            AR = context.preferences.addons[__module__].preferences
            if not AR.local_record_macros:
                if self.get('active', True) != value:
                    functions.local_runtime_save(AR, context.scene)
                self['active'] = value
    def get_command(self):
        return self.get("command", "")
    def set_command(self, value):
        res = functions.update_command(value)
        self['command'] = res if isinstance(res, str) else value
        self['is_available'] = res is not None
    def get_is_available(self):
        return self.get('is_available', True)

    label : StringProperty()
    command : StringProperty(get= get_command, set= set_command)
    active : BoolProperty(default= True, description= 'Toggles Macro on and off.', get= get_active, set= set_active)
    icon : IntProperty(default= 0) #Icon NONE: Global: BLANK1 (101), Local: MESH_PLANE (286)
    is_available : BoolProperty(default= True, get= get_is_available)
    ui_type : StringProperty(default= "")

class AR_action(id_system, alert_system):
    label : StringProperty()
    macros : CollectionProperty(type= AR_macro)
    icon : IntProperty(default= 0) #Icon NONE: Global: BLANK1 (101), Local: MESH_PLANE (286)

class AR_scene_data(PropertyGroup): # as Scene PointerProperty
    local : StringProperty(name= "Local", description= 'Scene Backup-Data of AddonPreference.local_actions (json format)', default= '{}')
    record_undo_end : BoolProperty(name= "Undo End", description= "Used to get the undo step before the record started to compare the undo steps (INTERNAL)", default= False)
# endregion

classes = [
    AR_macro,
    AR_scene_data
]

# region Registration
def register():
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)
# endregion