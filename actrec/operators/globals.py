# region Imports
# external modules
import os
from typing import Union
import zipfile
from collections import defaultdict
import uuid
import json

# blender modules
import bpy
from bpy.types import Operator
from bpy.props import StringProperty, BoolProperty, EnumProperty, CollectionProperty
from bpy_extras.io_utils import ImportHelper, ExportHelper

# relative imports
from .. import functions, properties, icon_manager, ui_functions
from . import shared
# endregion

__module__ = __package__.split(".")[0]

# region Operators
class AR_OT_gloabal_recategorize_action(shared.id_based, Operator):
    bl_idname = "ar.global_recategorize_action"
    bl_label = "Recategoize Action Button"
    bl_description = "Reallocate the selected Action to another Category"

    @classmethod
    def poll(cls, context):
        AR = context.preferences.addons[__module__].preferences
        return len(AR.global_actions) and len(AR.get("global_actions.selected_ids", []))

    def invoke(self, context: bpy.context, event: bpy.types.Event):
        return context.window_manager.invoke_props_dialog(self)

    def execute(self, context: bpy.context):
        AR = context.preferences.addons[__module__].preferences
        categories = AR.categories
        ids = functions.get_global_action_ids(AR, self.id, self.index)
        self.clear()
        if all(category.selected for category in categories): 
            return {"CANCELLED"}
        for category in categories:
            if category.selected:
                for id in set(ids).difference(x.id for x in category.actions):
                    new_action = category.actions.add()
                    new_action.id = id
            else:
                for id in ids:
                    category.actions.remove(category.actions.find(id))
        functions.global_runtime_save(AR)
        context.area.tag_redraw()
        return {"FINISHED"}

    def draw(self, context):
        AR = context.preferences.addons[__module__].preferences
        categories = AR.categories
        layout = self.layout
        for category in categories:
            layout.prop(category, 'selected', text= category.label)

