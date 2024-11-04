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

    if version >= (4, 2, 0):
        return bpy.utils.extension_path_user(package, path=path, create=create)
    else:
        return os.path.dirname(os.path.dirname(os.path.dirname(__file__)))

# endregion
