# region Imports
# external modules
import os
from typing import Union
import zipfile
from collections import defaultdict
import uuid
import json
from typing import TYPE_CHECKING

# blender modules
import bpy
from bpy.types import Operator, Context, Event, AddonPreferences, OperatorProperties, PropertyGroup
from bpy.props import StringProperty, BoolProperty, EnumProperty, CollectionProperty
from bpy_extras.io_utils import ImportHelper, ExportHelper

# relative imports
from .. import functions, properties, icon_manager, ui_functions, keymap
from . import shared
from ..functions.shared import get_preferences
from ..log import logger
from ..keymap import keymaps, keymap_items
if TYPE_CHECKING:
    from ..preferences import AR_preferences
    from ..properties.globals import AR_global_actions
else:
    AR_preferences = AddonPreferences
    AR_global_actions = PropertyGroup
# endregion


# region Operators


class AR_OT_global_recategorize_action(shared.Id_based, Operator):
    bl_idname = "ar.global_recategorize_action"
    bl_label = "Recategorize Action Button"
    bl_description = "Reallocate the selected Action to another Category"

    @classmethod
    def poll(cls, context: Context) -> bool:
        ActRec_pref = get_preferences(context)
        return len(ActRec_pref.global_actions) and len(ActRec_pref.get("global_actions.selected_ids", []))

    def invoke(self, context: Context, event: Event) -> set[str]:
        return context.window_manager.invoke_props_dialog(self)

    def execute(self, context: Context) -> set[str]:
        ActRec_pref = get_preferences(context)
        categories = ActRec_pref.categories
        ids = functions.get_global_action_ids(ActRec_pref, self.id, self.index)
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
        if ActRec_pref.autosave:
            functions.save(ActRec_pref)
        context.area.tag_redraw()
        return {"FINISHED"}

    def draw(self, context: Context) -> None:
        ActRec_pref = get_preferences(context)
        categories = ActRec_pref.categories
        layout = self.layout
        for category in categories:
            layout.prop(category, 'selected', text=category.label)