class AR_OT_global_import(Operator, ImportHelper):
    bl_idname = "ar.global_import"
    bl_label = "Import"
    bl_description = "Import the Action file into the storage"

    filter_glob: StringProperty(default='*.zip;*.json', options={'HIDDEN'})

    category : StringProperty(default= "Imports")
    mode : EnumProperty(name= 'Mode', items= [("add","Add","Add to the current Global data"), ("overwrite", "Overwrite", "Remove the current Global data")])

    def get_macros_from_file(self, context, zip_file: zipfile.ZipFile, path: str) -> list:
        lines =  zip_file.read(path).decode(encoding= "utf-8").splitlines()
        macros = []
        for line in lines:
            data = {'id' : uuid.uuid1().hex, 'active' : True, 'icon': 0}
            data['command'] = line
            label = functions.get_name_of_command(context, line)
            data['label'] = label if isinstance(label, str) else line
            macros.append(data)
        return macros

    def execute(self, context):
        AR = context.preferences.addons[__module__].preferences

        if not len(AR.import_settings) and bpy.ops.ar.global_import_settings('EXEC_DEFAULT', filepath= self.filepath, from_operator= True) == {'CANCELLED'}:
            self.report({'ERROR'}, "Selected file is incompatible")
            return {'CANCELLED'}

        if AR.import_extension == ".zip" or AR.import_extension == ".json":

            if self.mode == "overwrite":
                for i in range(len(AR.categories)):
                    ui_functions.unregister_category(AR, i)
                AR.global_actions.clear()
                AR.categories.clear()

            if AR.import_extension == ".zip":
                data = defaultdict(list)
                current_actions_length = 0
                zip_file = zipfile.ZipFile(self.filepath, mode= 'r')
                for category in AR.import_settings:
                    if category.use and any(action.use for action in category.actions):
                        actions = list(filter(lambda x: x.use, category.actions))
                        category_actions = [
                            {
                            'id' : uuid.uuid1().hex,
                            'label' : action.label,
                            'macros' : self.get_macros_from_file(context, zip_file, action.identifier),
                            'icon' : int(action.identifier.split("~")[-1].split(".")[0])
                            }for action in actions
                        ]
                        data['categories'].append({
                            'id' : uuid.uuid1().hex,
                            'label' : category.label,
                            'start' : current_actions_length,
                            'length' : len(actions),
                            'actions' : [{"id": action['id']} for action in category_actions]
                        })
                        data['actions'] += category_actions
                functions.import_global_from_dict(AR, data)
            elif AR.import_extension == ".json":
                with open(self.filepath, 'r', encoding= 'utf-8') as file:
                    data = json.loads(file.read())
                category_ids = set(category.identifier for category in AR.import_settings)
                action_ids = []
                for category in AR.import_settings:
                    action_ids += [action.identifier for action in category.actions]
                action_ids = set(action_ids)

                data['categories'] = [category for category in data['categories'] if category['id'] not in category_ids]
                data['actions'] = [action for action in data['actions'] if action['id'] not in action_ids]
                functions.import_global_from_dict(AR, data)
        else:
            self.report({'ERROR'}, "Select a .json or .zip file {%s}" %self.filepath)
        AR = context.preferences.addons[__module__].preferences
        AR.import_settings.clear()
        functions.category_runtime_save(AR)
        functions.global_runtime_save(AR, False)
        context.area.tag_redraw()
        return {"FINISHED"}

    def draw(self, context):
        AR = context.preferences.addons[__module__].preferences
        layout = self.layout
        layout.operator("ar.global_import_settings", text= "Load Importsettings").filepath = self.filepath
        col = layout.column(align= True)
        row = col.row(align=True)
        row.prop(self, 'mode', expand= True)
        for category in AR.import_settings:
            box = col.box()
            sub_col = box.column()
            row = sub_col.row()
            if category.show:
                row.prop(category, 'show', icon="TRIA_DOWN", text= "", emboss= False)
            else:
                row.prop(category, 'show', icon="TRIA_RIGHT", text= "", emboss= False)
            row.prop(category, 'use', text= "")
            row.label(text= category.label)
            if category.show:
                sub_col = box.column()
                for action in category.actions:
                    row = sub_col.row()
                    row.prop(action, 'use', text= "")
                    row.label(text= action.label)
        
    def cancel(self, context):
        AR = context.preferences.addons[__module__].preferences
        AR.import_settings.clear()

class AR_OT_global_import_settings(Operator):
    bl_idname = "ar.global_import_settings"
    bl_label = "Load Importsettings"
    bl_description = "Loads the select file to change the importsettings"

    filepath : StringProperty()
    from_operator : BoolProperty(default= False)

    def valid_file(self, file: str) -> bool:
        if file.count('~') == 2:
            index, name, icon = ".".join(file.split(".")[:-1]).split("~") # remove .py from filename and split apart
            return index.isdigit() and (icon.isupper() or icon.isdigit())
        return False
    
    def valid_directory(self, directroy: str) -> bool:
        if directroy.count('~') == 1:
            index, name = directroy.split('~')
            return index.isdigit()
        return False

    def import_sorted_zip(self, filepath: str) -> Union[dict, str]:
        with zipfile.ZipFile(filepath, 'r') as zip_file:
            filepaths = sorted(zip_file.namelist())
        categories = defaultdict(list)

        for file in filter(lambda x: x.endswith(".py"), filepaths):
            split = file.split("/")
            if len(split) < 2:
                return file
            category = split[-2]
            action_file = split[-1]
            if not (self.valid_directory(category) and self.valid_file(action_file)):
                return file
            categories[category].append(file)
        for item in categories.values():
            item.sort(key= lambda x: int(x.split("/")[-1].split('~')[0]))
        return categories

    def execute(self, context):
        AR = context.preferences.addons[__module__].preferences
        AR.import_settings.clear()
        
        if os.path.exists(self.filepath):
            if self.filepath.endswith(".zip"):
                AR.import_extension = ".zip"
                categories_paths = self.import_sorted_zip(self.filepath)
                if isinstance(categories_paths, str):
                    if not self.from_operator:
                        self.report({'ERROR'}, "The selected file is not compatible (%s)" %categories_paths)
                    return {'CANCELLED'}
                for key, item in sorted(categories_paths.items(), key= lambda x: int(x[0].split('~')[0])):
                    new_category = AR.import_settings.add()
                    new_category.identifier = key
                    new_category.label = key.split('~')[1]
                    for file in item:
                        new_action = new_category.actions.add()
                        new_action.identifier = file
                        new_action.label = file.split("/")[-1].split('~')[1]
                return {"FINISHED"}
            elif self.filepath.endswith(".json"):
                AR.import_extension = ".json"
                with open(self.filepath, 'r') as file:
                    data = json.loads(file.read())
                actions = {action.id : action for action in data['actions']}
                for category in data['categories']:
                    new_category = AR.import_settings.add()
                    new_category.identifier = category['id']
                    new_category.label = category['label']
                    for id in category['actions']:
                        action = actions[id]
                        new_action = new_category.actions.add()
                        new_action.identifier = action['id']
                        new_action.label = action['label']
        if not self.from_operator:
            self.report({'ERROR'}, "You need to select a .json or .zip file")
        self.from_operator = False
        return {'CANCELLED'}

