# region Imports
# external modules
import os
import importlib
from typing import TYPE_CHECKING

# blender modules
import bpy
from bpy.props import StringProperty, BoolProperty, EnumProperty, CollectionProperty, IntProperty
from bpy.types import AddonPreferences, Context
import rna_keymap_ui

# relative imports
from . import properties, functions, config, update, keymap, log, shared_data
from .log import logger, log_sys

if TYPE_CHECKING:
    def get_preferences(): return
else:
    from .functions.shared import get_preferences
# endregion

# region Preferences

class AR_preferences(AddonPreferences):
    global_selected_ids_internal: StringProperty(default="")
    bl_idname = __package__.split(".")[0]

    # --- Stable Internal Properties for Blender 5.0 ---
    is_loaded_internal: BoolProperty(default=False)
    icon_path_internal: StringProperty(default="")
    storage_path_internal: StringProperty(default="")
    active_local_action_index_internal: IntProperty(default=0)

    def update_is_loaded(self, context: Context) -> None:
        context.scene.name = context.scene.name

    def get_is_loaded(self) -> bool:
        return self.is_loaded_internal and shared_data.data_loaded

    def set_is_loaded(self, value: bool) -> None:
        self.is_loaded_internal = value

    is_loaded: BoolProperty(
        name="INTERNAL",
        description="INTERNAL USE ONLY",
        default=False,
        update=update_is_loaded,
        get=get_is_loaded,
        set=set_is_loaded
    )

    addon_directory: StringProperty(
        name="addon directory",
        default=os.path.dirname(os.path.dirname(__file__)),
        get=lambda self: self.bl_rna.properties['addon_directory'].default
    )

    preference_tab: EnumProperty(
        items=[('settings', "Settings", ""),
               ('path', "Paths", ""),
               ('keymap', "Keymap", ""),
               ('update', "Update", "")],
        name="Tab",
        description="Switch between preference tabs"
    )

    log_amount: IntProperty(
        name="Log Amount",
        description="Number of log files kept\nChanges apply on the next launch of Blender",
        default=5,
        min=1,
        soft_max=100
    )

    # icon manager
    def get_icon_path(self) -> str:
        origin_path = self.icon_path_internal
        if origin_path == "":
            origin_path = os.path.join(self.addon_directory, "Icons")
            self.icon_path_internal = origin_path
            
        if os.path.exists(origin_path):
            return origin_path
        else:
            path = os.path.join(self.addon_directory, "Icons")
            if not os.path.exists(path):
                os.makedirs(path, exist_ok=True)
            self.icon_path_internal = path
            return path

    def set_icon_path(self, origin_path: str) -> None:
        self.icon_path_internal = origin_path
        if not (os.path.exists(origin_path) and os.path.isdir(origin_path)):
            os.makedirs(origin_path, exist_ok=True)

    icon_path: StringProperty(
        name="Icons Path",
        description="The Path to the Storage for the added Icons",
        default=os.path.join(os.path.dirname(os.path.dirname(__file__)), "Icons"),
        get=get_icon_path,
        set=set_icon_path
    )

    selected_icon: IntProperty(
        name="selected icon",
        description="only internal usage",
        default=0,
        min=0,
        options={'HIDDEN'}
    )

    # update
    update: BoolProperty()
    restart: BoolProperty()
    version: StringProperty()
    auto_update: BoolProperty(
        default=True,
        name="Auto Update",
        description="automatically search for a new update"
    )
    update_progress: IntProperty(
        name="Update Progress",
        default=-1,
        min=-1,
        max=100,
        soft_min=0,
        soft_max=100,
        subtype='PERCENTAGE'
    )

    # locals
    local_actions: CollectionProperty(type=properties.AR_local_actions)

    def get_active_local_action_index(self) -> int:
        value = self.active_local_action_index_internal
        actions_length = len(self.local_actions)
        return value if value < actions_length else max(0, actions_length - 1)

    def set_active_local_action_index(self, value: int):
        # Using context from argument is safer if available, but we'll use bpy.context for now
        ActRec_pref = self # Inside the class, self is the pref object
        if not ActRec_pref.local_record_macros:
            actions_length = len(self.local_actions)
            safe_value = value if value < actions_length else actions_length - 1
            self.active_local_action_index_internal = safe_value if safe_value >= 0 else 0

    active_local_action_index: IntProperty(
        name="Select",
        min=0,
        get=get_active_local_action_index,
        set=set_active_local_action_index
    )
    local_to_global_mode: EnumProperty(
        name="Mode",
        items=[
            ("copy", "Copy", "Copy the Action over to Global"),
            ("move", "Move", "Move the Action over to Global and Delete it from Local")]
    )
    local_record_macros: BoolProperty(name="Record Macros", default=False)

    def hide_show_local_in_texteditor(self, context: Context):
        if self.hide_local_text:
            for text in bpy.data.texts:
                if text.lines and text.lines[0].body.strip().startswith("###ActRec_pref###"):
                    bpy.data.texts.remove(text)
        else:
            for action in self.local_actions:
                functions.local_action_to_text(action)
    
    hide_local_text: BoolProperty(
        name="Hide Local Action in Texteditor",
        description="Hide the Local Action in the Texteditor",
        update=hide_show_local_in_texteditor,
        default=True
    )
    local_create_empty: BoolProperty(default=True, name="Create Empty", description="Create Empty Macro on Error")

    # macros
    last_macro_label: StringProperty(name="last label", default="label of the last macro")
    last_macro_command: StringProperty(name="last command", default="command of the last macro")

    operators_list_length: IntProperty(name="INTERNAL", default=0)

    multiline_support_installing: BoolProperty(name="INTERNAL", default=False)
    multiline_support_dont_ask: BoolProperty(
        name="Don't Ask Again",
        description="Turns off the request for multiline support.",
        default=False
    )

    # globals
    global_actions: CollectionProperty(type=properties.AR_global_actions)

    global_to_local_mode: EnumProperty(
        items=[("copy", "Copy", "Copy the Action over to Global"),
               ("move", "Move", "Move the Action over to Global and Delete it from Local")],
        name="Mode"
    )
    autosave: BoolProperty(
        default=True,
        name="Autosave",
        description="automatically saves all Global Buttons to the Storage"
    )
    global_rename: StringProperty(name="Rename", description="Rename the selected Action")
    global_hide_menu: BoolProperty(name="Hide", description="Hide the global Menu")

    import_settings: CollectionProperty(type=properties.AR_global_import_category)
    import_extension: StringProperty()

    # categories
    def get_storage_path(self) -> str:
        origin_path = self.storage_path_internal
        if origin_path == "":
             origin_path = os.path.join(self.addon_directory, "Storage.json")
             self.storage_path_internal = origin_path
             
        if os.path.exists(origin_path):
            return origin_path
        else:
            path = os.path.join(self.addon_directory, "Storage.json")
            self.storage_path_internal = path
            return path

    def set_storage_path(self, origin_path: str) -> None:
        self.storage_path_internal = origin_path
        if os.path.exists(origin_path) and os.path.isfile(origin_path):
            return
        os.makedirs(os.path.dirname(origin_path), exist_ok=True)
        with open(origin_path, 'w') as storage_file:
            storage_file.write('{}')

    storage_path: StringProperty(
        name="Storage Path",
        description="The Path to the Storage for the saved Categories",
        default=os.path.join(os.path.dirname(os.path.dirname(__file__)), "Storage.json"),
        get=get_storage_path,
        set=set_storage_path
    )

    categories: CollectionProperty(type=properties.AR_category)

    # Added a stable storage for the selected category ID
    selected_category_id: StringProperty(default="")

    def get_selected_category(self) -> str:
        return self.selected_category_id
    
    def set_selected_category(self, value: str):
        self.selected_category_id = value

    selected_category: StringProperty(get=get_selected_category, set=set_selected_category, default='')
    show_all_categories: BoolProperty(name="Show All Categories", default=False)

    def draw(self, context: Context) -> None:
        ActRec_pref = self
        layout = self.layout
        col = layout.column()
        row = col.row(align=True)
        row.prop(ActRec_pref, 'preference_tab', expand=True)
        
        if ActRec_pref.preference_tab == 'update':
            col.operator('wm.url_open', text="Release Notes").url = config.release_notes_url
            row = col.row()
            if ActRec_pref.update:
                update.draw_update_button(row, ActRec_pref)
            else:
                row.operator('ar.update_check', text="Check For Updates")
                if ActRec_pref.restart:
                    row.operator('ar.show_restart_menu', text="Restart to Finish")
            if ActRec_pref.version != '':
                if ActRec_pref.update:
                    col.label(text="A new Version is available (%s)" % ActRec_pref.version)
                else:
                    col.label(text="You are using the latest Version (%s)" % ActRec_pref.version)
        
        elif ActRec_pref.preference_tab == 'path':
            col.label(text='Action Storage Folder')
            row = col.row()
            ops = row.operator("ar.preferences_directory_selector", text="Select Action Button's Storage Folder", icon='FILEBROWSER')
            ops.preference_name = "storage_path"
            ops.path_extension = "Storage.json"

            ops = row.operator("ar.preferences_recover_directory", text="Recover Default Folder", icon='FOLDER_REDIRECT')
            ops.preference_name = "storage_path"
            ops.path_extension = "Storage.json"
            row.operator('ar.preferences_open_explorer', text="", icon='FILEBROWSER').path = self.storage_path

            box = col.box()
            box_row = box.row()
            box_row.label(text=self.storage_path)
            op = box_row.operator('ar.copy_text', text="", icon="COPYDOWN")
            op.text = self.storage_path
            
            col.separator(factor=1.5)
            row = col.row().split(factor=0.5)
            row.label(text="Icon Storage Folder")
            row2 = row.row(align=True).split(factor=0.65, align=True)
            row2.operator("ar.add_custom_icon", text="Add Custom Icon", icon='PLUS')
            row2.operator("ar.delete_custom_icon", text="Delete", icon='TRASH')
            
            row = col.row()
            ops = row.operator("ar.preferences_directory_selector", text="Select Icon Storage Folder", icon='FILEBROWSER')
            ops.preference_name = "icon_path"
            ops.path_extension = ""

            ops = row.operator("ar.preferences_recover_directory", text="Recover Default Folder", icon='FOLDER_REDIRECT')
            ops.preference_name = "icon_path"
            ops.path_extension = "Icons"
            row.operator('ar.preferences_open_explorer', text="", icon='FILEBROWSER').path = self.icon_path

            box = col.box()
            box_row = box.row()
            box_row.label(text=self.icon_path)
            op = box_row.operator('ar.copy_text', text="", icon="COPYDOWN")
            op.text = self.icon_path
            
            col.separator(factor=1.5)
            row2 = col.row(align=True).split(factor=0.7, align=True)
            row2.operator('ar.preferences_open_explorer', text="Open Log").path = log_sys.path
            row2.prop(self, 'log_amount')
            
        elif ActRec_pref.preference_tab == 'keymap':
            col2 = col.column()
            kc = bpy.context.window_manager.keyconfigs.user
            for addon_keymap in keymap.keymaps.values():
                km = kc.keymaps.get(addon_keymap.name)
                if not km:
                    continue
                km = km.active()
                col2.context_pointer_set("keymap", km)
                ar_keymaps = filter(
                    lambda x: any(x.name == kmi.name and x.idname == kmi.idname
                                  for kmi in keymap.keymap_items['default']),
                    km.keymap_items
                )
                for kmi in [*ar_keymaps, *functions.get_all_action_keymaps(km)]:
                    rna_keymap_ui.draw_kmi(kc.keymaps, kc, km, kmi, col2, 0)
                    
        elif ActRec_pref.preference_tab == 'settings':
            row = col.row()
            row.prop(self, 'auto_update')
            row.prop(self, 'autosave')
            row = col.row()
            row.prop(self, 'hide_local_text')
            row.prop(self, 'local_create_empty')
            if importlib.util.find_spec('fontTools') is None:
                row = col.row()
                if self.multiline_support_installing:
                    row.label(text="Installing fontTools...")
                else:
                    row.operator('ar.macro_install_multiline_support')
            col.separator(factor=1.5)
            row = col.row()
            row.operator('wm.url_open', text="Manual", icon='ASSET_MANAGER').url = config.manual_url
            row.operator('wm.url_open', text="Hint", icon='HELP').url = config.hint_url
            row.operator('wm.url_open', text="Bug Report", icon='URL').url = config.bug_report_url
# endregion

classes = [
    AR_preferences
]

# region Registration

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    # Attempt to get pref safely; if this fails, we skip log config update
    try:
        ActRec_pref = get_preferences(bpy.context)
        log.update_log_amount_in_config(ActRec_pref.log_amount)
    except:
        pass
    for cls in classes:
        bpy.utils.unregister_class(cls)
# endregion