class AR_OT_global_import(Operator, ImportHelper):
    bl_idname = "ar.global_import"
    bl_label = "Import"
    bl_description = "Import the Action file into the storage"

    filter_glob: StringProperty(default='*.zip;*.json', options={'HIDDEN'})

    category: StringProperty(default="Imports")
    mode: EnumProperty(
        name='Mode',
        items=[
            ("add", "Add", "Add to the current Global data"),
            ("overwrite", "Overwrite", "Remove the current Global data")
        ]
    )
    include_keymap: BoolProperty(
        name="Include Shortcuts",
        description="Include the added Shortcuts of the actions",
        default=True
    )

    def get_macros_from_file(self, context: Context, zip_file: zipfile.ZipFile, path: str) -> list:
        """
        Extract macros from the path inside the given zip-file

        Args:
            context (Context): active blender context
            zip_file (zipfile.ZipFile): zip file to extract the macros from
            path (str): path to the file with macros inside the zip file

        Returns:
            list: extracted macros, macros are of type dict
        """
        lines = zip_file.read(path).decode(encoding="utf-8").splitlines()
        macros = []
        for line in lines:
            data = {'id': uuid.uuid1().hex, 'active': True, 'icon': 0}
            data['command'] = line
            label = functions.get_name_of_command(context, line)
            data['label'] = label if isinstance(label, str) else line
            macros.append(data)
        return macros

    def execute(self, context: Context) -> set[str]:
        ActRec_pref = get_preferences(context)

        # Try to load import settings and check if file is valid
        if (not len(ActRec_pref.import_settings)
                and bpy.ops.ar.global_import_settings(
                    'EXEC_DEFAULT',
                    filepath=self.filepath,
                    from_operator=True) == {'CANCELLED'}):
            self.report({'ERROR'}, "Selected file is incompatible")
            return {'CANCELLED'}

        if ActRec_pref.import_extension not in {".zip", ".json"}:
            ActRec_pref.import_settings.clear()
            self.report({'ERROR'}, "Select a .json or .zip file {%s}" % self.filepath)
            return {'CANCELLED'}

        if self.mode == "overwrite":
            for i in range(len(ActRec_pref.categories)):
                ui_functions.unregister_category(ActRec_pref, i)
            ActRec_pref.global_actions.clear()
            ActRec_pref.categories.clear()

        if ActRec_pref.import_extension == ".zip":
            # Only used because old Version used .zip to export and directory and file structure
            # Categories where saved as directories and Actions where saved as files in the specific directory
            data = defaultdict(list)
            zip_file = zipfile.ZipFile(self.filepath, mode='r')
            for category in ActRec_pref.import_settings:
                if category.use and any(action.use for action in category.actions):
                    actions = list(
                        filter(lambda x: x.use, category.actions))
                    category_actions = [
                        {
                            'id': uuid.uuid1().hex,
                            'label': action.label,
                            'macros': self.get_macros_from_file(context, zip_file, action.identifier),
                            'icon': int(action.identifier.split("~")[-1].split(".")[0])
                        }for action in actions
                    ]
                    data['categories'].append({
                        'id': uuid.uuid1().hex,
                        'label': category.label,
                        'actions': [{"id": action['id']} for action in category_actions]
                    })
                    data['actions'] += category_actions
            functions.import_global_from_dict(ActRec_pref, data)
        elif ActRec_pref.import_extension == ".json":
            with open(self.filepath, 'r', encoding='utf-8') as file:
                data = json.loads(file.read())
            category_ids = set(category.identifier for category in ActRec_pref.import_settings if category.use)
            action_ids = []
            for category in ActRec_pref.import_settings:
                action_ids += [action.identifier for action in category.actions if action.use]
            action_ids = set(action_ids)

            data['categories'] = [category for category in data['categories'] if category['id'] in category_ids]
            data['actions'] = [action for action in data['actions'] if action['id'] in action_ids]
            current_action_ids = set(action.id for action in ActRec_pref.global_actions)
            current_category_ids = set(action.id for action in ActRec_pref.categories)
            for action in data['actions']:
                if action['id'] not in current_action_ids:
                    continue
                action['id'] = uuid.uuid1().hex
            for category in data['categories']:
                if category['id'] not in current_category_ids:
                    continue
                category['id'] = uuid.uuid1().hex
            functions.import_global_from_dict(ActRec_pref, data)
            if self.include_keymap:
                km = context.window_manager.keyconfigs.user.keymaps['Screen']
                keymap.load_action_keymap_data(data, km.keymap_items)

        ActRec_pref = get_preferences(context)
        ActRec_pref.import_settings.clear()
        if ActRec_pref.autosave:
            functions.save(ActRec_pref)
        context.area.tag_redraw()
        return {"FINISHED"}

    def draw(self, context: Context) -> None:
        ActRec_pref = get_preferences(context)
        layout = self.layout
        layout.operator(
            "ar.global_import_settings",
            text="Load import settings"
        ).filepath = self.filepath
        col = layout.column(align=True)
        row = col.row(align=True)
        row.prop(self, 'mode', expand=True)
        col.prop(self, 'include_keymap')
        for category in ActRec_pref.import_settings:
            box = col.box()
            sub_col = box.column()
            row = sub_col.row()
            if category.show:
                row.prop(category, 'show', icon="TRIA_DOWN", text="", emboss=False)
            else:
                row.prop(category, 'show', icon="TRIA_RIGHT", text="", emboss=False)
            row.prop(category, 'use', text="")
            row.label(text=category.label)
            if not category.show:
                continue
            sub_col = box.column()
            for action in category.actions:
                row = sub_col.row()
                row.prop(action, 'use', text="")
                row.label(text=action.label)
                if not self.include_keymap:
                    continue
                sub2_col = row.column()
                sub2_col.alignment = 'RIGHT'
                sub2_col.enabled = False
                sub2_col.label(text=action.shortcut)

    def cancel(self, context: Context) -> None:
        ActRec_pref = get_preferences(context)
        ActRec_pref.import_settings.clear()