class AR_OT_global_export(Operator, ExportHelper):
    bl_idname = "ar.global_export"
    bl_label = "Export"
    bl_description = "Export the Action file as a .json file"

    def get_export_all(self):
        return self.get("export_all", False)
    def set_export_all(self, value):
        self["export_all"] = value
        for category in self.export_categories:
            category["export_all"] = value
            for action in category.actions:
                action["export_all"] = value

    filter_glob: StringProperty(default= '*.json', options= {'HIDDEN'})
    filename_ext = ".json"
    
    filepath: StringProperty(name="File Path", description="Filepath used for exporting the file", maxlen=1024, subtype='FILE_PATH', default= "ActionRecorderButtons")

    export_all : BoolProperty(name= "All", description= "Export all category", get= get_export_all, set= set_export_all)
    export_categories : CollectionProperty(type= properties.AR_global_export_categories)

    @classmethod
    def poll(cls, context):
        AR = context.preferences.addons[__module__].preferences
        return len(AR.global_actions)

    def invoke(self, context, event):
        AR = context.preferences.addons[__module__].preferences
        for category in AR.categories:
            new_category = self.export_categories.add()
            new_category.id = category.id
            new_category.label = category.label
            for id_action in category.actions:
                action = AR.global_actions.get(id_action.id, None)
                if action is None:
                    category.actions.remove(category.actions.find(id_action.id))
                    continue
                new_action = new_category.actions.add()
                new_action.id = action.id
                new_action.label = action.label
        return ExportHelper.invoke(self, context, event)

    def execute(self, context):
        AR = context.preferences.addons[__module__].preferences
        if not os.path.exists(os.path.dirname(self.filepath)):
            self.report({'ERROR', "Directory doesn't exist"})
            return {'CANCELLED'}
        if not self.filepath.endswith(".json"):
            self.report({'ERROR', "File has to be a json file"})
            return {'CANCELLED'}
        data = defaultdict(list)
        export_category_ids = set(category.id for category in self.export_categories if category.use)
        export_action_ids = []
        for category in self.export_categories:
            export_action_ids += set(action.id for action in category.actions if action.use)
        for category in AR.categories:
            if category.id in export_category_ids:
                data['categories'] = functions.property_to_python(AR.categories, exclude= ["name", "selected", "actions.name", "areas.name", "areas.modes.name"])
        for action in AR.global_actions:
            if action.id in export_action_ids:
                data['actions'] = functions.property_to_python(AR.global_actions, exclude= ["name", "selected", "alert", "macros.name", "macros.is_available", "macros.alert"])
        with open(self.filepath, 'w', encoding= 'utf-8') as file:
            json.dump(data, file, ensure_ascii= False, indent= 2)
        self.cancel(context)
        return {'FINISHED'}
    
    def cancel(self, context):
        self.export_categories.clear()
        self.all_categories = True

    def draw(self, context):
        layout = self.layout
        layout.prop(self, 'export_all', text= "All")
        col = layout.column(align= True)
        for category in self.export_categories:
            box = col.box()
            col2 = box.column()
            row = col2.row()
            row.prop(category, 'show', icon="TRIA_DOWN" if category.show else "TRIA_RIGHT", text= "", emboss= False)
            row.label(text= category.label)
            row.prop(category, 'use', text= "")
            if category.show:
                col2 = box.column(align= False)
                for action in category.actions:
                    subrow = col2.row()
                    subrow.prop(action, 'use' , text= '') 
                    subrow.label(text= action.label)

