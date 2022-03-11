# region Import
# external modules
from typing import Optional, Union
import requests
import json
import base64
import os
import subprocess
from collections import defaultdict
import threading
from contextlib import suppress
import sys

# blender modules
import bpy
from bpy.types import Operator
from bpy.props import BoolProperty, EnumProperty
from bpy_extras.io_utils import ExportHelper
from bpy.app.handlers import persistent

# realtive imports
from . import config
from .log import logger
# endregion

__module__ = __package__.split(".")[0]
class update_manager:
    download_list = []
    download_length = 0
    update_respond = None
    update_data_chunks = defaultdict(lambda: {"chunks": b''})
    version_file = {} # used to store downloaded file from "AR_OT_update_check"
    version_file_thread = None

# region functions
@persistent
def on_start(dummy= None) -> None:
    AR = bpy.context.preferences.addons[__module__].preferences
    if AR.auto_update and update_manager.version_file_thread is None:
        t = threading.Thread(target= no_stream_download_version_file, args= [__module__], daemon= True)
        t.start()
        update_manager.version_file_thread = t

@persistent
def on_scene_update(dummy= None) -> None:
    t = update_manager.version_file_thread
    if t and update_manager.version_file.get("version", None):
        t.join()
        bpy.app.handlers.depsgraph_update_post.remove(on_scene_update)
        bpy.app.handlers.load_post.remove(on_start)

def check_for_update(version_file: Optional[dict]) -> tuple[bool, Union[str, tuple[int, int, int]]]:
    if version_file is None:
        return (False, "No Internet Connection")
    version = config.version
    download_version = tuple(version_file["version"])
    if download_version > version:
        return (True, download_version)
    else:
        return (False, version)

def update(AR, path, update_respond: Optional[requests.Response], download_chunks: dict, download_length: int) -> Optional[bool]:
    finished_downloaded = False
    progress = 0
    length = 1
    try:
        if update_respond:
            total_length = update_respond.headers.get('content-length', None)
            if total_length is None:
                length = progress = update_respond.raw._fp_bytes_read
                download_chunks[path]["chunks"] = update_respond.content
                update_respond.close()
                finished_downloaded = True
                update_manager.update_respond = None
            else:
                length = int(total_length)
                for chunk in update_respond.iter_content(chunk_size= 1024):
                    if chunk:
                        download_chunks[path]["chunks"] += chunk

                progress = update_respond.raw._fp_bytes_read
                finished_downloaded = progress == length
                if finished_downloaded:
                    update_respond.close()
                    update_manager.update_respond = None
        else:
            update_manager.update_respond = requests.get(config.repo_source_url %path, stream= True)
        AR.update_progress = 100 * (progress / (length * download_length) + (download_length - len(update_manager.download_list)) / download_length)
        if finished_downloaded:
            update_manager.download_list.pop(0)
        return finished_downloaded
    except Exception as err:
        logger.warning("no Connection (%s)" %err)
        return None

def install_update(AR, download_chunks: dict, version_file: dict) -> None:
    for path in download_chunks:
        absolute_path = os.path.join(AR.addon_directory, path)
        absolute_directory = os.path.dirname(absolute_path)
        if not os.path.exists(absolute_directory):
            os.makedirs(absolute_directory)
        with open(absolute_path, 'w', encoding= 'utf-8') as ar_file:
            ar_file.write(download_chunks[path]["chunks"].decode('utf-8'))
    for path in version_file['remove']:
        remove_path = os.path.join(AR.addon_directory, path)
        if os.path.exists(remove_path):
            for root, dirs, files in os.walk(remove_path, topdown= False):
                for name in files:
                    os.remove(os.path.join(root, name))
                for name in dirs:
                    os.rmdir(os.path.join(root, name))
    version = tuple(AR.version.split("."))
    download_chunks.clear()
    version_file.clear()
    logger.info("Updated Action Recorder to Version: %s" %str(version))

def start_get_version_file() -> Optional[bool]:
    try:
        update_manager.version_file['respond'] = requests.get(config.check_source_url, stream= True)
        update_manager.version_file['chunk'] = b''
        logger.info("Start Download: version_file")
        return True
    except Exception as err:
        logger.warning("no Connection (%s)" %err)
        return None

