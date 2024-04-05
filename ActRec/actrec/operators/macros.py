# region Imports
# external modules
import importlib
import json
import time
import numpy
import threading
from typing import Optional
from logging import Logger

# blender modules
import bpy
from bpy.types import Operator, PointerProperty, UILayout, Context, Event
from bpy.props import StringProperty, IntProperty, EnumProperty, CollectionProperty, FloatProperty, BoolProperty
from idprop.types import IDPropertyArray

# relative imports
from . import shared
from .. import functions, properties, shared_data
from ..log import logger
from ..functions.shared import get_preferences
# endregion

# region Operators


class Macro_based(shared.Id_based):
    action_index: IntProperty(default=-1)
    ignore_selection = False

    def clear(self) -> None:
        self.action_index = -1
        super().clear()


class AR_OT_macro_add(shared.Id_based, Operator):
    bl_idname = "ar.macro_add"
    bl_label = "ActRec Add Macro"
    bl_description = "Add the last operation you executed"
    bl_options = {'UNDO'}

    command: StringProperty(default="")
    report_length: IntProperty(default=0)

    @classmethod
    def poll(cls, context: Context) -> bool:
        ActRec_pref = get_preferences(context)
        return not ActRec_pref.local_record_macros

    def execute(self, context: Context) -> set[str]:
        ActRec_pref = get_preferences(context)

        if not len(ActRec_pref.local_actions):
            self.report({'ERROR'}, 'Add a local action first')
            return {'CANCELLED'}

        index = functions.get_local_action_index(ActRec_pref, self.id, self.index)
        action = ActRec_pref.local_actions[index]

        if action.is_playing:
            self.report({'INFO'}, "The action is playing and can not be edited!")
            return {'CANCELLED'}

        new_report = False
        command = None

        if not self.command:  # get the command from the latest Blender report
            reports = functions.get_report_text(context).splitlines()
            length = len(reports)
            if self.report_length != length:
                new_report = True
                self.report_length = length
                reports.reverse()
                for report in reports:
                    if report.startswith(("bpy.ops.", "bpy.context.")):
                        command = report
                        break
        else:  # command was passed through with the operator parameter
            new_report = True
            command = self.command

        undo_count = 0
        # improve command by comparing to tracked_actions
        # tracked actions is written by the function track_scene in functions.macros
        # which keeps track of all executed Operator in detail but none information about changed Properties
        if command and (new_report or ActRec_pref.last_macro_command != command):
            if command.startswith("bpy.context."):
                tracked_actions = []
                if not self.command:
                    tracked_actions = numpy.array(shared_data.tracked_actions)[::-1]
                    i = 0
                    len_tracked = len(tracked_actions)
                    while i < len_tracked and tracked_actions[i][2] != "CONTEXT":
                        i += 1
                    tracked_actions = tracked_actions[:i + 1]
                reports = functions.merge_report_tracked([command], tracked_actions)
                logger.info("Record Report: %s" % reports)

                # tries to recover more data of changed Properties
                # by creating a copy of former data and try to match and complete it with the active data
                for bpy_type, register, undo, parent, name, value in reports:
                    if not bpy.ops.ed.undo.poll():
                        break

                    copy_dict = functions.create_object_copy(context, parent, name)

                    bpy.ops.ed.undo()
                    undo_count += 1
                    context = bpy.context

                    ret = functions.improve_context_report(context, copy_dict, parent, name, value)
                    if not undo:  # revert redo if report didn't triggered any undo save
                        bpy.ops.ed.redo()
                        undo_count -= 1
                    if ret:
                        command = ret
                        break

            elif command.startswith("bpy.ops."):
                ops_type, ops_name, ops_values = functions.split_operator_report(command)
                if not self.command:
                    tracked_actions = numpy.array(shared_data.tracked_actions)[::-1]
                    i = 0
                    len_tracked = len(tracked_actions)
                    if len_tracked > i:
                        tracked = tracked_actions[i]
                        i += 1
                        # compare tracked operator data with the command operator data
                        while (not (tracked[2] == "%s_OT_%s" % (ops_type.upper(), ops_name)
                                    and functions.compare_op_dict(ops_values, tracked[3]))
                               and len_tracked > i):
                            tracked = tracked_actions[i]
                            i += 1
                    reports = functions.merge_report_tracked([command], tracked_actions[:i + 1])
                    logger.info("Record Report: %s" % reports)
                else:  # convert command to simple incase the command was passthrough with the operator
                    bl_options = getattr(getattr(bpy.ops, ops_type), ops_name).bl_options
                    reports = [(1, "REGISTER" in bl_options, "UNDO" in bl_options, ops_type, ops_name, ops_values)]

                # catch operators that won't work with simple calls, because they need a specific selection
                # these operators will be replaced by self written Operators with similar behavior
                for bpy_type, register, undo, parent, name, value in reports:
                    if register:
                        evaluation = functions.evaluate_operator(parent, name, value)
                        ret = functions.improve_operator_report(context, parent, name, value, evaluation)
                        if ret:
                            command = ret
                            break

            # redo all undo actions which where taken during the improve process
            while undo_count > 0:
                bpy.ops.ed.redo()
                undo_count -= 1

            ui_type = ""
            if context.area:
                ui_type = context.area.ui_type
            functions.add_report_as_macro(context, ActRec_pref, action, command, [], ui_type)
        else:
            if new_report:
                self.report({'ERROR'}, "No Action could be added")
            if ActRec_pref.local_create_empty:
                macro = action.macros.add()
                macro.label = "<Empty>"
                macro.command = ""
                action.active_macro_index = -1
                bpy.ops.ar.macro_edit('INVOKE_DEFAULT', index=index, edit=True)

        functions.save_local_to_scene(ActRec_pref, context.scene)
        if not ActRec_pref.hide_local_text:
            functions.local_action_to_text(action)
        bpy.context.area.tag_redraw()
        shared_data.tracked_actions.clear()
        self.command = ""
        return {"FINISHED"}


