# region Imports
# external modules
import json
import uuid
import numpy
from typing import TYPE_CHECKING

# blender modules
import bpy
from bpy.types import Operator, Context, Event, AddonPreferences, OperatorProperties, PropertyGroup
from bpy.props import StringProperty, IntProperty, EnumProperty, CollectionProperty

# relative imports
from .. import functions, properties, icon_manager, shared_data
from ..log import logger
from . import shared
from ..functions.shared import get_preferences
if TYPE_CHECKING:
    from ..preferences import AR_preferences
    from ..properties.categories import AR_category
    from ..properties.globals import AR_global_actions
else:
    AR_preferences = AddonPreferences
    AR_category = PropertyGroup
    AR_global_actions = PropertyGroup
# endregion

CONTEXT_REPORT = 0
OPERATOR_REPORT = 1

# region Operators


class AR_OT_local_to_global(Operator):
    bl_idname = "ar.local_to_global"
    bl_label = "Local Action to Global"
    bl_description = "Transfer the selected Action to Global-actions"
    bl_options = {'UNDO'}

    @classmethod
    def poll(cls, context: Context) -> bool:
        ActRec_pref = get_preferences(context)
        return len(ActRec_pref.local_actions) and not ActRec_pref.local_record_macros

    def invoke(self, context: Context, event: Event) -> set[str]:
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context: Context) -> None:
        ActRec_pref = get_preferences(context)
        categories = ActRec_pref.categories
        layout = self.layout
        if len(categories):
            for category in categories:
                layout.prop(category, 'selected', text=category.label)
        else:
            box = layout.box()
            col = box.column()
            col.scale_y = 0.9
            col.label(text='Please add a category first', icon='INFO')
            col.label(text='To do that, go to the advanced menu', icon='BLANK1')

    def local_to_global(
            self,
            ActRec_pref: AR_preferences,
            category: AR_category,
            action: AR_global_actions) -> None:
        """
        copy the given local action to a global action

        Args:
            ActRec_pref (AR_preferences): preferences of this addon
            category (AR_category): category to copy the action to
            action (AR_global_actions): action to copy
        """
        id = uuid.uuid1().hex if action.id in [x.id for x in ActRec_pref.global_actions] else action.id
        data = functions.property_to_python(
            action,
            exclude=["name", "alert", "macros.name", "macros.alert",
                     "macros.is_available", "macros.is_playing", "is_playing"]
        )
        data["id"] = id
        data["selected"] = True
        functions.add_data_to_collection(ActRec_pref.global_actions, data)
        new_action = category.actions.add()
        new_action.id = id

    def execute(self, context: Context) -> set[str]:
        ActRec_pref = get_preferences(context)
        categories = ActRec_pref.categories

        if not len(categories):
            return {'CANCELLED'}

        for category in categories:
            if category.selected:
                self.local_to_global(ActRec_pref, category, ActRec_pref.local_actions
                                     [ActRec_pref.active_local_action_index])
                break
        if ActRec_pref.local_to_global_mode == 'move':
            functions.remove_local_action_from_text(ActRec_pref.local_actions[ActRec_pref.active_local_action_index])
            ActRec_pref.local_actions.remove(ActRec_pref.active_local_action_index)
        functions.save_local_to_scene(ActRec_pref, context.scene)
        if ActRec_pref.autosave:
            functions.save(ActRec_pref)
        context.area.tag_redraw()
        return {"FINISHED"}


class AR_OT_local_add(Operator):
    bl_idname = "ar.local_add"
    bl_label = "Add"
    bl_description = "Add a New Action"
    bl_options = {'UNDO'}

    name: StringProperty(
        name="Name",
        description="Name of the Action",
        default="Untitled"
    )

    @classmethod
    def poll(cls, context: Context) -> bool:
        ActRec_pref = get_preferences(context)
        return not ActRec_pref.local_record_macros

    def execute(self, context: Context) -> set[str]:
        ActRec_pref = get_preferences(context)
        new = ActRec_pref.local_actions.add()
        new.id  # create new id, uses internal getter
        new.label = functions.check_for_duplicates(map(lambda x: x.label, ActRec_pref.local_actions), self.name)
        ActRec_pref.active_local_action_index = -1  # set to last element, uses internal setter
        functions.save_local_to_scene(ActRec_pref, context.scene)
        if not ActRec_pref.hide_local_text:
            functions.local_action_to_text(new)
        context.area.tag_redraw()
        return {"FINISHED"}