def get_version_file(res: requests.Response) -> Union[bool, dict, None]:
    try:
        total_length = res.headers.get('content-length', None)
        if total_length is None:
            logger.info("Finsihed Download: version_file")
            content = res.content
            res.close()
            return json.loads(content)
        else:
            for chunk in res.iter_content(chunk_size= 1024):
                update_manager.version_file['chunk'] += chunk
            length = res.raw._fp_bytes_read
            if int(total_length) == length:
                res.close()
                logger.info("Finsihed Download: version_file")
                return json.loads(update_manager.version_file['chunk'])
            return True
    except Exception as err:
        logger.warning("no Connection (%s)" %err)
        res.close()
        return None

def apply_version_file_result(AR, version_file, update):
    AR.update = update[0]
    if not update[0]:
        res = version_file.get('respond')
        if res:
            res.close()
        version_file.clear()
    if isinstance(update[1], str):
        AR.version = update[1]
    else:
        AR.version = ".".join(map(str, update[1]))

def get_download_list(version_file) -> Optional[list]:
    download_files = version_file["files"]
    if download_files is None:
        return None
    download_list = []
    version = config.version
    for key in download_files:
        if tuple(download_files[key]) > version:
            download_list.append(key)
    return download_list

def no_stream_download_version_file(module_name):
    try:
        logger.info("Start Download: version_file")
        res = requests.get(config.check_source_url)
        logger.info("Finsihed Download: version_file")
        update_manager.version_file = json.loads(res.content)
        version_file = update_manager.version_file
        update = check_for_update(version_file)
        AR = bpy.context.preferences.addons[module_name].preferences
        apply_version_file_result(AR, version_file, update)
    except Exception as err:
        logger.warning("no Connection (%s)" %err)
        return None
# endregion functions

# region UI functions
def draw_update_button(layout, AR) -> None:
    if AR.update_progress >= 0:
        row = layout.row()
        row.enabled = False
        row.prop(AR, 'update_progress', text= "Progress", slider= True)
    else:
        layout.operator('ar.update', text= 'Update')
# endregion

# region Operator
class AR_OT_update_check(Operator):
    bl_idname = "ar.update_check"
    bl_label = "Check for Update"
    bl_description = "check for available update"
    
    def invoke(self, context, event):
        res = start_get_version_file()
        if res:
            self.timer = context.window_manager.event_timer_add(0.1)
            context.window_manager.modal_handler_add(self)
            return {'RUNNING_MODAL'}
        self.report({'WARNING'}, "No Internet Connection")
        return {'CANCELLED'}

    def modal(self, context, event):
        version_file = get_version_file(update_manager.version_file['respond'])
        if isinstance(version_file, dict) or version_file is None:
            update_manager.version_file = version_file
            return self.execute(context)
        return {'PASS_THROUGH'}

    def execute(self, context):
        version_file = update_manager.version_file
        if not version_file:
            return {'CANCELLED'}
        if version_file.get('respond'):
            return {'RUNNING_MODAL'}
        update = check_for_update(version_file)
        AR = context.preferences.addons[__module__].preferences
        apply_version_file_result(AR, version_file, update)
        context.window_manager.event_timer_remove(self.timer)
        return {"FINISHED"}

    def cancel(self, context):
        if update_manager.version_file:
            res = update_manager.version_file.get('respond')
            if res:
                res.close()
            update_manager.version_file.clear()
        context.window_manager.event_timer_remove(self.timer)