class AR_OT_macro_add_event(shared.Id_based, Operator):
    bl_idname = "ar.macro_add_event"
    bl_label = "Add Event"
    bl_description = "Add a Event to the selected Action"
    bl_options = {'UNDO'}

    types = [
        ('Timer', 'Timer', 'Wait the chosen Time and continue with the next macros', 'SORTTIME', 0),
        ('Render Complete', 'Render Complete',
         '''Waits for the render process to be completed and execute the next macros\n
         WARNING: Macros executed after this might crash Blender''', 'IMAGE_RGB_ALPHA', 1),
        ('Loop', 'Loop',
         '''Add before the macro to Loop\n
         Note: The Loop need the EndLoop Event to work, otherwise the Event get skipped''',
         'FILE_REFRESH', 3),
        ('EndLoop', 'EndLoop', 'Ending the latest called loop, when no Loop Event was called this Event get skipped',
         'FILE_REFRESH', 4),
        ('Clipboard', 'Clipboard', 'Paste and add the macro currently on the clipboard', 'CONSOLE', 5),
        ('Select Object', 'Select Object', 'Select the chosen objects', 'OBJECT_DATA', 7),
        ('Run Script', 'Run Script',
         'Choose a Text file that gets saved into the macro and executed', 'FILE_SCRIPT', 8)]
    type: EnumProperty(items=types, name="Event Type", description='Shows all possible Events', default='Clipboard')

    time: FloatProperty(name="Time", description="Time in Seconds", unit='TIME')
    statement_type: EnumProperty(
        default='repeat',
        items=[
            ('repeat', 'Repeat', 'Repeat the given count', '', 0),
            ('python', 'Python Statement', 'Create a custom statement with python code', '', 1)
        ]
    )
    repeat_count: IntProperty(name='Count', min=0, default=1, description="How many times the Loop gets repeated")
    python_statement: StringProperty(name="Statement", description="Statement to be evaluated as python code")
    object: StringProperty(
        name="Active",
        description="Choose an Object which get select and set as active when this Event is played",
        default=""
    )
    objects: CollectionProperty(type=properties.AR_event_object_name)
    keep_selection: BoolProperty(
        name="Keep Selection",
        description="Select the specified objects and keep the current selected objects selected",
        default=False
    )
    script_name: StringProperty(name="Text", description="Chose a Text to convert into a macro script")

    macro_index: IntProperty(name="Macro Index", default=-1)

    @classmethod
    def poll(cls, context: Context) -> bool:
        ActRec_pref = get_preferences(context)
        return len(ActRec_pref.local_actions) and not ActRec_pref.local_record_macros

    def invoke(self, context: Context, event: Event) -> set[str]:
        if self.object == "" and context.object is not None and len(self.objects) == 0:
            self.object = context.object.name
        if len(self.objects) == 0:
            self.objects.add()
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context: Context) -> None:
        layout = self.layout
        layout.prop(self, 'type')
        if self.type == 'Timer':
            box = layout.box()
            box.prop(self, 'time')
        elif self.type == 'Loop':
            box = layout.box()
            box.prop(self, 'statement_type', text="Type")
            box.separator()
            if self.statement_type == 'python':
                box.prop(self, 'python_statement')
            else:
                box.prop(self, 'repeat_count')
        elif self.type == 'Select Object':
            box = layout.box()
            box.prop(self, 'keep_selection')
            box.prop_search(self, 'object', context.view_layer, 'objects')
            box.separator()
            for object in self.objects:
                box.prop_search(object, 'name', context.view_layer, 'objects')
        elif self.type == 'Run Script':
            box = layout.box()
            row = box.row()
            row.prop_search(self, 'script_name', bpy.data, 'texts', results_are_suggestions=True)
            op = row.operator('ar.macro_event_load_script', icon='IMPORT', text="")
            op.id = self.id
            op.index = self.index
            op.macro_index = self.macro_index

    def check(self, context: Context) -> None:
        while (index := self.objects.find("")) >= 0:
            self.objects.remove(index)
        self.objects.add()

    def execute(self, context: Context) -> set[str]:
        ActRec_pref = get_preferences(context)
        index = functions.get_local_action_index(ActRec_pref, self.id, self.index)
        action = ActRec_pref.local_actions[index]

        if action.is_playing:
            self.report({'INFO'}, "The action is playing and can not be edited!")
            return {'CANCELLED'}

        if self.macro_index == -1:
            macro = action.macros.add()
        else:
            macro = action.macros[self.macro_index]
            self.macro_index = -1

        if self.type == 'Clipboard':
            clipboard = context.window_manager.clipboard.replace("\n", "")
            name = functions.get_name_of_command(context, clipboard)
            macro.label = name if isinstance(name, str) else clipboard
            macro.command = clipboard
        else:
            macro.label = "Event: %s" % self.type
            data = {'Type': self.type}
            if self.type == 'Timer':
                data['Time'] = self.time
            elif self.type == 'Loop':
                data['StatementType'] = self.statement_type
                if self.statement_type == 'python':
                    data["PyStatement"] = self.python_statement
                else:
                    data["RepeatCount"] = self.repeat_count
            elif self.type == 'Select Object':
                data['Object'] = self.object
                data['Objects'] = [obj.name for obj in self.objects]
                data['KeepSelection'] = self.keep_selection
            elif self.type == 'Run Script':
                text: bpy.types.Text = bpy.data.texts.get(self.script_name)
                if text is None:
                    data['ScriptName'] = self.script_name
                    if self.script_name != "" and macro.command.startswith("ar.event:"):
                        split = macro.command.split(":")
                        old_data = json.loads(":".join(split[1:]))
                        data['ScriptText'] = old_data.get('ScriptText', "")
                    else:
                        data['ScriptText'] = "# No script with this name was available during initialization"
                else:
                    data['ScriptName'] = text.name.replace("[ActRec Macro]", "").strip()
                    data['ScriptText'] = "\n".join(line.body for line in text.lines)
            macro.command = "ar.event: %s" % json.dumps(data)
        functions.save_local_to_scene(ActRec_pref, context.scene)
        if not ActRec_pref.hide_local_text:
            functions.local_action_to_text(action)
        context.area.tag_redraw()
        self.clear()
        return {"FINISHED"}

    def clear(self) -> None:
        self.object = ""
        self.objects.clear()
        super().clear()