class AR_OT_global_save(Operator):
    bl_idname = "ar.global_save"
    bl_label = "Save"
    bl_description = "Save all Global Actions to the Storage"

    def execute(self, context):
        functions.save(context.preferences.addons[__module__].preferences)
        return {"FINISHED"}

class AR_OT_global_load(Operator):
    bl_idname = "ar.global_load"
    bl_label = "Load"
    bl_description = "Load all Actions from the Storage"

    def execute(self, context):
        AR = context.preferences.addons[__module__].preferences
        functions.load(AR)
        functions.category_runtime_save(AR, False)
        functions.global_runtime_save(AR, False)
        context.area.tag_redraw()
        return {"FINISHED"}

class AR_OT_global_to_local(shared.id_based, Operator):
    bl_idname = "ar.global_to_local"
    bl_label = "Global Action to Local"
    bl_description = "Transfer the selected Action to Local-actions"

    @classmethod
    def poll(cls, context):
        AR = context.preferences.addons[__module__].preferences
        return len(AR.global_actions) and len(AR.get("global_actions.selected_ids", []))

    def global_to_local(self, AR, action) -> None:
        id = uuid.uuid1().hex if action.id in set(x.id for x in AR.local_actions) else action.id
        data = functions.property_to_python(action, exclude= ["name", "alert", "macros.name", "macros.alert", "macros.is_available"])
        data["id"] = id
        functions.add_data_to_collection(AR.local_actions, data)
        AR.active_local_action_index = len(AR.local_actions)

    def execute(self, context):
        AR = context.preferences.addons[__module__].preferences
        for id in functions.get_global_action_ids(AR, self.id, self.index):
            self.global_to_local(AR, AR.global_actions[id])
            if AR.global_to_local_mode == 'move':
                AR.global_actions.remove(AR.global_actions.find(id))
                for category in AR.categories:
                    category.actions.remove(category.actions.find(id))
        functions.category_runtime_save(AR)
        functions.global_runtime_save(AR, False)
        context.area.tag_redraw()
        self.clear()
        return {"FINISHED"}

class AR_OT_global_remove(shared.id_based, Operator):
    bl_idname = "ar.global_remove"
    bl_label = "Remove Action"
    bl_description = "Remove the selected actions"

    @classmethod
    def poll(cls, context):
        AR = context.preferences.addons[__module__].preferences
        return len(AR.global_actions) and len(AR.get("global_actions.selected_ids", []))

    def execute(self, context):
        AR = context.preferences.addons[__module__].preferences
        for id in functions.get_global_action_ids(AR, self.id, self.index):
            AR.global_actions.remove(AR.global_actions.find(id))
            for category in AR.categories:
                category.actions.remove(category.actions.find(id))
        functions.category_runtime_save(AR)
        functions.global_runtime_save(AR, False)
        context.area.tag_redraw()
        self.clear()
        return {"FINISHED"}

    def invoke(self, context, event):
        return context.window_manager.invoke_confirm(self, event)

class AR_OT_global_move_up(shared.id_based, Operator):
    bl_idname = "ar.global_move_up"
    bl_label = "Move Action Up"
    bl_description = "Move the selected actions Up"

    @classmethod
    def poll(cls, context):
        AR = context.preferences.addons[__module__].preferences
        return len(AR.global_actions) and len(AR.get("global_actions.selected_ids", []))

    def execute(self, context):
        AR = context.preferences.addons[__module__].preferences
        ids = set(functions.get_global_action_ids(AR, self.id, self.index))
        for category in AR.categories:
            for id_action in category.actions:
                if id_action.id in ids:
                    index = category.actions.find(id_action.id)
                    category.actions.move(index, index - 1)
        functions.category_runtime_save(AR)
        context.area.tag_redraw()
        self.clear()
        return {"FINISHED"}

