# region Import
# external modules
from typing import Optional, Union
import requests
import json
import os
import subprocess
from collections import defaultdict
import threading
from contextlib import suppress
import sys
from typing import TYPE_CHECKING

# blender modules
import bpy
from bpy.types import Operator, Scene, AddonPreferences, UILayout, Context, Event
from bpy.props import BoolProperty, EnumProperty
from bpy_extras.io_utils import ExportHelper
from bpy.app.handlers import persistent

# relative imports
from . import config
from .log import logger
from .functions.shared import get_preferences
if TYPE_CHECKING:
    from .preferences import AR_preferences
else:
    AR_preferences = AddonPreferences
# endregion


__module__ = __package__.split(".")[0]


class Update_manager:
    """manage data for update processes"""
    download_list = []
    download_length = 0
    update_respond = None
    update_data_chunks = defaultdict(lambda: {"chunks": b''})
    version_file = {}  # used to store downloaded file from "AR_OT_update_check"
    version_file_thread = None

# region functions


@persistent
def on_start(dummy: Scene = None) -> None:
    """
    get called on start of Blender with on_load handler and checks for available update of ActRec
    opens a thread to run the process faster (the thread get closed in on_scene_update)

    Args:
        dummy (Scene, optional):
        needed because blender handler inputs the scene as argument for a handler function. Defaults to None.
    """
    ActRec_pref = get_preferences(bpy.context)
    if not (ActRec_pref.auto_update and Update_manager.version_file_thread is None):
        return
    t = threading.Thread(target=no_stream_download_version_file, args=[__module__], daemon=True)
    t.start()
    Update_manager.version_file_thread = t


@persistent
def on_scene_update(dummy: Scene = None) -> None:
    """
    get called on the first scene update of Blender and closes the thread from on start,
    which is used to check for updates and removes the functions from the handler

    Args:
        dummy (bpy.type.Scene, optional):
        needed because blender handler inputs the scene as argument for a handler function. Defaults to None.
    """
    t = Update_manager.version_file_thread
    if not (t and Update_manager.version_file.get("version", None)):
        return
    t.join()
    bpy.app.handlers.depsgraph_update_post.remove(on_scene_update)
    bpy.app.handlers.load_post.remove(on_start)


def check_for_update(version_file: Optional[dict]) -> tuple[bool, Union[str, tuple[int, int, int]]]:
    """
    checks if a new version of ActRec is available on GitHub

    Args:
        version_file (Optional[dict]): contains data about the addon version and the version of each file

    Returns:
        tuple[bool, Union[str, tuple[int, int, int]]]:
        [0] False for error or the latest version, True for new available version;
        [1] error message or tuple of the version
    """
    if version_file is None:
        return (False, "No Internet Connection")
    version = config.version
    download_version = tuple(version_file["version"])
    if download_version > version:
        return (True, download_version)
    else:
        return (False, version)


def update(
        ActRec_pref: AR_preferences,
        path: str,
        update_respond: Optional[requests.Response],
        download_chunks: dict,
        download_length: int) -> Optional[bool]:
    """
    runs the update process and shows the download process with a progress bar if possible

    Args:
        ActRec_pref (AR_preferences): preferences of this addon
        path (str): path to the file to update
        update_respond (Optional[requests.Response]): open response to file,
        needed if file is to large to download in one function call (chunk size 1024)
        download_chunks (dict): contains all downloaded files and their data
        download_length (int): the current length of the chunks, needed to show progress bar

    Returns:
        Optional[bool]: the downloaded file or None if an error occurred
    """
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
                Update_manager.update_respond = None
            else:
                length = int(total_length)
                for chunk in update_respond.iter_content(chunk_size=1024):
                    if chunk:
                        download_chunks[path]["chunks"] += chunk

                progress = update_respond.raw._fp_bytes_read
                finished_downloaded = progress == length
                if finished_downloaded:
                    update_respond.close()
                    Update_manager.update_respond = None
        else:
            Update_manager.update_respond = requests.get(
                config.repo_source_url % path, stream=True)
        ActRec_pref.update_progress = int(100 * (progress / (length * download_length) + (
            download_length - len(Update_manager.download_list)) / download_length))
        if finished_downloaded:
            Update_manager.download_list.pop(0)
        return finished_downloaded
    except Exception as err:
        logger.warning("no Connection (%s)" % err)
        return None