class AR_OT_macro_event_load_script(Macro_based, Operator):
    bl_idname = 'ar.macro_event_load_script'
    bl_label = 'Load Text to Text Editor'
    bl_description = "Loads the Text of this macro into the Texteditor"

    macro_index: IntProperty(name="Macro Index", default=-1)

    def execute(self, context: Context) -> set[str]:
        if self.macro_index < 0:
            self.clear()
            return {'CANCELLED'}

        ActRec_pref = functions.get_preferences(context)
        action_index = functions.get_local_action_index(ActRec_pref, '', self.action_index)
        action = ActRec_pref.local_actions[action_index]

        if self.macro_index >= len(action.macros):
            self.clear()
            return {'CANCELLED'}
        macro = action.macros[self.macro_index]
        self.macro_index = -1

        split = macro.command.split(":")
        if split[0] != 'ar.event':
            self.clear()
            return {'CANCELLED'}

        data = json.loads(":".join(split[1:]))
        if data['Type'] != 'Run Script':
            self.clear()
            return {'CANCELLED'}

        text_name = data['ScriptName']
        if bpy.data.texts.find(text_name) != -1:
            text_name = "%s [ActRec Macro]" % data['ScriptName']
        text = bpy.data.texts.get(text_name)
        if text is None:
            text = bpy.data.texts.new(text_name)
        text.clear()
        text.write(data['ScriptText'])
        return {'FINISHED'}


class AR_OT_macro_remove(Macro_based, Operator):
    bl_idname = "ar.macro_remove"
    bl_label = "Remove Macro"
    bl_description = "Remove the selected Macro"
    bl_options = {'UNDO'}

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
        action_index = functions.get_local_action_index(ActRec_pref, '', self.action_index)
        action = ActRec_pref.local_actions[action_index]

        if action.is_playing:
            self.report({'INFO'}, "The action is playing and can not be edited!")
            return {'CANCELLED'}

        index = functions.get_local_macro_index(action, self.id, self.index)
        action.macros.remove(index)
        functions.save_local_to_scene(ActRec_pref, context.scene)
        if not ActRec_pref.hide_local_text:
            functions.local_action_to_text(action)
        context.area.tag_redraw()
        self.clear()
        return {"FINISHED"}


