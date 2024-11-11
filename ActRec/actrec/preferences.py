# region Imports
# external modules
import os
from typing import TYPE_CHECKING

# blender modules
import bpy
from bpy.props import StringProperty, BoolProperty, EnumProperty, CollectionProperty, IntProperty
from bpy.types import AddonPreferences, Context
import rna_keymap_ui

# relative imports
from . import properties, functions, config, keymap, log, shared_data
from .log import logger, log_sys
from .. import __package__ as base_package
from .functions import wrapper

if TYPE_CHECKING:
    def get_preferences(): return
else:
    from .functions.shared import get_preferences
# endregion

# region Preferences


class AR_preferences(AddonPreferences):
    bl_idname = base_package

    def update_is_loaded(self, context: Context) -> None:
        context.scene.name = context.scene.name

    def get_is_loaded(self) -> bool:
        return self.get("is_loaded", False) and shared_data.data_loaded

    def set_is_loaded(self, value: bool) -> None:
        self["is_loaded"] = value

    is_loaded: BoolProperty(
        name="INTERNAL",
        description="INTERNAL USE ONLY",
        default=False,
        update=update_is_loaded,
        get=get_is_loaded,
        set=set_is_loaded
    )

    source_addon_directory: StringProperty(
        name="source addon directory",
        default=os.path.dirname(os.path.dirname(__file__)),
        get=lambda self: self.bl_rna.properties['source_addon_directory'].default
    )  # get the base addon directory of the source files

    addon_directory: StringProperty(
        name="addon directory",
        default=wrapper.get_user_path(base_package, create=True),
        get=lambda self: self.bl_rna.properties['addon_directory'].default
    )  # get the base addon directory for local files

    preference_tab: EnumProperty(
        items=[('settings', "Settings", ""),
               ('path', "Paths", ""),
               ('keymap', "Keymap", "")],
        name="Tab",
        description="Switch between preference tabs"
    )

    # log
    log_amount: IntProperty(
        name="Log Amount",
        description="Number of log files kept\nChanges apply on the next launch of Blender",
        default=5,
        min=1,
        soft_max=100
    )

    # icon manager
    def get_icon_path(self) -> str:
        """
        getter of icon_path
        fallback to relative path of the addon if folder doesn't exists

        Returns:
            str: path of the folder
        """
        origin_path = self.get('icon_path', 'Fallback')
        if os.path.exists(origin_path):
            return self['icon_path']
        else:
            path = os.path.join(self.addon_directory, "Icons")
            if origin_path != 'Fallback':
                logger.error("ActRec ERROR: Icon Path \"%s\" don't exist, fallback to %s" % (origin_path, path))
            self['icon_path'] = path
            if not os.path.exists(path):
                os.makedirs(path, exist_ok=True)
            return path

    def set_icon_path(self, origin_path: str) -> None:
        """setter of icon_path
        creates new folder if needed

        Args:
            origin_path (str): path of the new icon folder
        """
        self['icon_path'] = origin_path
        if not (os.path.exists(origin_path) and os.path.isdir(origin_path)):
            os.makedirs(origin_path, exist_ok=True)

    icon_path: StringProperty(
        name="Icons Path",
        description="The Path to the Storage for the added Icons",
        default=os.path.join(wrapper.get_user_path(base_package, create=True), "Icons"),
        get=get_icon_path,
        set=set_icon_path
    )

    # Icon NONE: Global: BLANK1 (101), Local: MESH_PLANE (286)
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
    )  # used as slider

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
    )  # used as slider

    # locals
    local_actions: CollectionProperty(type=properties.AR_local_actions)

    def get_active_local_action_index(self) -> int:
        """
        getter of active_local_action_index

        Returns:
            int: index of the active local action
        """
        value = self.get('active_local_action_index', 0)
        actions_length = len(self.local_actions)
        return value if value < actions_length else actions_length - 1

    def set_active_local_action_index(self, value: int):
        """
        setter of active_local_action_index
        sets a new local index if possible

        Args:
            value (int): index to set
        """
        ActRec_pref = get_preferences(bpy.context)
        if not ActRec_pref.local_record_macros:
            actions_length = len(self.local_actions)
            value = value if value < actions_length else actions_length - 1
            self['active_local_action_index'] = value if value >= 0 else actions_length - 1

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
        """
        update function of hide_local_text
        gets called every time the value of the hide_local_text is changed
        hides/show the local action as text files in the texteditor of Blender

        Args:
            context (Context): unused
        """
        if self.hide_local_text:
            for text in bpy.data.texts:
                if text.lines[0].body.strip().startswith("###ActRec_pref###"):
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
        description="""Turns off the request for multiline support.
Can also be installed under Preferences > Add-ons > Action Recorder > Settings""",
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
        """
        getter of storage_path
        fallback to relative path of the addon if folder doesn't exists

        Returns:
            str: path of the storage file
        """
        origin_path = self.get('storage_path', 'Fallback')
        if os.path.exists(origin_path):
            return self['storage_path']
        else:
            path = os.path.join(self.addon_directory, "Storage.json")
            if origin_path != 'Fallback':
                logger.error("ActRec ERROR: Storage Path \"%s\" don't exist, fallback to %s" % (origin_path, path))
            self['storage_path'] = path
            return path

    def set_storage_path(self, origin_path: str) -> None:
        """
        setter of storage_path

        Args:
            origin_path (str): path of the new storage file
        """
        self['storage_path'] = origin_path
        if os.path.exists(origin_path) and os.path.isfile(origin_path):
            return
        os.makedirs(os.path.dirname(origin_path), exist_ok=True)
        with open(origin_path, 'w') as storage_file:
            storage_file.write('{}')

    storage_path: StringProperty(
        name="Storage Path",
        description="The Path to the Storage for the saved Categories",
        default=os.path.join(wrapper.get_user_path(base_package, create=True), "Storage.json"),
        get=get_storage_path,
        set=set_storage_path
    )

    categories: CollectionProperty(type=properties.AR_category)

    def get_selected_category(self) -> str:
        """
        getter of selected_category

        Returns:
            str: returns the id (uuid hex format) of the selected category
        """
        return self.get("categories.selected_id", '')
    selected_category: StringProperty(get=get_selected_category, default='')
    show_all_categories: BoolProperty(name="Show All Categories", default=False)

    def draw(self, context: Context) -> None:
        """
        draws the addon preferences

        Args:
            context (Context): active blender context
        """
        ActRec_pref = get_preferences(context)
        layout = self.layout
        col = layout.column()
        row = col.row(align=True)
        row.prop(ActRec_pref, 'preference_tab', expand=True)
        if ActRec_pref.preference_tab == 'path':
            col.label(text='Action Storage Folder')
            row = col.row()
            ops = row.operator(
                "ar.preferences_directory_selector",
                text="Select Action Button's Storage Folder",
                icon='FILEBROWSER'
            )
            ops.preference_name = "storage_path"
            ops.path_extension = "Storage.json"

            ops = row.operator(
                "ar.preferences_recover_directory",
                text="Recover Default Folder",
                icon='FOLDER_REDIRECT'
            )
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
            row2.operator(
                "ar.add_custom_icon",
                text="Add Custom Icon",
                icon='PLUS'
            )
            row2.operator("ar.delete_custom_icon", text="Delete", icon='TRASH')
            row = col.row()
            ops = row.operator(
                "ar.preferences_directory_selector",
                text="Select Icon Storage Folder",
                icon='FILEBROWSER'
            )
            ops.preference_name = "icon_path"
            ops.path_extension = ""

            ops = row.operator(
                "ar.preferences_recover_directory",
                text="Recover Default Folder",
                icon='FOLDER_REDIRECT'
            )
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
            row.prop(self, 'autosave')
            row = col.row()
            row.prop(self, 'hide_local_text')
            row.prop(self, 'local_create_empty')
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
    ActRec_pref = functions.get_preferences(bpy.context)
    log.update_log_amount_in_config(ActRec_pref.log_amount)
    for cls in classes:
        bpy.utils.unregister_class(cls)
# endregion