class AR_OT_local_remove(shared.Id_based, Operator):
    bl_idname = "ar.local_remove"
    bl_label = "Remove"
    bl_description = "Remove the selected Action"
    bl_options = {'UNDO'}

    @classmethod
    def description(cls, context: Context, properties: OperatorProperties) -> str:
        ActRec_pref = get_preferences(context)
        index = functions.get_local_action_index(ActRec_pref, "", -1)
        label = "NONE"
        if len(ActRec_pref.local_actions):
            label = ActRec_pref.local_actions[index].label
        return "Remove the selected Action\nAction: %s" % (label)

    @classmethod
    def poll(cls, context: Context) -> bool:
        ActRec_pref = get_preferences(context)
        return len(ActRec_pref.local_actions) and not ActRec_pref.local_record_macros

    def execute(self, context) -> set[str]:
        ActRec_pref = get_preferences(context)
        index = functions.get_local_action_index(ActRec_pref, self.id, self.index)
        self.clear()
        if index == -1:
            self.report({'ERROR'}, "Selected Action couldn't be deleted")
            return {"CANCELLED"}
        else:
            functions.remove_local_action_from_text(ActRec_pref.local_actions[index])
            ActRec_pref.local_actions.remove(index)
        functions.save_local_to_scene(ActRec_pref, context.scene)
        context.area.tag_redraw()
        return {"FINISHED"}


class AR_OT_local_move_up(shared.Id_based, Operator):
    bl_idname = "ar.local_move_up"
    bl_label = "Move Up"
    bl_description = "Move the selected Action up"
    bl_options = {'UNDO'}

    ignore_selection = False

    @classmethod
    def poll(cls, context: Context) -> bool:
        ActRec_pref = get_preferences(context)
        ignore = cls.ignore_selection
        cls.ignore_selection = False
        return (
            len(ActRec_pref.local_actions) >= 2
            and (ignore or ActRec_pref.active_local_action_index - 1 >= 0)
            and not ActRec_pref.local_record_macros
        )

    def execute(self, context: Context) -> set[str]:
        ActRec_pref = get_preferences(context)
        index = functions.get_local_action_index(ActRec_pref, self.id, self.index)
        self.clear()
        if index == -1 or index - 1 < 0:
            self.report({'ERROR'}, "Selected Action couldn't be moved")
            return {"CANCELLED"}
        else:
            ActRec_pref.local_actions.move(index, index - 1)
            ActRec_pref.active_local_action_index -= 1
        functions.save_local_to_scene(ActRec_pref, context.scene)
        context.area.tag_redraw()
        return {"FINISHED"}

    def cancel(self, context: Context) -> None:
        self.clear()


class AR_OT_local_move_down(shared.Id_based, Operator):
    bl_idname = "ar.local_move_down"
    bl_label = "Move Down"
    bl_description = "Move the selected Action Down"
    bl_options = {'UNDO'}

    ignore_selection = False

    @classmethod
    def poll(cls, context: Context) -> bool:
        ActRec_pref = get_preferences(context)
        ignore = cls.ignore_selection
        cls.ignore_selection = False
        return (
            len(ActRec_pref.local_actions) >= 2
            and (ignore or ActRec_pref.active_local_action_index + 1 < len(ActRec_pref.local_actions))
            and not ActRec_pref.local_record_macros
        )

    def execute(self, context: Context) -> set[str]:
        ActRec_pref = get_preferences(context)
        index = functions.get_local_action_index(ActRec_pref, self.id, self.index)
        self.clear()
        if index == -1 or index + 1 >= len(ActRec_pref.local_actions):
            self.report({'ERROR'}, "Selected Action couldn't be moved")
            return {"CANCELLED"}
        else:
            ActRec_pref.local_actions.move(index, index + 1)
            ActRec_pref.active_local_action_index += 1
        functions.save_local_to_scene(ActRec_pref, context.scene)
        context.area.tag_redraw()
        return {"FINISHED"}

    def cancel(self, context: Context) -> None:
        self.clear()