class AR_OT_global_import_settings(Operator):
    bl_idname = "ar.global_import_settings"
    bl_label = "Load import settings"
    bl_description = "Loads the select file to change the import settings"

    filepath: StringProperty()
    from_operator: BoolProperty(default=False)

    def valid_file(self, file: str) -> bool:
        # Only used because old Version used .zip to export and directory and file structure
        # Categories where saved as directories and Actions where saved as files in the specific directory
        """
        check if the given file is valid based on the string
        the file must match the pattern <int>~<any>~<int|Uppercase string>.py

        Args:
            file (str): filename with extension

        Returns:
            bool: is valid
        """
        if file.count('~') == 2:
            # remove .py from filename and split apart
            index, name, icon = ".".join(file.split(".")[:-1]).split("~")
            return index.isdigit() and (icon.isupper() or icon.isdigit())
        return False

    def valid_directory(self, directory: str) -> bool:
        # Only used because old Version used .zip to export and directory and file structure
        # Categories where saved as directories and Actions where saved as files in the specific directory
        """
        check if the given directory is valid based on the string
        the directory must match the pattern <int>~<name>

        Args:
            directory (str): directory, directory with path is not allowed e.g. my_path/my_dir

        Returns:
            bool: is valid
        """
        if directory.count('~') == 1:
            index, name = directory.split('~')
            return index.isdigit()
        return False

    def import_sorted_zip(self, filepath: str) -> Union[dict, str]:
        # Only used because old Version used .zip to export and directory and file structure
        # Categories where saved as directories and Actions where saved as files in the specific directory
        """
        sort the directories inside the zip based on the specific category pattern

        Args:
            filepath (str): path the zip file

        Returns:
            Union[dict, str]:
                Success (dict): category as key with list of files;
                Error (str): file that occurred with the error
        """
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
            item.sort(key=lambda x: int(x.split("/")[-1].split('~')[0]))
        return categories

    def map_shortcut_to_actions(self, context: Context, keymap_data: dict) -> dict:
        """
        maps the keymap to the corresponding action id

        Args:
            keymap_data (str): JSON Format

        Returns:
            dict: key (str): id; value (str): shortcut
        """
        km = context.window_manager.keyconfigs.addon.keymaps.new(name="AR_IMPORT_TEMP")
        keymap.load_action_keymap_data(keymap_data, km.keymap_items)
        shortcut_map = {}
        for kmi in km.keymap_items:
            shortcut_map[kmi.properties.id] = kmi.to_string()
        context.window_manager.keyconfigs.addon.keymaps.remove(km)
        return shortcut_map

    def execute(self, context: Context) -> set[str]:
        ActRec_pref = get_preferences(context)
        ActRec_pref.import_settings.clear()

        if not os.path.exists(self.filepath):
            if not self.from_operator:
                self.report({'ERROR'}, "You need to select a .json or .zip file")
            self.from_operator = False
            return {'CANCELLED'}

        if self.filepath.endswith(".zip"):
            # Only used because old Version used .zip to export and directory and file structure
            # Categories where saved as directories and Actions where saved as files in the specific directory
            ActRec_pref.import_extension = ".zip"
            categories_paths = self.import_sorted_zip(self.filepath)
            if isinstance(categories_paths, str):
                if not self.from_operator:
                    self.report(
                        {'ERROR'}, "The selected file is not compatible (%s)" % categories_paths)
                return {'CANCELLED'}
            for key, item in sorted(categories_paths.items(), key=lambda x: int(x[0].split('~')[0])):
                new_category = ActRec_pref.import_settings.add()
                new_category.identifier = key
                new_category.label = key.split('~')[1]
                for file in item:
                    new_action = new_category.actions.add()
                    new_action.identifier = file
                    new_action.label = file.split("/")[-1].split('~')[1]
            return {"FINISHED"}
        elif self.filepath.endswith(".json"):
            ActRec_pref.import_extension = ".json"
            try:
                with open(self.filepath, 'r', encoding='utf-8') as file:
                    data = json.loads(file.read())
                actions = {action['id']: action for action in data['actions']}
                shortcut_map = self.map_shortcut_to_actions(context, data)
                for category in data['categories']:
                    new_category = ActRec_pref.import_settings.add()
                    new_category.identifier = category['id']
                    new_category.label = category['label']
                    for id in category['actions']:
                        action = actions[id['id']]
                        new_action = new_category.actions.add()
                        new_action.identifier = action['id']
                        new_action.label = action['label']
                        new_action.shortcut = shortcut_map.get(action['id'], "")
                return {"FINISHED"}
            except Exception as err:
                logger.error("selected .json file not compatible (%s)" % err)
                self.report({'ERROR'}, "The selected file is not compatible (%s)" % self.filepath)
                return {'CANCELLED'}