class AR_OT_macro_move_up(Macro_based, Operator):
    bl_idname = "ar.macro_move_up"
    bl_label = "Move Macro Up"
    bl_description = "Move the selected Macro up"
    bl_options = {'UNDO'}

    @classmethod
    def poll(cls, context: Context) -> bool:
        ActRec_pref = get_preferences(context)
        ignore = cls.ignore_selection
        cls.ignore_selection = False
        if not len(ActRec_pref.local_actions):
            return False
        action = ActRec_pref.local_actions[ActRec_pref.active_local_action_index]
        return ((len(action.macros) >= 2 and action.active_macro_index - 1 >= 0 or ignore)
                and not ActRec_pref.local_record_macros)

    def execute(self, context: Context) -> set[str]:
        ActRec_pref = get_preferences(context)
        action_index = functions.get_local_action_index(ActRec_pref, '', self.action_index)
        action = ActRec_pref.local_actions[action_index]

        if action.is_playing:
            self.report({'INFO'}, "The action is playing and can not be edited!")
            return {'CANCELLED'}

        index = functions.get_local_macro_index(action, self.id, self.index)
        self.clear()
        if index == -1 or index - 1 < 0:
            self.report({'ERROR'}, "Selected Action couldn't be moved")
            return {"CANCELLED"}
        else:
            action.macros.move(index, index - 1)
            action.active_macro_index = index - 1
        functions.save_local_to_scene(ActRec_pref, context.scene)
        if not ActRec_pref.hide_local_text:
            functions.local_action_to_text(action)
        context.area.tag_redraw()
        return {"FINISHED"}


class AR_OT_macro_move_down(Macro_based, Operator):
    bl_idname = "ar.macro_move_down"
    bl_label = "Move Macro Down"
    bl_description = "Move the selected Macro down"
    bl_options = {'UNDO'}

    @classmethod
    def poll(cls, context: Context) -> bool:
        ActRec_pref = get_preferences(context)
        ignore = cls.ignore_selection
        cls.ignore_selection = False
        if not len(ActRec_pref.local_actions):
            return False
        action = ActRec_pref.local_actions[ActRec_pref.active_local_action_index]
        return ((len(action.macros) >= 2 and action.active_macro_index + 1 < len(action.macros) or ignore)
                and not ActRec_pref.local_record_macros)

    def execute(self, context: Context) -> set[str]:
        ActRec_pref = get_preferences(context)
        action_index = functions.get_local_action_index(ActRec_pref, '', self.action_index)
        action = ActRec_pref.local_actions[action_index]

        if action.is_playing:
            self.report({'INFO'}, "The action is playing and can not be edited!")
            return {'CANCELLED'}

        index = functions.get_local_macro_index(action, self.id, self.index)
        self.clear()
        if index == -1 or index + 1 >= len(action.macros):
            self.report({'ERROR'}, "Selected Action couldn't be moved")
            return {"CANCELLED"}
        else:
            action.macros.move(index, index + 1)
            action.active_macro_index = index + 1
        functions.save_local_to_scene(ActRec_pref, context.scene)
        if not ActRec_pref.hide_local_text:
            functions.local_action_to_text(action)
        context.area.tag_redraw()
        return {"FINISHED"}


class Font_analysis():
    def __init__(self, font_path: str) -> None:
        self.path = font_path

        if importlib.util.find_spec('fontTools') is None:
            self.use_dynamic_text = False
            return

        self.use_dynamic_text = True

        if not (self.path.endswith(".ttf") or self.path.endswith(".woff2")):
            self.use_dynamic_text = False
            logger.error("Couldn't use selected font because it's not a .ttf or .woff2\nFILE: %s" % self.path)
            return

        from fontTools.ttLib import TTFont

        font = TTFont(self.path)
        self.t = font['cmap'].getcmap(3, 1).cmap
        self.s = font.getGlyphSet()
        self.units_per_em = font['head'].unitsPerEm

    @classmethod
    def is_installed(cls) -> bool:

        return (
            importlib.util.find_spec('fontTools') is not None
            and (bpy.app.version < (3, 4, 0) or importlib.util.find_spec('brotli'))
        )

    @classmethod
    def install(cls, logger: Logger) -> bool:
        """
        install fonttools to blender modules if not installed

        Returns:
            bool: success
        """
        if bpy.app.version >= (3, 4, 0):
            # Blender 3.4 uses woff2 therefore the package brotli is required
            if importlib.util.find_spec('fontTools') is None or importlib.util.find_spec('brotli') is None:
                success, output = functions.install_packages('fontTools', 'brotli')
                if success:
                    logger.info(output)
                else:
                    logger.warning(output)

            if importlib.util.find_spec('fontTools') is None or importlib.util.find_spec('brotli') is None:
                logger.warning("For some reason fontTools or brotli couldn't be installed :(")
                return False
        else:
            if importlib.util.find_spec('fontTools') is None:
                success, output = functions.install_packages('fontTools')
                if success:
                    logger.info(output)
                else:
                    logger.warning(output)

            if importlib.util.find_spec('fontTools') is None:
                logger.warning("For some reason fontTools couldn't be installed :(")
                return False
        return True

    def get_width_of_text(self, context: Context, text: str) -> list[float]:
        """
        get the width of each character of the text in pixels,
        because Blender uses Pixel for measurement of window width

        Args:
            context (Context): active blender context
            text (str): text to get width from

        Returns:
            list[float]: width for each character in the text
        """
        total = []
        font_style = context.preferences.ui_styles[0].widget
        for c in text:
            total.append(self.s[self.t[ord(c)]].width * font_style.points/self.units_per_em)
        return total