class AR_OT_local_load(Operator):
    bl_idname = "ar.local_load"
    bl_label = "Load Local Actions"
    bl_description = "Load the Local Action from the last Save"
    bl_options = {'UNDO'}

    source: EnumProperty(
        name='Source',
        description="Choose the source from where to load",
        items=[('scene', 'Scene', ''), ('text', 'Texteditor', '')]
    )
    texts: CollectionProperty(type=properties.AR_local_load_text)

    @classmethod
    def poll(cls, context: Context) -> bool:
        ActRec_pref = get_preferences(context)
        return not ActRec_pref.local_record_macros and not ActRec_pref.local_record_macros

    def invoke(self, context: Context, event: Event) -> set[str]:
        texts = self.texts
        texts.clear()
        for text in bpy.data.texts:
            if text.lines[0].body.strip().startswith("###ActRec_pref###"):
                txt = texts.add()
                txt.name = text.name
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context: Context) -> None:
        layout = self.layout
        layout.prop(self, 'source', expand=True)
        if self.source != 'text':
            return
        box = layout.box()
        texts = [txt.name for txt in bpy.data.texts]
        for text in self.texts:
            if text.name not in texts:
                continue
            row = box.row()
            row.label(text=text.name)
            row.prop(text, 'apply', text='')

    def execute(self, context: Context) -> set[str]:
        ActRec_pref = get_preferences(context)
        logger.info("Load Local Actions")
        if self.source == 'scene':
            data = json.loads(context.scene.ar.local)
            if not isinstance(data, list):
                self.report({'ERROR'}, "scene data couldn't be loaded")
                return {'CANCELLED'}
        else:
            data = []
            for text in self.texts:
                if not text.apply:
                    continue
                if bpy.data.texts.find(text.name) == -1:
                    continue
                text = bpy.data.texts[text.name]
                lines = [line.body for line in text.lines]
                header = {}
                for prop in lines[0].split("#")[-1].split(","):
                    key, value = prop.split(":")
                    header[key.strip()] = eval(value.strip())
                macros = []
                for line in lines[1:]:
                    split_line = line.split("#")
                    macro = {'command': "#".join(split_line[:-1])}
                    for prop in split_line[-1].split(","):
                        key, value = prop.split(":")
                        macro[key.strip()] = eval(value.strip())
                    macros.append(macro)
                data.append({'label': text.name, 'id': header['id'], 'macros': macros, 'icon': header['icon']})
        functions.load_local_action(ActRec_pref, data)
        functions.save_local_to_scene(ActRec_pref, context.scene)
        if not ActRec_pref.hide_local_text:
            for action in ActRec_pref.local_actions:
                functions.local_action_to_text(action)
        context.area.tag_redraw()
        self.cancel(context)
        return {"FINISHED"}

    def cancel(self, context: Context) -> None:
        self.texts.clear()


class AR_OT_local_selection_up(Operator):
    bl_idname = 'ar.local_selection_up'
    bl_label = 'ActRec Selection Up'
    bl_options = {'UNDO'}

    @classmethod
    def poll(cls, context: Context) -> bool:
        ActRec_pref = get_preferences(context)
        return len(ActRec_pref.local_actions)

    def execute(self, context: Context) -> set[str]:
        ActRec_pref = get_preferences(context)
        if ActRec_pref.active_local_action_index - 1 >= 0:
            ActRec_pref.active_local_action_index = ActRec_pref.active_local_action_index - 1
            context.area.tag_redraw()
        return {'FINISHED'}


class AR_OT_local_selection_down(Operator):
    bl_idname = 'ar.local_selection_down'
    bl_label = 'ActRec Selection Down'
    bl_options = {'UNDO'}

    @classmethod
    def poll(cls, context: Context) -> bool:
        ActRec_pref = get_preferences(context)
        return len(ActRec_pref.local_actions)

    def execute(self, context: Context) -> set[str]:
        ActRec_pref = get_preferences(context)
        if ActRec_pref.active_local_action_index + 1 < len(ActRec_pref.local_actions):
            ActRec_pref.active_local_action_index = ActRec_pref.active_local_action_index + 1
            context.area.tag_redraw()
        return {'FINISHED'}