class AR_OT_global_export(Operator, ExportHelper):
    bl_idname = "ar.global_export"
    bl_label = "Export"
    bl_description = "Export the Action file as a .json file"

    def get_export_all(self) -> bool:
        """
        default getter for export all

        Returns:
            bool: state of export all
        """
        return self.get("export_all", False)

    def set_export_all(self, value: bool) -> None:
        """
        setter for export all
        transfer the value to all categories and actions

        Args:
            value (bool): state of export all
        """
        self["export_all"] = value
        for category in self.export_categories:
            category["export_all"] = value
            for action in category.actions:
                action["export_all"] = value

    filter_glob: StringProperty(default='*.json', options={'HIDDEN'})
    filename_ext = ".json"

    filepath: StringProperty(
        name="File Path",
        description="Filepath used for exporting the file",
        maxlen=1024,
        subtype='FILE_PATH',
        default="ActionRecorderButtons"
    )

    export_all: BoolProperty(
        name="All",
        description="Export all category",
        get=get_export_all,
        set=set_export_all
    )
    export_categories: CollectionProperty(type=properties.AR_global_export_categories)

    include_keymap: BoolProperty(
        name="Include Shortcuts",
        description="Include the added Shortcuts of the actions",
        default=True
    )

    @classmethod
    def poll(cls, context: Context) -> bool:
        ActRec_pref = get_preferences(context)
        return len(ActRec_pref.global_actions)

    def invoke(self, context: Context, event: Event) -> set[str]:
        # Make copy of categories and actions ot export_categories and export_actions
        ActRec_pref = get_preferences(context)
        km = context.window_manager.keyconfigs.user.keymaps['Screen']
        for category in ActRec_pref.categories:
            new_category = self.export_categories.add()
            new_category.id = category.id
            new_category.label = category.label
            for id_action in category.actions:
                action = ActRec_pref.global_actions.get(id_action.id, None)
                if action is None:
                    category.actions.remove(category.actions.find(id_action.id))
                    continue
                new_action = new_category.actions.add()
                new_action.id = action.id
                new_action.label = action.label
                action_keymap = functions.get_action_keymap(action.id, km)
                if action_keymap:
                    new_action.shortcut = action_keymap.to_string()
        return ExportHelper.invoke(self, context, event)

    def execute(self, context: Context) -> set[str]:
        ActRec_pref = get_preferences(context)
        if not os.path.exists(os.path.dirname(self.filepath)):
            self.report({'ERROR', "Directory doesn't exist"})
            return {'CANCELLED'}
        if not self.filepath.endswith(".json"):
            self.report({'ERROR', "File has to be a json file"})
            return {'CANCELLED'}
        data = defaultdict(list)
        export_category_ids = set(
            category.id for category in self.export_categories if category.use
        )
        export_action_ids = []
        for category in self.export_categories:
            export_action_ids += set(
                action.id for action in category.actions if action.use
            )
        for category in ActRec_pref.categories:
            if category.id in export_category_ids:
                item = functions.property_to_python(
                    category,
                    exclude=["name", "selected", "actions.name", "areas.name", "areas.modes.name"]
                )
                length = len(item["actions"])
                for i, action in enumerate(reversed(item["actions"]), start=1):
                    if action["id"] not in export_action_ids:
                        item["actions"].pop(length - i)
                data['categories'].append(item)
        for action in ActRec_pref.global_actions:
            if action.id in export_action_ids:
                data['actions'].append(functions.property_to_python(
                    action,
                    exclude=["name", "selected", "alert", "macros.name",
                             "macros.is_available", "macros.alert", "is_playing"]
                ))

        if self.include_keymap:
            km = context.window_manager.keyconfigs.user.keymaps['Screen']
            keymap.append_keymap(data, export_action_ids, km)

        with open(self.filepath, 'w', encoding='utf-8') as file:
            json.dump(data, file, ensure_ascii=False, indent=2)
        self.cancel(context)
        return {'FINISHED'}

    def cancel(self, context: Context) -> None:
        self.export_categories.clear()
        self.all_categories = True

    def draw(self, context: Context) -> None:
        layout = self.layout
        layout.prop(self, 'include_keymap')
        layout.prop(self, 'export_all', text="All")
        col = layout.column(align=True)
        for category in self.export_categories:
            box = col.box()
            col2 = box.column()
            row = col2.row()
            row.prop(
                category, 'show', icon="TRIA_DOWN" if category.show else "TRIA_RIGHT", text="", emboss=False)
            row.label(text=category.label)
            row.prop(category, 'use', text="")

            if not category.show:
                continue
            col2 = box.column(align=False)
            for action in category.actions:
                sub_row = col2.row()
                sub_row.prop(action, 'use', text='')
                sub_row.label(text=action.label)
                if self.include_keymap:
                    sub_col = sub_row.column()
                    sub_col.alignment = 'RIGHT'
                    sub_col.enabled = False
                    sub_col.label(text=action.shortcut)


