# region Imports
# external modules
import os
import logging
import traceback
import sys
from datetime import datetime

# blender modules
import bpy
from bpy.app.handlers import persistent
import addon_utils
from .. import __package__ as base_package

# relative imports
from . import config
from .functions import wrapper
# endregion

# region Log system


class Log_system:
    """logging system for the addon"""

    def __init__(self, count: int) -> None:
        """
        creates a log object which unregister with blender

        Args:
            count (int): amount of log files which are kept simultaneously
        """
        logger = logging.getLogger(base_package)
        self.logger = logger
        logger.setLevel(logging.DEBUG)

        self.setup_file_logging(count)

        sys.excepthook = self.exception_handler

    def setup_file_logging(self, count: int) -> None:
        """
        Setup the file logging if possible.

        Args:
            count (int): amount of log files which are kept simultaneously
        """
        dir = self.directory = os.path.join(wrapper.get_user_path(base_package, create=True), "logs")

        if not os.path.exists(dir):
            os.mkdir(dir)
        all_logs = os.listdir(dir)
        self.log_later = []
        while len(all_logs) >= count:
            try:
                # delete oldest file
                os.remove(min([os.path.join(dir, filename) for filename in all_logs], key=os.path.getctime))
            except PermissionError as err:
                self.log_later.append("File is already used -> PermissionError: %s" % str(err))
                break
            except FileNotFoundError as err:
                self.log_later.append("For some reason the File doesn't exists %s" % str(err))
                break
            all_logs = os.listdir(dir)
        self.path = os.path.join(dir, "ActRec_%s.log" % (datetime.today().strftime('%d-%m-%Y_%H-%M-%S')))

    def exception_handler(self, exc_type, exc_value, exc_tb) -> None:
        traceback.print_exception(exc_type, exc_value, exc_tb)
        self.logger.error("Uncaught exception", exc_info=(exc_type, exc_value, exc_tb))

    def check_file_exists(self) -> bool:
        """
        Checks if file logging is possible

        Returns:
            bool: True if file logging is possible otherwise False
        """

        return hasattr(self, 'path') and self.path is not None

    def detach_file(self) -> None:
        """
        remove file of the logger
        """
        if not self.check_file_exists():
            return

        self.file_handler.close()
        self.logger.removeHandler(self.file_handler)

    def append_file(self) -> None:
        """
        adds a file to the logger
        """
        if not self.check_file_exists():
            return

        file_formatter = logging.Formatter(
            "%(levelname)s - %(relativeCreated)d - %(filename)s:%(funcName)s - %(message)s"
        )
        file_handler = logging.FileHandler(self.path, mode='a', encoding='utf-8', delay=True)
        file_handler.setLevel(self.logger.level)
        file_handler.setFormatter(file_formatter)
        self.logger.addHandler(file_handler)
        self.file_handler = file_handler

        self.startup_log()

    def startup_log(self):
        """
        Logging startup information of the logfile
        """
        addon_version = (-1, -1, -1)
        for mod in addon_utils.modules():
            if mod.__name__ == base_package:
                addon_version = mod.bl_info.get("version", addon_version)
                break

        logger.info(
            "Logging ActRec %s running on Blender %s"
            % (".".join([str(x) for x in addon_version]), bpy.app.version_string)
        )
        for log_text in self.log_later:
            logger.info(log_text)


def update_log_amount_in_config(amount: int) -> None:
    """
    writes given amount as log amount into the config file

    Args:
        amount (int): log amount
    """
    if config.log_amount == amount:
        return

    path = os.path.join(os.path.dirname(__file__), "config.py")
    with open(path, 'r', encoding='utf-8') as file:
        lines = file.readlines()

    for i, line in enumerate(lines):
        if not line.startswith('log_amount'):
            continue
        lines[i] = "log_amount = %i\n" % amount
        break
    else:
        lines.append("log_amount = %i\n" % amount)

    with open(path, 'w', encoding='utf-8') as file:
        file.writelines(lines)


# creates logger
log_amount = 5
if hasattr(config, 'log_amount'):
    log_amount = config.log_amount
log_sys = Log_system(log_amount)
logger = log_sys.logger
# endregion