class AR_OT_update(Operator):
    bl_idname = "ar.update"
    bl_label = "Update"
    bl_description = "install the new version"

    @classmethod
    def poll(cls, context):
        AR = context.preferences.addons[__module__].preferences
        return AR.update

    def invoke(self, context, event):
        update_manager.download_list = get_download_list(update_manager.version_file)
        update_manager.download_length = len(update_manager.download_list)
        self.timer = context.window_manager.event_timer_add(0.05, window= context.window)
        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}

    def modal(self, context, event):
        if not len(update_manager.download_list):
            return self.execute(context)

        AR = context.preferences.addons[__module__].preferences
        path = update_manager.download_list[0]
        res = update(AR, path, update_manager.update_respond, update_manager.update_data_chunks, update_manager.download_length)

        if res is None:
            self.report({'WARNING'}, "No Internet Connection")
            return {'CANCELLED'}
        
        context.area.tag_redraw()
        return {'PASS_THROUGH'}

    def execute(self, context):
        if not(update_manager.version_file and update_manager.update_data_chunks):
            return {'CANCELLED'}
        AR = context.preferences.addons[__module__].preferences
        AR.update = False
        AR.restart = True
        install_update(AR, update_manager.update_data_chunks, update_manager.version_file)
        AR.update_progress = -1
        self.cancel(context)
        bpy.ops.ar.show_restart_menu('INVOKE_DEFAULT')
        context.area.tag_redraw()
        return {"FINISHED"}

    def cancel(self, context):
        res = update_manager.update_respond
        if res:
            res.close()
        update_manager.update_respond = None
        update_manager.download_length = 0
        update_manager.download_list.clear()
        update_manager.update_data_chunks.clear()
        context.window_manager.event_timer_remove(self.timer)

class AR_OT_restart(Operator, ExportHelper):
    bl_idname = "ar.restart"
    bl_label = "Restart Blender"
    bl_description = "Restart Blender"
    bl_options = {"INTERNAL"}

    save : BoolProperty(default= False)
    filename_ext = ".blend"
    filter_folder : BoolProperty(default= True, options={'HIDDEN'})
    filter_blender : BoolProperty(default= True, options={'HIDDEN'})

    def invoke(self, context, event):
        if self.save and not bpy.data.filepath:
            return ExportHelper.invoke(self, context, event)
        else:
            return self.execute(context)

    def execute(self, context):
        AR = context.preferences.addons[__module__].preferences
        path = bpy.data.filepath
        if self.save:
            if not path:
                path = self.filepath
                if not path:
                    return ExportHelper.invoke(self, context, None)
            bpy.ops.wm.save_mainfile(filepath= path)
        AR.restart = False
        if os.path.exists(path):
            args = [*sys.argv, path]
        else:
            args = sys.argv
        subprocess.Popen(args)
        bpy.ops.wm.quit_blender()
        return {"FINISHED"}
    
    def draw(self, context):
        pass

class AR_OT_show_restart_menu(Operator):
    bl_idname = "ar.show_restart_menu"
    bl_label = "Restart Blender"
    bl_description = "Restart Blender"
    bl_options = {'REGISTER', 'UNDO'}

    restart_options : EnumProperty(items= [("exit", "Don't Restart", "Don't restart and exit this window"), ("save", "Save & Restart", "Save & Restart Blender"), ("restart", "Restart", "Restart Blender")])

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def execute(self, context):
        if self.restart_options == "save":
            bpy.ops.ar.restart(context.copy(), save= True)
        elif self.restart_options == "restart":
            bpy.ops.ar.restart(context.copy())
        return {"FINISHED"}
    
    def cancel(self, context):
        bpy.ops.ar.show_restart_menu("INVOKE_DEFAULT")

    def draw(self, context):
        AR = context.preferences.addons[__module__].preferences
        layout = self.layout
        if AR.restart:
            layout.label(text= "You need to restart Blender to complete the Update")
        layout.prop(self, 'restart_options', expand= True)
# endregion

classes = [
    AR_OT_update_check,
    AR_OT_update,
    AR_OT_restart,
    AR_OT_show_restart_menu
]

# region Registration
def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.app.handlers.load_post.append(on_start)
    bpy.app.handlers.depsgraph_update_post.append(on_scene_update)

def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)
    with suppress(Exception):
        bpy.app.handlers.load_post.remove(on_start)
    with suppress(Exception):
        bpy.app.handlers.depsgraph_update_post.remove(on_scene_update)
    update_manager.download_list.clear()
    update_manager.download_length = 0
    update_manager.update_data_chunks.clear()
    update_manager.update_respond = None
    update_manager.version_file.clear()
    update_manager.version_file_thread = None
# endregion 