class AR_OT_global_save(Operator):
    bl_idname = "ar.global_save"
    bl_label = "Save"
    bl_description = "Save all Global Actions to the Storage"

    def execute(self, context: Context) -> set[str]:
        functions.save(get_preferences(context))
        return {"FINISHED"}


class AR_OT_global_load(Operator):
    bl_idname = "ar.global_load"
    bl_label = "Load"
    bl_description = "Load all Actions from the Storage"

    def execute(self, context: Context) -> set[str]:
        ActRec_pref = get_preferences(context)
        functions.load(ActRec_pref)
        context.area.tag_redraw()
        return {"FINISHED"}


class AR_OT_global_to_local(shared.Id_based, Operator):
    bl_idname = "ar.global_to_local"
    bl_label = "Global Action to Local"
    bl_description = "Transfer the selected Action to Local-actions"
    bl_options = {'UNDO'}

    @ classmethod
    def poll(cls, context: Context) -> bool:
        ActRec_pref = get_preferences(context)
        return len(ActRec_pref.global_actions) and len(ActRec_pref.get("global_actions.selected_ids", []))

    def global_to_local(self, ActRec_pref: AR_preferences, action: AR_global_actions) -> None:
        """
        copy the given global action to a local action

        Args:
            ActRec_pref (AR_preferences): preferences of this addon
            action (AR_global_actions): action to copy
        """
        id = uuid.uuid1().hex if action.id in set(x.id for x in ActRec_pref.local_actions) else action.id
        data = functions.property_to_python(
            action,
            exclude=["name", "alert", "macros.name", "macros.alert",
                     "macros.is_available", "macros.is_playing", "is_playing"]
        )
        data["id"] = id
        functions.add_data_to_collection(ActRec_pref.local_actions, data)
        ActRec_pref.active_local_action_index = len(ActRec_pref.local_actions)

    def execute(self, context: Context) -> set[str]:
        ActRec_pref = get_preferences(context)
        for id in functions.get_global_action_ids(ActRec_pref, self.id, self.index):
            self.global_to_local(ActRec_pref, ActRec_pref.global_actions[id])
            if ActRec_pref.global_to_local_mode != 'move':
                continue
            ActRec_pref.global_actions.remove(ActRec_pref.global_actions.find(id))
            for category in ActRec_pref.categories:
                category.actions.remove(category.actions.find(id))
        functions.save_local_to_scene(ActRec_pref, context.scene)
        if ActRec_pref.autosave:
            functions.save(ActRec_pref)
        context.area.tag_redraw()
        self.clear()
        return {"FINISHED"}


class AR_OT_global_remove(shared.Id_based, Operator):
    bl_idname = "ar.global_remove"
    bl_label = "Remove Action"
    bl_description = "Remove the selected actions"

    @classmethod
    def description(cls, context: Context, properties: OperatorProperties) -> str:
        ActRec_pref = get_preferences(context)
        ids = ActRec_pref.get("global_actions.selected_ids", [])
        selected_actions_str = ", ".join(ActRec_pref.global_actions[id].label for id in ids)
        return "Remove the selected actions\nActions: %s" % (selected_actions_str)

    @classmethod
    def poll(cls, context: Context) -> bool:
        ActRec_pref = get_preferences(context)
        return len(ActRec_pref.global_actions) and len(ActRec_pref.get("global_actions.selected_ids", []))

    def invoke(self, context: Context, event: Event) -> set[str]:
        return context.window_manager.invoke_confirm(self, event)

    def execute(self, context: Context) -> set[str]:
        ActRec_pref = get_preferences(context)
        km = context.window_manager.keyconfigs.user.keymaps['Screen']
        for id in functions.get_global_action_ids(ActRec_pref, self.id, self.index):
            if functions.get_action_keymap(id, km) is not None:
                functions.remove_action_keymap(id, km)
            ActRec_pref.global_actions.remove(ActRec_pref.global_actions.find(id))
            for category in ActRec_pref.categories:
                category.actions.remove(category.actions.find(id))
        if ActRec_pref.autosave:
            functions.save(ActRec_pref)
        context.area.tag_redraw()
        self.clear()
        return {"FINISHED"}