class AR_OT_local_play(shared.Id_based, Operator):
    bl_idname = 'ar.local_play'
    bl_label = 'ActRec Play'
    bl_description = 'Play the selected Action.'
    bl_options = {'REGISTER', 'UNDO'}

    ignore_selection = False

    @classmethod
    def poll(cls, context: Context) -> bool:
        ActRec_pref = get_preferences(context)
        ignore = cls.ignore_selection
        cls.ignore_selection = False
        return (
            len(ActRec_pref.local_actions)
            and (len(ActRec_pref.local_actions[ActRec_pref.active_local_action_index].macros) or ignore)
            and not ActRec_pref.local_record_macros
        )

    def execute(self, context: Context) -> set[str]:
        ActRec_pref = get_preferences(context)
        index = functions.get_local_action_index(ActRec_pref, self.id, self.index)
        action = ActRec_pref.local_actions[index]
        if action.is_playing:
            self.report({'INFO'}, "The action is already playing!")
            return {'CANCELLED'}
        err = functions.play(context, action.macros, action, 'local_actions')
        if err:
            self.report({'ERROR'}, str(err))
        # Ensure is_playing is always reset, even if the play function didn't reset it
        action.is_playing = False
        self.clear()
        return {'FINISHED'}


class AR_OT_local_record(shared.Id_based, Operator):
    bl_idname = "ar.local_record"
    bl_label = "Start/Stop Recording"
    bl_options = {'UNDO'}

    ignore_selection = False
    record_start_index: IntProperty()

    @classmethod
    def description(cls, context: Context, properties: OperatorProperties) -> str:
        ActRec_pref = get_preferences(context)
        if ActRec_pref.local_record_macros:
            return "Stops Recording the Macros"
        return "Starts Recording the Macros"

    @classmethod
    def poll(cls, context: Context) -> bool:
        ActRec_pref = get_preferences(context)
        return len(ActRec_pref.local_actions)

    def execute(self, context: Context) -> set[str]:
        ActRec_pref = get_preferences(context)
        index = functions.get_local_action_index(ActRec_pref, self.id, self.index)
        action = ActRec_pref.local_actions[index]

        if action.is_playing:
            self.report({'INFO'}, "The action is playing and can not be edited!")
            return {'CANCELLED'}

        ActRec_pref.local_record_macros = not ActRec_pref.local_record_macros
        if ActRec_pref.local_record_macros:  # start recording
            self.id = action.id
            self.index = index
            self.record_start_index = functions.get_report_text(context).count('\n')
            context.scene.ar.record_undo_end = not context.scene.ar.record_undo_end
            return {"FINISHED"}

        # end recording and add reports as macros
        reports = functions.get_report_text(context).splitlines()[self.record_start_index:]
        reports = [report for report in reports if report.startswith('bpy.')]
        if not len(reports):
            self.clear()
            return {"FINISHED"}
        reports = numpy.array(functions.merge_report_tracked(reports, shared_data.tracked_actions), dtype=object)
        shared_data.tracked_actions.clear()
        logger.info("Record Reports: %s", reports)

        record_undo_end = context.scene.ar.record_undo_end
        redo_steps = 0
        while record_undo_end == bpy.context.scene.ar.record_undo_end and bpy.ops.ed.undo.poll():
            bpy.ops.ed.undo()
            redo_steps += 1
        context = bpy.context
        i = 0

        data = []
        skip_op_redo = True
        len_reports = len(reports)
        while bpy.ops.ed.redo.poll() and redo_steps > 0 and len_reports > i:
            bpy_type, register, undo, parent, name, value = reports[i]
            if bpy_type == CONTEXT_REPORT:
                # register, undo are always True for Context reports
                copy_dict = functions.create_object_copy(context, parent, name)
                if bpy.ops.ed.redo.poll():
                    bpy.ops.ed.redo()
                    redo_steps -= 1
                    context = bpy.context

                if bpy.ops.ed.redo.poll() and copy_dict == functions.create_object_copy(context, parent, name):
                    bpy.ops.ed.redo()
                    redo_steps -= 1
                    context = bpy.context

                data.append(functions.improve_context_report(context, copy_dict, parent, name, value))

                if not skip_op_redo and bpy.ops.ed.undo.poll():
                    bpy.ops.ed.undo()
                    redo_steps += 1
                    context = bpy.context

            elif bpy_type == OPERATOR_REPORT:
                if register:
                    evaluation = functions.evaluate_operator(parent, name, value)

                if len_reports > i + 1:
                    skip_op_redo = reports[i + 1][0] == 1
                else:
                    skip_op_redo = True
                if undo and skip_op_redo and bpy.ops.ed.redo.poll():
                    bpy.ops.ed.redo()
                    redo_steps -= 1
                    context = bpy.context

                if register:
                    data.append(functions.improve_operator_report(context, parent, name, value, evaluation))
            i += 1

        while redo_steps > 0 and bpy.ops.ed.redo.poll():
            bpy.ops.ed.redo()
        context = bpy.context

        error_reports = []
        action = ActRec_pref.local_actions[index]
        for report in data:
            functions.add_report_as_macro(context, ActRec_pref, action, report, error_reports)
        if error_reports:
            self.report({'ERROR'}, "Not all reports could be added added:\n%s" % "\n".join(error_reports))
        functions.save_local_to_scene(ActRec_pref, bpy.context.scene)
        if not ActRec_pref.hide_local_text:
            functions.local_action_to_text(action)
        context.area.tag_redraw()
        self.clear()
        return {"FINISHED"}