def install_update(ActRec_pref: AR_preferences, download_chunks: dict, version_file: dict) -> None:
    """
    installs all downloaded files successively and removes old files if needed
    + cleans up all unused data

    Args:
        ActRec_pref (AR_preferences): preferences of this addon
        download_chunks (dict): contains all downloaded files and their data
        version_file (dict): contains data about the addon version, the version of each file and the open request
    """
    for path in download_chunks:
        # remove ActRec/ from path, because the Add-on is inside of another directory on GitHub
        relative_path = path.replace("\\", "/").split("/", 1)[1]
        absolute_path = os.path.join(ActRec_pref.addon_directory, relative_path)
        absolute_directory = os.path.dirname(absolute_path)
        if not os.path.exists(absolute_directory):
            os.makedirs(absolute_directory, exist_ok=True)
        with open(absolute_path, 'w', encoding='utf-8') as ar_file:
            ar_file.write(download_chunks[path]["chunks"].decode('utf-8'))
    for path in version_file['remove']:
        # remove ActRec/ from path, because the Add-on is inside of another directory on GitHub
        relative_path = path.replace("\\", "/").split("/", 1)[1]
        remove_path = os.path.join(ActRec_pref.addon_directory, relative_path)
        if not os.path.exists(remove_path):
            continue
        for root, dirs, files in os.walk(remove_path, topdown=False):
            for name in files:
                os.remove(os.path.join(root, name))
            for name in dirs:
                os.rmdir(os.path.join(root, name))
    version = tuple(ActRec_pref.version.split("."))
    download_chunks.clear()
    version_file.clear()
    logger.info("Updated Action Recorder to Version: %s" % str(version))


def start_get_version_file() -> bool:
    """
    starts the request process to get the version file, which is needed to only update the changed files

    Returns:
        bool: success of the process
    """
    try:
        Update_manager.version_file['respond'] = requests.get(
            config.check_source_url, stream=True)
        Update_manager.version_file['chunk'] = b''
        logger.info("Start Download: version_file")
        return True
    except Exception as err:
        logger.warning("no Connection (%s)" % err)
        return False


def get_version_file(res: requests.Response) -> Union[bool, dict, None]:
    """
    downloads the data of the version file and needed to be called again if the download process isn't finished

    Args:
        res (requests.Response): response that was created by start_get_version_file

    Returns:
        Union[bool, dict, None]:
        [None] error;
        [True] needed to be called again;
        [dict] data of the version file in JSON-format
    """
    try:
        total_length = res.headers.get('content-length', None)
        if total_length is None:
            logger.info("Finished Download: version_file")
            content = res.content
            res.close()
            return json.loads(content)

        for chunk in res.iter_content(chunk_size=1024):
            Update_manager.version_file['chunk'] += chunk
        length = res.raw._fp_bytes_read
        if int(total_length) == length:
            res.close()
            logger.info("Finished Download: version_file")
            return json.loads(Update_manager.version_file['chunk'])
        return True
    except Exception as err:
        logger.warning("no Connection (%s)" % err)
        res.close()
        return None


def apply_version_file_result(
        ActRec_pref: AR_preferences,
        version_file: dict,
        update: tuple[bool, Union[tuple, str]]) -> None:
    """
    updates the version in the addon preferences if needed and closes the open request from version file

    Args:
        ActRec_pref (AR_preferences): preferences of this addon
        version_file (dict): contains data about the addon version, the version of each file and the open request
        update (tuple[bool, Union[tuple, str]]):
        [0] update is available;
        [1] version of the addon in str or tuple format
    """
    ActRec_pref.update = update[0]
    if not update[0]:
        res = version_file.get('respond')
        if res:
            res.close()
        version_file.clear()
    if isinstance(update[1], str):
        ActRec_pref.version = update[1]
    else:
        ActRec_pref.version = ".".join(map(str, update[1]))