class AR_OT_global_move_up(shared.Id_based, Operator):
    bl_idname = "ar.global_move_up"
    bl_label = "Move Action Up"
    bl_description = "Move the selected actions Up"

    @classmethod
    def poll(cls, context: Context) -> bool:
        ActRec_pref = get_preferences(context)
        return len(ActRec_pref.global_actions) and len(ActRec_pref.get("global_actions.selected_ids", []))

    def execute(self, context: Context) -> set[str]:
        ActRec_pref = get_preferences(context)
        ids = set(functions.get_global_action_ids(ActRec_pref, self.id, self.index))
        for category in ActRec_pref.categories:
            for id_action in category.actions:
                if id_action.id not in ids:
                    continue
                index = category.actions.find(id_action.id)
                category.actions.move(index, index - 1)
        if ActRec_pref.autosave:
            functions.save(ActRec_pref)
        context.area.tag_redraw()
        self.clear()
        return {"FINISHED"}


class AR_OT_global_move_down(shared.Id_based, Operator):
    bl_idname = "ar.global_move_down"
    bl_label = "Move Action Down"
    bl_description = "Move the selected actions Down"

    @classmethod
    def poll(cls, context: Context) -> bool:
        ActRec_pref = get_preferences(context)
        return len(ActRec_pref.global_actions) and len(ActRec_pref.get("global_actions.selected_ids", []))

    def execute(self, context: Context) -> set[str]:
        ActRec_pref = get_preferences(context)
        ids = set(functions.get_global_action_ids(ActRec_pref, self.id, self.index))
        for category in ActRec_pref.categories:
            for id_action in reversed(list(category.actions)):
                if id_action.id not in ids:
                    continue
                index = category.actions.find(id_action.id)
                category.actions.move(index, index + 1)
        if ActRec_pref.autosave:
            functions.save(ActRec_pref)
        context.area.tag_redraw()
        self.clear()
        return {"FINISHED"}


class AR_OT_global_execute_action(shared.Id_based, Operator):
    bl_idname = 'ar.global_execute_action'
    bl_label = 'ActRec Action Button'
    bl_description = 'Play this Action Button'
    bl_options = {'UNDO', 'INTERNAL'}

    @classmethod
    def description(cls, context: Context, properties: OperatorProperties):
        ActRec_pref = functions.get_preferences(context)
        id = functions.get_global_action_id(ActRec_pref, properties.id, properties.index)
        action = ActRec_pref.global_actions[id]
        return action.description

    def execute(self, context: Context) -> set[str]:
        ActRec_pref = get_preferences(context)
        id = functions.get_global_action_id(ActRec_pref, self.id, self.index)
        self.clear()
        if id is None:
            return {'CANCELLED'}
        action = ActRec_pref.global_actions[id]
        if action.is_playing:
            self.report({'INFO'}, "The action is already playing!")
            return {'CANCELLED'}
        err = functions.play(context, action.macros, action, 'global_actions')
        if err:
            self.report({'ERROR'}, str(err))
        return {'FINISHED'}


class AR_OT_global_icon(icon_manager.Icontable, shared.Id_based, Operator):
    bl_idname = "ar.global_icon"

    def invoke(self, context: Context, event: Event) -> set[str]:
        ActRec_pref = get_preferences(context)
        id = functions.get_global_action_id(ActRec_pref, self.id, self.index)
        if id is None:
            self.clear()
            return {'CANCELLED'}
        self.id = id
        if not self.reuse:
            ActRec_pref.selected_icon = ActRec_pref.global_actions[id].icon
        self.search = ''
        return context.window_manager.invoke_props_dialog(self, width=1000)

    def execute(self, context: Context) -> set[str]:
        ActRec_pref = get_preferences(context)
        ActRec_pref.global_actions[self.id].icon = ActRec_pref.selected_icon
        ActRec_pref.selected_icon = 0  # Icon: NONE
        self.reuse = False
        if ActRec_pref.autosave:
            functions.save(ActRec_pref)
        bpy.context.area.tag_redraw()
        self.clear()
        return {"FINISHED"}


