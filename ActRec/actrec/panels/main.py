# region Imports
# blender modules
import bpy
from bpy.types import Panel, Context

# relative imports
from .. import config
from .. import update
from ..log import log_sys
from ..functions.shared import get_preferences
# endregion

classes = []
ui_space_types = ['CLIP_EDITOR', 'NODE_EDITOR', 'TEXT_EDITOR', 'SEQUENCE_EDITOR', 'NLA_EDITOR',
                  'DOPESHEET_EDITOR', 'VIEW_3D', 'GRAPH_EDITOR', 'IMAGE_EDITOR']  # blender spaces with UI region

# region Panels


def panel_factory(space_type: str):
    """
    create panels for every space type with UI

    Args:
        space_type (str): valid space type of blender which has a UI region
    """

    class AR_PT_local(Panel):
        bl_space_type = space_type
        bl_region_type = 'UI'
        bl_category = 'Action Recorder'
        bl_label = 'Local Actions'
        bl_idname = "AR_PT_local_%s" % space_type
        bl_order = 0

        def draw(self, context: Context) -> None:
            ActRec_pref = get_preferences(context)
            layout = self.layout
            if ActRec_pref.update:
                box = layout.box()
                box.label(text="new Version available (%s)" % ActRec_pref.version)
                update.draw_update_button(box, ActRec_pref)
            box = layout.box()
            box_row = box.row()
            col = box_row.column()
            col.template_list('AR_UL_locals', '', ActRec_pref, 'local_actions',
                              ActRec_pref, 'active_local_action_index', rows=4, sort_lock=True)
            col = box_row.column()
            col2 = col.column(align=True)
            col2.operator("ar.local_add", text='', icon='ADD')
            col2.operator("ar.local_remove", text='', icon='REMOVE')
            col2 = col.column(align=True)
            col2.operator("ar.local_move_up", text='', icon='TRIA_UP')
            col2.operator("ar.local_move_down", text='', icon='TRIA_DOWN')
    AR_PT_local.__name__ = "AR_PT_local_%s" % space_type

    class AR_PT_macro(Panel):
        bl_space_type = space_type
        bl_region_type = 'UI'
        bl_category = 'Action Recorder'
        bl_label = 'Macro Editor'
        bl_idname = "AR_PT_macro_%s" % space_type
        bl_order = 1

        @classmethod
        def poll(cls, context: Context) -> bool:
            ActRec_pref = get_preferences(context)
            return len(ActRec_pref.local_actions)

        def draw(self, context: Context) -> None:
            ActRec_pref = get_preferences(context)
            layout = self.layout
            box = layout.box()
            box_row = box.row()
            col = box_row.column()
            selected_action = ActRec_pref.local_actions[ActRec_pref.active_local_action_index]
            col.template_list(
                'AR_UL_macros',
                '',
                selected_action,
                'macros',
                selected_action,
                'active_macro_index',
                rows=4,
                sort_lock=True
            )
            col = box_row.column()
            col.active = not selected_action.is_playing
            if not ActRec_pref.local_record_macros:
                col2 = col.column(align=True)
                col2.operator("ar.macro_add", text='', icon='ADD')
                col2.operator("ar.macro_add_event", text='', icon='MODIFIER')
                col2.operator("ar.macro_remove", text='', icon='REMOVE')
                col2 = col.column(align=True)
                col2.operator("ar.macro_move_up", text='', icon='TRIA_UP')
                col2.operator("ar.macro_move_down", text='', icon='TRIA_DOWN')
            row = layout.row()
            row.active = not selected_action.is_playing
            if ActRec_pref.local_record_macros:
                row.scale_y = 2
                row.operator("ar.local_record", text='Stop')
            else:
                row2 = row.row(align=True)
                row2.operator("ar.local_record", text='Record', icon='REC')
                row2.operator("ar.local_clear", text='Clear')
                col = layout.column()
                row = col.row()
                row.scale_y = 2
                row.operator("ar.local_play", text="Playing..." if selected_action.is_playing else "Play")
                col.operator("ar.local_to_global", text='Local to Global')
                row = col.row(align=True)
                row.enabled = bpy.ops.ar.local_to_global.poll()
                row.prop(ActRec_pref, 'local_to_global_mode', expand=True)
    AR_PT_macro.__name__ = "AR_PT_macro_%s" % space_type

    class AR_PT_global(Panel):
        bl_space_type = space_type
        bl_region_type = 'UI'
        bl_category = 'Action Recorder'
        bl_label = 'Global Actions'
        bl_idname = "AR_PT_global_%s" % space_type
        bl_order = 2

        def draw_header(self, context: Context) -> None:
            ActRec_pref = get_preferences(context)
            layout = self.layout
            row = layout.row(align=True)
            row.prop(
                ActRec_pref,
                'global_hide_menu',
                icon='COLLAPSEMENU',
                text="",
                emboss=True
            )

        def draw(self, context: Context) -> None:
            ActRec_pref = get_preferences(context)
            if not ActRec_pref.is_loaded:  # loads the actions if not already done
                ActRec_pref.is_loaded = True
            layout = self.layout
            if not ActRec_pref.global_hide_menu:
                col = layout.column()
                row = col.row()
                row.scale_y = 2
                row.operator("ar.global_to_local", text='Global to Local')
                row = col.row(align=True)
                row.enabled = bpy.ops.ar.global_to_local.poll()
                row.prop(ActRec_pref, 'global_to_local_mode', expand=True)
                row = layout.row().split(factor=0.4)
                row.label(text='Buttons')
                row2 = row.row(align=True)
                row2.operator("ar.global_move_up", text='', icon='TRIA_UP')
                row2.operator("ar.global_move_down", text='', icon='TRIA_DOWN')
                row2.operator(
                    "ar.global_recategorize_action",
                    text='',
                    icon='PRESET'
                )
                row2.operator("ar.global_remove", text='', icon='TRASH')
    AR_PT_global.__name__ = "AR_PT_global_%s" % space_type

    class AR_PT_help(Panel):
        bl_space_type = space_type
        bl_region_type = 'UI'
        bl_category = 'Action Recorder'
        bl_label = 'Help'
        bl_idname = "AR_PT_help_%s" % space_type
        bl_options = {'DEFAULT_CLOSED'}
        bl_order = 3

        def draw_header(self, context: Context) -> None:
            layout = self.layout
            layout.label(icon='INFO')

        def draw(self, context: Context) -> None:
            layout = self.layout
            ActRec_pref = get_preferences(context)
            layout.operator(
                'wm.url_open',
                text="Manual",
                icon='ASSET_MANAGER'
            ).url = config.manual_url
            layout.operator(
                'wm.url_open',
                text="Hint",
                icon='HELP'
            ).url = config.hint_url
            layout.operator(
                'ar.preferences_open_explorer',
                text="Open Log"
            ).path = log_sys.path
            layout.operator(
                'wm.url_open',
                text="Bug Report",
                icon='URL'
            ).url = config.bug_report_url
            layout.operator(
                'wm.url_open',
                text="Release Notes"
            ).url = config.release_notes_url
            row = layout.row()
            if ActRec_pref.update:
                update.draw_update_button(row, ActRec_pref)
            else:
                row.operator('ar.update_check', text="Check For Updates")
                if ActRec_pref.restart:
                    row.operator(
                        'ar.show_restart_menu',
                        text="Restart to Finish"
                    )
            if ActRec_pref.version != '':
                if ActRec_pref.update:
                    layout.label(
                        text="new Version available (%s)" % ActRec_pref.version
                    )
                else:
                    layout.label(text="latest Version (%s)" % ActRec_pref.version)
    AR_PT_help.__name__ = "AR_PT_help_%s" % space_type

    class AR_PT_advanced(Panel):
        bl_space_type = space_type
        bl_region_type = 'UI'
        bl_category = 'Action Recorder'
        bl_label = 'Advanced'
        bl_idname = "AR_PT_advanced_%s" % space_type
        bl_options = {'DEFAULT_CLOSED'}
        bl_order = 4

        def draw(self, context: Context) -> None:
            ActRec_pref = get_preferences(context)
            layout = self.layout
            col = layout.column()
            col.label(text="Category", icon='GROUP')
            row = col.row(align=True)
            row.label(text='')
            row2 = row.row(align=True)
            row2.scale_x = 1.5
            row2.operator("ar.category_move_up", text='', icon='TRIA_UP')
            row2.operator("ar.category_move_down", text='', icon='TRIA_DOWN')
            row2.operator("ar.category_add", text='', icon='ADD')
            row2.operator("ar.category_delete", text='', icon='TRASH')
            row.label(text='')
            row = col.row(align=False)
            row.operator("ar.category_edit", text='Edit')
            row.prop(
                ActRec_pref,
                'show_all_categories',
                text="",
                icon='RESTRICT_VIEW_OFF' if ActRec_pref.show_all_categories else 'RESTRICT_VIEW_ON'
            )
            col.label(text="Data Management", icon='FILE_FOLDER')
            col.operator("ar.global_import", text='Import')
            col.operator("ar.global_export", text='Export')
            col.label(text="Storage File Settings", icon="FOLDER_REDIRECT")
            row = col.row()
            row.label(text="AutoSave")
            row.prop(
                ActRec_pref,
                'autosave',
                toggle=True,
                text="On" if ActRec_pref.autosave else "Off"
            )
            col.operator("ar.global_save", text='Save to File')
            col.operator("ar.global_load", text='Load from File')
            col.label(text="Local Settings")
            row = col.row(align=True)
            row.operator("ar.local_load", text='Load Local Actions')
            row.prop(
                ActRec_pref,
                'hide_local_text',
                text="",
                toggle=True,
                icon="HIDE_ON" if ActRec_pref.hide_local_text else "HIDE_OFF"
            )
            col.prop(
                ActRec_pref,
                'local_create_empty',
                text="Create Empty Macro on Error"
            )
    AR_PT_advanced.__name__ = "AR_PT_advanced_%s" % space_type

    global classes
    classes += [
        AR_PT_local,
        AR_PT_macro,
        AR_PT_global,
        AR_PT_help,
        AR_PT_advanced
    ]
# endregion


# region Registration
for space in ui_space_types:
    panel_factory(space)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)
# endregion