class AR_OT_macro_multiline_support(Operator):
    bl_idname = "ar.macro_multiline_support"
    bl_label = "Multiline Support"
    bl_options = {'INTERNAL'}
    bl_description = "Adds multiline support the edit macro dialog"

    def invoke(self, context: Context, event: Event) -> set[str]:
        return context.window_manager.invoke_props_dialog(self, width=350)

    def draw(self, context: Context) -> None:
        ActRec_pref = get_preferences(context)
        layout = self.layout

        if Font_analysis.is_installed():
            layout.label(text="Support Enabled")
            return

        layout.label(text="Do you want to install multiline support?")
        if bpy.app.version >= (3, 4, 0):
            layout.label(text="This requires the fontTools, brotli package to be installed.")
        else:
            layout.label(text="This requires the fontTools package to be installed.")
        row = layout.row()
        if ActRec_pref.multiline_support_installing:
            if bpy.app.version >= (3, 4, 0):
                row.label(text="Installing fontTools, brotli...")
            else:
                row.label(text="Installing fontTools...")
        else:
            row.operator('ar.macro_install_multiline_support', text="Install")
            row.prop(ActRec_pref, 'multiline_support_dont_ask')

    def execute(self, context: Context) -> set[str]:
        bpy.ops.ar.macro_edit("INVOKE_DEFAULT", edit=True, multiline_asked=True)
        return {'FINISHED'}

    def cancel(self, context: Context) -> None:
        # Also recall when done is not clicked
        bpy.ops.ar.macro_edit("INVOKE_DEFAULT", edit=True, multiline_asked=True)


class AR_OT_macro_install_multiline_support(Operator):
    """
    Try's to install the package fonttools
    to get the width of the given command and split it into multiple lines
    """
    bl_idname = "ar.macro_install_multiline_support"
    bl_label = "Install Multiline Support"
    bl_options = {'INTERNAL'}

    success = []

    @classmethod
    def poll(cls, context: Context) -> bool:
        ActRec_pref = get_preferences(context)
        return not ActRec_pref.multiline_support_installing

    def invoke(self, context: Context, event: Event) -> set[str]:
        def install(success: list, logger):
            success.append(Font_analysis.install(logger))

        self.success.clear()
        ActRec_pref = get_preferences(context)
        context.window_manager.modal_handler_add(self)
        self.timer = context.window_manager.event_timer_add(0.1, window=context.window)
        self.thread = threading.Thread(target=install, args=(self.success, logger), daemon=True)
        self.thread.start()
        ActRec_pref.multiline_support_installing = True
        return {'RUNNING_MODAL'}

    def modal(self, context: Context, event: Event) -> set[str]:

        if event.type != 'TIMER':
            return {'PASS_THROUGH'}

        if not self.thread.is_alive():
            return self.execute(context)
        return {'RUNNING_MODAL'}

    def execute(self, context: Context) -> set[str]:
        ActRec_pref = get_preferences(context)
        self.thread.join()
        ActRec_pref.multiline_support_installing = False
        if context and context.area:
            context.area.tag_redraw()
        if len(self.success) and self.success[0]:
            self.report({'INFO'}, "Successfully installed multiline support")
            return {'FINISHED'}
        self.report({'ERROR'}, "Could not install multiline support. See Log for further information.")
        return {'CANCELLED'}