class AR_OT_add_ar_shortcut(Operator):
    bl_idname = "ar.add_ar_shortcut"
    bl_label = "Add Shortcut"
    bl_options = {'INTERNAL'}
    bl_description = "Add a Shortcut to the selected Action"

    id: StringProperty()

    def draw(self, context: Context) -> None:
        self.layout.label(text=self.bl_label)
        km = keymap.keymaps['temp']
        for kmi in km.keymap_items:
            if kmi.idname != "ar.global_execute_action" or kmi.properties.id != self.id:
                continue
            self.layout.prop(kmi, "type", text="", full_event=True)
            kmi.active = True
            break

    def invoke(self, context: Context, event: Event) -> set[str]:
        km = keymap.keymaps['temp']
        if self.id and functions.get_action_keymap(self.id, km) is None:
            functions.add_empty_action_keymap(self.id, km)
        return context.window_manager.invoke_popup(self)

    def execute(self, context: Context) -> set[str]:
        return {"FINISHED"}

    def cancel(self, context: Context) -> None:
        #  Use cancel as execution of changed keymap (not intended use of invoke_popup)
        km = keymap.keymaps['temp']
        kmi = functions.get_action_keymap(self.id, km)
        if self.id != '' and not functions.is_action_keymap_empty(kmi):
            km_user = context.window_manager.keyconfigs.user.keymaps['Screen']
            km_user.keymap_items.new_from_item(kmi, head=True)
        functions.remove_action_keymap(self.id, km)


class AR_OT_remove_ar_shortcut(Operator):
    bl_idname = "ar.remove_ar_shortcut"
    bl_label = "Remove Shortcut"
    bl_options = {'INTERNAL'}
    bl_description = "Remove the Shortcut from the selected Action"

    id: StringProperty()

    def execute(self, context: Context) -> set[str]:
        km = context.window_manager.keyconfigs.user.keymaps['Screen']
        if functions.get_action_keymap(self.id, km) is None:
            return {"CANCELLED"}
        functions.remove_action_keymap(self.id, km)
        return {"FINISHED"}


class AR_OT_global_edit(Operator):
    bl_idname = "ar.global_edit"
    bl_label = "Edit Action"
    bl_description = "Edit the label and description of this Action"
    bl_options = {'INTERNAL'}

    id: StringProperty()
    description: StringProperty(
        name="Description",
        description="Sets the description that gets shown when hovered over this action"
    )
    label: StringProperty(
        name="Label",
        description="Sets the label of this action"
    )

    def draw(self, context: Context) -> None:
        layout = self.layout
        layout.prop(self, 'label')
        layout.prop(self, 'description')

    def invoke(self, context: Context, event: Event) -> set[str]:
        ActRec_pref = functions.get_preferences(context)
        id = functions.get_global_action_id(ActRec_pref, self.id, -1)
        action = ActRec_pref.global_actions[id]
        self.label = action.label
        self.description = action.description
        return context.window_manager.invoke_props_dialog(self)

    def execute(self, context: Context) -> set[str]:
        ActRec_pref = functions.get_preferences(context)
        id = functions.get_global_action_id(ActRec_pref, self.id, -1)
        action = ActRec_pref.global_actions[id]
        action.label = self.label
        action.description = self.description
        if ActRec_pref.autosave:
            functions.save(ActRec_pref)
        context.area.tag_redraw()
        return {'FINISHED'}

# endregion


classes = [
    AR_OT_global_recategorize_action,
    AR_OT_global_import,
    AR_OT_global_import_settings,
    AR_OT_global_export,
    AR_OT_global_save,
    AR_OT_global_load,
    AR_OT_global_to_local,
    AR_OT_global_remove,
    AR_OT_global_move_up,
    AR_OT_global_move_down,
    AR_OT_global_execute_action,
    AR_OT_global_icon,
    AR_OT_add_ar_shortcut,
    AR_OT_remove_ar_shortcut,
    AR_OT_global_edit
]

# region Registration


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)
# endregion