def get_download_list(version_file: dict) -> Optional[list]:
    """
    creates a list of which files needed to be downloaded to install the update

    Args:
        version_file (dict): contains data about the addon version, the version of each file and the open request

    Returns:
        Optional[list]:
        [None] no paths are written;
        [list] list of the paths that needed to be downloaded
    """
    download_files = version_file["files"]
    if download_files is None:
        return None
    download_list = []
    version = config.version
    for key in download_files:
        if tuple(download_files[key]) > version:
            download_list.append(key)
    return download_list


def no_stream_download_version_file(module_name: str) -> None:
    """
    downloads the version file without needed to be called again. Is faster but stops Blender from executing other code.

    Args:
        module_name (str): name of the addon to get the addon preferences
    """
    try:
        logger.info("Start Download: version_file")
        res = requests.get(config.check_source_url)
        logger.info("Finished Download: version_file")
        Update_manager.version_file = json.loads(res.content)
        version_file = Update_manager.version_file
        update = check_for_update(version_file)
        ActRec_pref = bpy.context.preferences.addons[module_name].preferences
        apply_version_file_result(ActRec_pref, version_file, update)
    except Exception as err:
        logger.warning("no Connection (%s)" % err)
# endregion functions

# region UI functions


def draw_update_button(layout: UILayout, ActRec_pref: AR_preferences) -> None:
    """
    draws the update button and show a progress bar when files get downloaded

    Args:
        layout (UILayout): context where to draw the button
        ActRec_pref (AR_preferences): preferences of this addon
    """
    if ActRec_pref.update_progress >= 0:
        row = layout.row()
        row.enabled = False
        row.prop(ActRec_pref, 'update_progress', text="Progress", slider=True)
    else:
        layout.operator('ar.update', text='Update')
# endregion

# region Operator


class AR_OT_update_check(Operator):
    bl_idname = "ar.update_check"
    bl_label = "Check for Update"
    bl_description = "check for available update"

    def invoke(self, context: Context, event: Event) -> set[str]:
        res = start_get_version_file()
        if res:
            self.timer = context.window_manager.event_timer_add(0.1)
            context.window_manager.modal_handler_add(self)
            return {'RUNNING_MODAL'}
        self.report({'WARNING'}, "No Internet Connection")
        return {'CANCELLED'}

    def modal(self, context: Context, event: Event) -> set[str]:
        version_file = get_version_file(Update_manager.version_file['respond'])
        if isinstance(version_file, dict) or version_file is None:
            Update_manager.version_file = version_file
            return self.execute(context)
        return {'PASS_THROUGH'}

    def execute(self, context: Context) -> set[str]:
        version_file = Update_manager.version_file
        if not version_file:
            return {'CANCELLED'}
        if version_file.get('respond'):
            return {'RUNNING_MODAL'}
        update = check_for_update(version_file)
        ActRec_pref = get_preferences(context)
        apply_version_file_result(ActRec_pref, version_file, update)
        context.window_manager.event_timer_remove(self.timer)
        return {"FINISHED"}

    def cancel(self, context: Context) -> None:
        if Update_manager.version_file:
            res = Update_manager.version_file.get('respond')
            if res:
                res.close()
            Update_manager.version_file.clear()
        context.window_manager.event_timer_remove(self.timer)