class AR_OT_macro_edit(Macro_based, Operator):
    bl_idname = "ar.macro_edit"
    bl_label = "Edit"
    bl_description = "Double click to Edit"
    bl_options = {'UNDO'}

    def set_clear_operator(self, value: bool) -> None:
        """
        setter of clear_operator.
        Delete the parameters of an operator command. Otherwise the complete command is cleared.

        Args:
            value (bool): unused
        """
        if self.use_last_command:
            command = self.last_command
            if command.startswith("bpy.ops."):
                self.last_command = "%s()" % command.split("(")[0]
            else:
                self.last_command = ""
        else:
            command = self.command
            if command.startswith("bpy.ops."):
                self.command = "%s()" % command.split("(")[0]
            else:
                self.command = ""

    def get_command(self) -> str:
        """
        get the command, which is created from the splitted lines of the command

        Returns:
            str: command as single line
        """
        if not self.use_last_command and any(line.update for line in self.lines):
            self.command = "".join(line.text for line in self.lines)
        return self.get('command', '')

    def set_command(self, value: str) -> None:
        """
        set the command and convert it into multiple lines, which fit into the width of the popup

        Args:
            value (str): command as single line
        """
        self['command'] = value
        if self.use_last_command:
            return
        self.lines.clear()
        for line in functions.text_to_lines(bpy.context, value, AR_OT_macro_edit.font, self.width - 20):
            new = self.lines.add()
            new['text'] = line

    def get_last_command(self) -> str:
        """
        get the last command, which is created from the splitted lines of the command
        last command is the last added command

        Returns:
            str: last command as single line
        """
        if self.use_last_command and any(line.update for line in self.lines):
            self.last_command = "".join(line.text for line in self.lines)
        return self.get('last_command', '')

    def set_last_command(self, value: str) -> None:
        """
        set the last command and convert it into multiple lines, which fit into the width of the popup
        last command is the last added command

        Args:
            value (str): last command as single line
        """
        self['last_command'] = value
        if not self.use_last_command:
            return
        self.lines.clear()
        for line in functions.text_to_lines(bpy.context, value, AR_OT_macro_edit.font, self.width - 20):
            new = self.lines.add()
            new['text'] = line

    def get_use_last_command(self) -> str:
        """
        default Blender property getter

        Returns:
            str: state if last command is used. Defaults to False
        """
        return self.get("use_last_command", False)

    def set_use_last_command(self, value: bool) -> None:
        """
        set the state, whether to use the last command

        Args:
            value (bool): state
        """
        self["use_last_command"] = value
        if value:  # update multi line representation of the switched command
            self.last_command = self.last_command
        else:
            self.command = self.command

    label: StringProperty(name="Label")
    command: StringProperty(name="Command", get=get_command, set=set_command)
    last_label: StringProperty(name="Last Label")
    last_command: StringProperty(name="Last Command", get=get_last_command, set=set_last_command)
    last_id: StringProperty(name="Last Id")
    edit: BoolProperty(default=False)
    multiline_asked: BoolProperty(default=False)
    clear_operator: BoolProperty(
        name="Clear Operator",
        description="Delete the parameters of an operator command. Otherwise the complete command is cleared",
        get=lambda x: False,
        set=set_clear_operator
    )
    use_last_command: BoolProperty(
        default=False, name="Copy Previous",
        description="Copy the data of the previous recorded Macro and place it in this Macro",
        get=get_use_last_command,
        set=set_use_last_command
    )
    lines: CollectionProperty(type=properties.AR_macro_multiline)
    width: IntProperty(default=500, name="width", description="Window width of the Popup")
    font = None
    time = 0
    is_operator = False

    def items_ui_type(self, context: Context) -> list[tuple]:
        enum_items = [("NONE", "None", "not specified, will be using the active type", "BLANK1", 0)]
        if context is None or context.area is None:
            return enum_items
        area = context.area
        try:
            area.ui_type = ""
        except TypeError as err:
            error_items = eval(str(err).split('enum "" not found in ')[1])
            enum_items.extend(
                (item,
                 UILayout.enum_item_name(area, 'ui_type', item),
                 UILayout.enum_item_description(area, 'ui_type', item),
                 UILayout.enum_item_icon(area, 'ui_type', item),
                 i
                 )for i, item in enumerate(error_items, 1)
            )
        return enum_items
    ui_type: EnumProperty(
        items=items_ui_type,
        default=0,
        name="Editor Type",
        description="Current editor type for this area"
    )

    @classmethod
    def poll(cls, context: Context) -> bool:
        ActRec_pref = get_preferences(context)
        return not ActRec_pref.local_record_macros

    def invoke(self, context: Context, event: Event) -> set[str]:
        ActRec_pref = get_preferences(context)
        action_index = self.action_index = functions.get_local_action_index(ActRec_pref, '', self.action_index)
        action = ActRec_pref.local_actions[action_index]

        if action.is_playing:
            self.report({'INFO'}, "The action is playing and can not be edited!")
            return {'CANCELLED'}

        index = self.index = functions.get_local_macro_index(action, self.id, self.index)
        macro = action.macros[index]

        if not self.multiline_asked and not Font_analysis.is_installed() and not ActRec_pref.multiline_support_dont_ask:
            bpy.ops.ar.macro_multiline_support("INVOKE_DEFAULT")
            self.cancel(context)
            self.multiline_asked = True
            return {'CANCELLED'}  # Recall this Operator when handled

        font_path = functions.get_font_path()
        if AR_OT_macro_edit.font is None or AR_OT_macro_edit.font.path != font_path:
            AR_OT_macro_edit.font = Font_analysis(font_path)

        t = time.time()
        # register double click if user clicks on same macro within 0.7 seconds
        if self.last_id == macro.id and AR_OT_macro_edit.time + 0.7 > t or self.edit:
            split = macro.command.split(":")
            if split[0] == 'ar.event':  # Event Macro
                data = json.loads(":".join(split[1:]))
                default_kwargs = {
                    'type': data['Type'],
                    'macro_index': self.index
                }
                kwargs_mapping = {
                    'Timer': lambda: {
                        'time': data['Time']
                    },
                    'Loop.python': lambda: {
                        'statement_type': 'python',
                        'python_statement': data["PyStatement"]
                    },
                    'Loop.count': lambda: {
                        # DEPRECATED Convert old count loop into new repeat loop
                        'statement_type': 'repeat',
                        'repeat_count': int((data["Endnumber"] - data["Startnumber"])/data["Stepnumber"])
                    },
                    'Loop.repeat': lambda: {
                        'statement_type': 'repeat',
                        'repeat_count': data["RepeatCount"]
                    },
                    'Select Object': lambda: {
                        'object': data['Object'],
                        'objects': [{'name': obj_name} for obj_name in data['Objects']],
                        'keep_selection': data['KeepSelection']
                    },
                    'Run Script': lambda: {
                        'script_name': data['ScriptName']
                    }
                }
                data_type = data['Type']
                if data_type == 'Loop':
                    data_type += '.%s' % data["StatementType"]
                bpy.ops.ar.macro_add_event(
                    'INVOKE_DEFAULT',
                    **default_kwargs,
                    **kwargs_mapping.get(data_type, lambda: {})())
                self.clear()
                return {"FINISHED"}

            self.label = macro.label
            self.command = macro.command
            self.last_label = ActRec_pref.last_macro_label
            self.last_command = ActRec_pref.last_macro_command
            self.is_operator = self.command.startswith("bpy.ops")
            try:
                self.ui_type = macro.ui_type
            except TypeError:
                self.ui_type = "NONE"
            return context.window_manager.invoke_props_dialog(self, width=self.width)
        else:
            action.active_macro_index = index
        self.last_id = macro.id
        AR_OT_macro_edit.time = t
        self.clear()
        return {"FINISHED"}

    def draw(self, context: Context) -> None:
        layout = self.layout
        ActRec_pref = functions.get_preferences(context)

        if self.use_last_command:
            layout.prop(self, 'last_label', text="Label")
            self.last_command  # update last command by calling the internal get method
        else:
            layout.prop(self, 'label', text="Label")
            self.command   # update command by calling the internal get method

        col = layout.column(align=True)
        for line in self.lines:
            col.prop(line, 'text', text="")

        row = layout.row()
        action = ActRec_pref.local_actions[self.action_index]
        macro = action.macros[self.index]
        row.prop(self, 'ui_type', text="")
        if self.is_operator:
            row.prop(macro, 'operator_execution_context', text="")
            row.prop(self, 'clear_operator', toggle=True)
        row.prop(self, 'use_last_command', toggle=True)
        op = row.operator('ar.copy_text', text="", icon="COPYDOWN")
        if self.use_last_command:
            op.text = self.last_command
        else:
            op.text = self.command

    def execute(self, context: Context) -> set[str]:
        ActRec_pref = get_preferences(context)
        action = ActRec_pref.local_actions[self.action_index]
        macro = action.macros[self.index]
        if self.use_last_command:
            macro.label = self.last_label
            macro.command = self.last_command
        else:
            macro.label = self.label
            macro.command = self.command
        macro.ui_type = "" if self.ui_type == "NONE" else self.ui_type
        functions.save_local_to_scene(ActRec_pref, context.scene)
        if not ActRec_pref.hide_local_text:
            functions.local_action_to_text(action)
        context.area.tag_redraw()
        self.cancel(context)
        return {"FINISHED"}

    def cancel(self, context: Context) -> None:
        self.edit = False
        self.multiline_asked = False
        self.use_last_command = False
        self.clear()