class AR_OT_local_icon(icon_manager.Icontable, shared.Id_based, Operator):
    bl_idname = "ar.local_icon"
    bl_options = {'UNDO'}

    @classmethod
    def poll(cls, context: Context) -> bool:
        ActRec_pref = get_preferences(context)
        return not ActRec_pref.local_record_macros

    def invoke(self, context: Context, event: Event) -> set[str]:
        ActRec_pref = get_preferences(context)
        index = functions.get_local_action_index(ActRec_pref, self.id, self.index)
        action = ActRec_pref.local_actions[index]
        self.id = action.id
        if not self.reuse:
            ActRec_pref.selected_icon = action.icon
        self.search = ''
        return context.window_manager.invoke_props_dialog(self, width=1000)

    def execute(self, context: Context) -> set[str]:
        ActRec_pref = get_preferences(context)
        action = ActRec_pref.local_actions[self.id]
        action.icon = ActRec_pref.selected_icon
        ActRec_pref.selected_icon = 0  # Icon: NONE
        self.reuse = False
        functions.save_local_to_scene(ActRec_pref, context.scene)
        if not ActRec_pref.hide_local_text:
            functions.local_action_to_text(action)
        context.area.tag_redraw()
        self.clear()
        return {"FINISHED"}


class AR_OT_local_clear(shared.Id_based, Operator):
    bl_idname = "ar.local_clear"
    bl_label = "Clear Macros"
    bl_description = "Delete all Macros of the selected Action"
    bl_options = {'UNDO'}

    ignore_selection = False

    @classmethod
    def poll(cls, context: Context) -> bool:
        ActRec_pref = get_preferences(context)
        ignore = cls.ignore_selection
        cls.ignore_selection = False
        return (
            len(ActRec_pref.local_actions)
            and (len(ActRec_pref.local_actions[ActRec_pref.active_local_action_index].macros) or ignore)
            and not ActRec_pref.local_record_macros
        )

    def execute(self, context: Context) -> set[str]:
        ActRec_pref = get_preferences(context)
        index = functions.get_local_action_index(ActRec_pref, self.id, self.index)
        action = ActRec_pref.local_actions[index]

        if action.is_playing:
            self.report({'INFO'}, "The action is playing and can not be edited!")
            return {'CANCELLED'}

        action.macros.clear()
        functions.save_local_to_scene(ActRec_pref, context.scene)
        if not ActRec_pref.hide_local_text:
            functions.local_action_to_text(action)
        bpy.context.area.tag_redraw()
        self.clear()
        return {"FINISHED"}
# endregion


classes = [
    AR_OT_local_to_global,
    AR_OT_local_add,
    AR_OT_local_remove,
    AR_OT_local_move_up,
    AR_OT_local_move_down,
    AR_OT_local_load,
    AR_OT_local_selection_up,
    AR_OT_local_selection_down,
    AR_OT_local_play,
    AR_OT_local_record,
    AR_OT_local_icon,
    AR_OT_local_clear
]

# region Registration


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)
# endregion
