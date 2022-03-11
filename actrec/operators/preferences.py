# region Imports
# external modules
import os
import sys
import subprocess

# blender modules
import bpy
from bpy.types import Operator
from bpy.props import StringProperty
from bpy_extras.io_utils import ExportHelper

# relative imports
from ..log import logger
# endregion

__module__ = __package__.split(".")[0]

# region Operator
class AR_OT_preferences_directory_selector(Operator, ExportHelper):
    bl_idname = "ar.preferences_directory_selector"
    bl_label = "Select Directory"
    bl_description = " "
    bl_options = {'REGISTER','INTERNAL'}

    filename_ext = "."
    use_filter_folder = True
    filepath : StringProperty (name = "File Path", maxlen = 0, default = " ")

    pref_property : StringProperty()
    path_extension : StringProperty()

    def execute(self, context):
        AR = bpy.context.preferences.addons[__module__].preferences
        userpath = self.properties.filepath
        if(not os.path.isdir(userpath)):
            msg = "Please select a directory not a file\n" + userpath
            self.report({'ERROR'}, msg)
            return{'CANCELLED'}
        AR = context.preferences.addons[__module__].preferences
        setattr(AR, self.pref_property, os.path.join(userpath, self.path_extension))
        return{'FINISHED'}

class AR_OT_preferences_recover_directory(Operator):
    bl_idname = "ar.preferences_recover_directory"
    bl_label = "Recover Standart Directory"
    bl_description = "Recover the standart Storage directory"
    bl_options = {'REGISTER','INTERNAL'}

    pref_property : StringProperty()
    path_extension : StringProperty()

    def execute(self, context):
        AR = context.preferences.addons[__module__].preferences
        setattr(AR, self.pref_property, os.path.join(AR.addon_directory, self.path_extension))
        return{'FINISHED'}
        
class AR_OT_preferences_open_explorer(Operator):
    bl_idname = "ar.preferences_open_explorer"
    bl_label = "Open Explorer"
    bl_description = "Open the Explorer with the given path"
    bl_options = {'REGISTER','INTERNAL'}

    path : StringProperty(name="Path", description= "Open the explorer with the given path")

    def open_file_in_explorer(self, path):
        if sys.platform == "win32":
            subprocess.call(["explorer", "/select,", path])
        elif sys.platform == "darwin":
            subprocess.call(["open", "-R", path])
        else:
            subprocess.call(["xdg-open", os.path.dirname(path)])

    def open_directory_in_explorer(self, directory):
        if sys.platform == "win32":
            os.startfile(self.directory)
        else:
            opener = "open" if sys.platform == "darwin" else "xdg-open"
            subprocess.call([opener, self.directory])


    def execute(self, context):
        self.path = os.path.normpath(self.path)
        if os.path.isdir(self.path):
            self.open_directory_in_explorer(self.path)
        elif os.path.isfile(self.path):
            try:
                self.open_file_in_explorer(self.path)
            except Exception as err:
                self.open_directory_in_explorer(os.path.dirname(self.path))
                logger.info("Fallback to show directory: %s" %err)                
        return {'FINISHED'}
# endregion

classes = [
    AR_OT_preferences_directory_selector,
    AR_OT_preferences_recover_directory,
    AR_OT_preferences_open_explorer
]

# region Registration
def register():
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)
# endregion