class AR_OT_global_move_down(shared.id_based, Operator):
    bl_idname = "ar.global_move_down"
    bl_label = "Move Action Down"
    bl_description = "Move the selected actions Down"

    @classmethod
    def poll(cls, context):
        AR = context.preferences.addons[__module__].preferences
        return len(AR.global_actions) and len(AR.get("global_actions.selected_ids", []))

    def execute(self, context):
        AR = context.preferences.addons[__module__].preferences
        ids = set(functions.get_global_action_ids(AR, self.id, self.index))
        for category in AR.categories:
            for id_action in reversed(list(category.actions)):
                if id_action.id in ids:
                    index = category.actions.find(id_action.id)
                    category.actions.move(index, index + 1)
        functions.category_runtime_save(AR)
        context.area.tag_redraw()
        self.clear()
        return {"FINISHED"}

class AR_OT_global_rename(shared.id_based, Operator):
    bl_idname = "ar.global_rename"
    bl_label = "Rename Button"
    bl_description = "Rename the selected Button"
    
    label : StringProperty()

    @classmethod
    def poll(cls, context):
        AR = context.preferences.addons[__module__].preferences
        return len(AR.global_actions) and len(AR.get("global_actions.selected_ids", [])) == 1

    def execute(self, context):
        AR = context.preferences.addons[__module__].preferences
        ids = functions.get_global_action_ids(AR, self.id, self.index)
        self.clear()
        label = self.label
        self.label = ""

        if len(ids) == 1:
            id = ids[0]
            action = AR.global_actions.get(id, None)
            if action:
                AR.global_actions[id].label = label
                functions.global_runtime_save(AR)
                context.area.tag_redraw()
                return {"FINISHED"}
        return {'CANCELLED'}

class AR_OT_global_execute_action(shared.id_based, Operator):
    bl_idname = 'ar.global_execute_action'
    bl_label = 'ActRec Action Button'
    bl_description = 'Play this Action Button'
    bl_options = {'UNDO', 'INTERNAL'}

    def execute(self, context):
        AR = context.preferences.addons[__module__].preferences
        id = functions.get_global_action_id(AR, self.id, self.index)
        self.clear()
        if id is None:
            return {'CANCELLED'}
        action = AR.global_actions[id]
        err = functions.play(context.copy(), action.macros, action, 'global_actions')
        if err:
            self.report({'ERROR'}, str(err))
        return{'FINISHED'}

class AR_OT_global_icon(icon_manager.icontable, shared.id_based, Operator):
    bl_idname = "ar.global_icon"

    def invoke(self, context, event):
        AR = context.preferences.addons[__module__].preferences
        id = functions.get_global_action_id(AR, self.id, self.index)
        if id is None:
            self.clear()
            return {'CANCELLED'}
        self.id = id
        if not self.reuse:
            AR.selected_icon = AR.global_actions[id].icon
        self.search = ''
        return context.window_manager.invoke_props_dialog(self, width=1000)

    def execute(self, context):
        AR = context.preferences.addons[__module__].preferences
        AR.global_actions[self.id].icon = AR.selected_icon
        AR.selected_icon = 0 #Icon: NONE
        self.reuse = False
        functions.global_runtime_save(AR)
        bpy.context.area.tag_redraw()
        self.clear()
        return {"FINISHED"}
# endregion

classes = [
    AR_OT_gloabal_recategorize_action,
    AR_OT_global_import,
    AR_OT_global_import_settings,
    AR_OT_global_export,
    AR_OT_global_save,
    AR_OT_global_load,
    AR_OT_global_to_local,
    AR_OT_global_remove,
    AR_OT_global_move_up,
    AR_OT_global_move_down,
    AR_OT_global_rename,
    AR_OT_global_execute_action,
    AR_OT_global_icon
]

# region Registration
def register():
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)
# endregion
