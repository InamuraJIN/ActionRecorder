# ===============================================================================
# Wrapper functions for Blender API to support multiple LTS versions of Blender.
# This script should be independent of any local import to avoid circular imports.
#
# Supported Blender versions (Updated: 2024-11-04):
# - 4.2 LTS
# - 3.6 LTS
# ===============================================================================

# region Imports
import bpy
from bpy.app import version

import os
# endregion

# region Functions


def get_user_path(package: str, path: str = '', create: bool = False):
    """
    Return a user writable directory associated with an extension.

    Args:
        package (str): The __package__ of the extension.
        path (str, optional): Optional subdirectory. Defaults to ''.
        create (bool, optional): Treat the path as a directory and create it if its not existing. Defaults to False.
    """
    fallback = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    try:
        if version >= (4, 2, 0):
            return bpy.utils.extension_path_user(package, path=path, create=create)
        else:
            return fallback  # The Fallback path is also the extension user directory for Blender 3.6 LTS.
    except ValueError as err:
        print("ERROR ActRec: ValueError: %s" % str(err))
        if err.args[0] == "The \"package\" does not name an extension":
            print("--> This error might be caused as the addon is installed the first time.")
            print("    If this errors remains please try reinstalling the Add-on and report it to the developer.")

        print("    Fallback to old extension directory: %s." % fallback)
        return fallback

# endregion