class AR_OT_copy_to_actrec(Operator):  # used in the right click menu of Blender
    bl_idname = "ar.copy_to_actrec"
    bl_label = "Copy to Action Recorder"
    bl_description = "Copy the selected Operator to Action Recorder Macro"
    bl_options = {'UNDO'}

    copy_single: BoolProperty(default=False)

    context_class_lookup = {
        bpy.types.Scene: "scene",
        bpy.types.Object: "active_object",
        bpy.types.Space: "space_data",
        bpy.types.Area: "area",
        bpy.types.Window: "window",
        bpy.types.Mesh: "active_object.data"
    }

    @classmethod
    def poll(cls, context: Context) -> bool:

        return (getattr(context, "button_operator", None)
                or getattr(context, "button_pointer", None)
                and getattr(context, "button_prop", None)
                )

    def execute(self, context: Context) -> set[str]:
        ActRec_pref = get_preferences(context)
        if not len(ActRec_pref.local_actions):
            bpy.ops.ar.local_add()

        action = ActRec_pref.local_actions[ActRec_pref.active_local_action_index]
        if action.is_playing:
            self.report({'INFO'}, "The action is playing and can not be edited!")
            return {'CANCELLED'}

        # referring to https://docs.blender.org/api/current/bpy.types.Menu.html?menu#extending-the-button-context-menu
        button_pointer = getattr(context, "button_pointer", None)
        button_prop = getattr(context, "button_prop", None)
        if not (button_pointer is None or button_prop is None):
            base_object = button_pointer.id_data
            object_class = base_object.__class__

            attr = self.context_class_lookup.get(object_class)
            if attr is None:
                attr = self.context_class_lookup.get(button_pointer.__class__)
            if attr is None:
                for cls in button_pointer.__class__.__bases__:
                    attr = self.context_class_lookup.get(cls)
                    if attr is not None:
                        break

            if attr is not None and base_object != functions.get_attribute(context, attr):
                base_object = functions.get_attribute(context, attr)
                object_class = base_object.__class__

            if attr is not None:
                return_value = self.handle_button_property(
                    context,
                    button_pointer,
                    button_prop,
                    base_object,
                    object_class,
                    attr
                )
                if return_value:
                    return return_value

            # scans to the context attributes to get data for adding context commands
            for attr in dir(context):
                return_value = self.handle_button_property(
                    context,
                    button_pointer,
                    button_prop,
                    base_object,
                    object_class,
                    attr
                )
                if return_value:
                    return return_value
            else:
                self.report({'WARNING'}, "Couldn't copy this property")
                return {"CANCELLED"}

        button_operator = getattr(context, "button_operator", None)
        if button_operator is not None:
            op_properties = {}
            for prop in button_operator.bl_rna.properties[1:]:  # not include rna_type
                attribute = prop.identifier
                value = getattr(button_operator, attribute)
                if isinstance(value, str):
                    value = "\'%s\'" % value
                op_properties[attribute] = functions.convert_value_to_python(value)
            op_type, op_idname = button_operator.bl_rna.identifier.split("_OT_")
            bpy.ops.ar.macro_add('EXEC_DEFAULT', command="bpy.ops.%s.%s(%s)" %
                                 (op_type.lower(), op_idname.lower(), functions.dict_to_kwarg_str(op_properties)))
            for area in context.screen.areas:
                area.tag_redraw()
            return {"FINISHED"}
        return {"CANCELLED"}

    def handle_button_property(
            self,
            context: Context,
            button_pointer,
            button_prop,
            base_object,
            object_class,
            attr: str) -> Optional[set[str]]:
        """
        add the given property (= button_pointer + button_prop) as a macro if possible

        Args:
            context (Context): active blender context
            button_pointer (Any from bpy.types): button_pointer attribute from the context
            button_prop (Any from bpy.types): button_prop attribute from the context
            base_object (Any from bpy.types): object that is an attribute of context
            object_class (Any <class> from bpy.types): class of the base_object
            attr (str): attribute of context where the base_object is located

        Returns:
            Optional[set[str]]: on success: {"FINISHED"}
        """
        if isinstance(functions.get_attribute(context, attr), object_class):
            try:
                prop = getattr(button_pointer, button_prop.identifier)
                identifier = ".%s" % button_prop.identifier
            except AttributeError:  # Geometry Nodes need this -> NodesModifier
                prop = button_pointer[button_prop.identifier]
                identifier = "[\"%s\"]" % button_prop.identifier
            value = functions.convert_value_to_python(prop)
            if self.copy_single and bpy.ops.ui.copy_data_path_button.poll():
                clipboard = context.window_manager.clipboard
                bpy.ops.ui.copy_data_path_button(full_path=True)
                single_index = context.window_manager.clipboard.split(
                    " = ", 1)[0].rsplit(
                    ".", 1)[1].rsplit(
                    "[", 1)[1].replace(
                    "]", "")
                context.window_manager.clipboard = clipboard
                if single_index.isdigit():
                    value = value[int(single_index)]

            if isinstance(value, str):
                value = "'%s'" % value
            elif isinstance(value, float):
                value = round(value, button_prop.precision)
            elif isinstance(value, IDPropertyArray):
                value = value.to_list()
            elif isinstance(button_prop, PointerProperty) and value is not None:
                for identifier, prop in bpy.data.bl_rna.properties.items():
                    if (prop.type == 'COLLECTION'
                        and prop.fixed_type == button_prop.fixed_type
                            and value.name in getattr(bpy.data, identifier)):
                        value = "bpy.data.%s['%s']" % (identifier, value.name)
                        break

            if base_object != button_pointer:
                try:
                    attr = "%s.%s" % (attr, button_pointer.path_from_id())
                except ValueError:
                    if base_object is None:
                        return
                    pointer_class = button_pointer.__class__
                    for prop in base_object.bl_rna.properties:
                        prop_object = getattr(base_object, prop.identifier)
                        if (isinstance(prop_object, pointer_class)
                                or (hasattr(prop_object, 'bl_rna') and isinstance(prop_object.bl_rna, pointer_class))):
                            attr = "%s.%s" % (attr, prop.identifier)
                            break

            if self.copy_single:
                command = "bpy.context.%s%s[%s] = %s" % (
                    attr, identifier, single_index, str(value))
            else:
                command = "bpy.context.%s%s = %s" % (attr, identifier, str(value))
            self.copy_single = False
            bpy.ops.ar.macro_add('EXEC_DEFAULT', command=command)
            for area in context.screen.areas:
                area.tag_redraw()
            return {"FINISHED"}
# endregion


classes = [
    AR_OT_macro_add,
    AR_OT_macro_add_event,
    AR_OT_macro_event_load_script,
    AR_OT_macro_remove,
    AR_OT_macro_move_up,
    AR_OT_macro_move_down,
    AR_OT_macro_edit,
    AR_OT_copy_to_actrec,
    AR_OT_macro_multiline_support,
    AR_OT_macro_install_multiline_support
]

# region Registration


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)
# endregion