class AR_OT_update(Operator):
    bl_idname = "ar.update"
    bl_label = "Update"
    bl_description = "install the new version"

    @classmethod
    def poll(cls, context: Context) -> bool:
        ActRec_pref = get_preferences(context)
        return ActRec_pref.update

    def invoke(self, context: Context, event: Event) -> set[str]:
        Update_manager.download_list = get_download_list(
            Update_manager.version_file)
        Update_manager.download_length = len(Update_manager.download_list)
        self.timer = context.window_manager.event_timer_add(
            0.05, window=context.window)
        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}

    def modal(self, context: Context, event: Event) -> set[str]:
        if not len(Update_manager.download_list):
            return self.execute(context)

        ActRec_pref = get_preferences(context)
        path = Update_manager.download_list[0]
        res = update(ActRec_pref, path, Update_manager.update_respond,
                     Update_manager.update_data_chunks, Update_manager.download_length)

        if res is None:
            self.report({'WARNING'}, "No Internet Connection")
            return {'CANCELLED'}

        context.area.tag_redraw()
        return {'PASS_THROUGH'}

    def execute(self, context: Context) -> set[str]:
        if not (Update_manager.version_file and Update_manager.update_data_chunks):
            return {'CANCELLED'}
        ActRec_pref = get_preferences(context)
        ActRec_pref.update = False
        ActRec_pref.restart = True
        install_update(ActRec_pref, Update_manager.update_data_chunks,
                       Update_manager.version_file)
        ActRec_pref.update_progress = -1
        self.cancel(context)
        bpy.ops.ar.show_restart_menu('INVOKE_DEFAULT')
        context.area.tag_redraw()
        return {"FINISHED"}

    def cancel(self, context: Context) -> None:
        res = Update_manager.update_respond
        if res:
            res.close()
        Update_manager.update_respond = None
        Update_manager.download_length = 0
        Update_manager.download_list.clear()
        Update_manager.update_data_chunks.clear()
        context.window_manager.event_timer_remove(self.timer)


class AR_OT_restart(Operator, ExportHelper):
    bl_idname = "ar.restart"
    bl_label = "Restart Blender"
    bl_description = "Restart Blender"
    bl_options = {"INTERNAL"}

    save: BoolProperty(default=False)
    filename_ext = ".blend"
    filter_folder: BoolProperty(default=True, options={'HIDDEN'})
    filter_blender: BoolProperty(default=True, options={'HIDDEN'})

    def invoke(self, context: Context, event: Event) -> set[str]:
        if self.save and not bpy.data.filepath:
            return ExportHelper.invoke(self, context, event)
        else:
            return self.execute(context)

    def execute(self, context: Context) -> set[str]:
        ActRec_pref = get_preferences(context)
        path = bpy.data.filepath
        if self.save:
            if not path:
                path = self.filepath
                if not path:
                    return ExportHelper.invoke(self, context, None)
            bpy.ops.wm.save_mainfile(filepath=path)
        ActRec_pref.restart = False
        if os.path.exists(path):
            args = [*sys.argv, path]
        else:
            args = sys.argv
        subprocess.Popen(args)
        bpy.ops.wm.quit_blender()
        return {"FINISHED"}

    def draw(self, context: Context) -> None:
        pass


class AR_OT_show_restart_menu(Operator):
    bl_idname = "ar.show_restart_menu"
    bl_label = "Restart Blender"
    bl_description = "Restart Blender"
    bl_options = {'REGISTER', 'UNDO'}

    restart_options: EnumProperty(
        items=[("exit", "Don't Restart", "Don't restart and exit this window"),
               ("save", "Save & Restart", "Save & Restart Blender"),
               ("restart", "Restart", "Restart Blender")])

    def invoke(self, context: Context, event: Event) -> set[str]:
        return context.window_manager.invoke_props_dialog(self)

    def execute(self, context: Context) -> set[str]:
        if self.restart_options == "save":
            bpy.ops.ar.restart(save=True)
        elif self.restart_options == "restart":
            bpy.ops.ar.restart()
        return {"FINISHED"}

    def cancel(self, context: Context) -> None:
        bpy.ops.ar.show_restart_menu("INVOKE_DEFAULT")

    def draw(self, context: Context) -> None:
        ActRec_pref = get_preferences(context)
        layout = self.layout
        if ActRec_pref.restart:
            layout.label(
                text="You need to restart Blender to complete the Update")
        layout.prop(self, 'restart_options', expand=True)
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
    Update_manager.download_list.clear()
    Update_manager.download_length = 0
    Update_manager.update_data_chunks.clear()
    Update_manager.update_respond = None
    Update_manager.version_file.clear()
    Update_manager.version_file_thread = None
# endregion
