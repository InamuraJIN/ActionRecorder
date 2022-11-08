# region Imports
# external modules
import os
import logging
import traceback
import sys
from datetime import datetime

# blender modules
import bpy

# relative imports
from . import config
# endregion

__module__ = __package__.split(".")[0]

# region Log system


class Log_system:
    """logging system for the addon"""

    def __init__(self, count: int):
        """
        creates a log object which unregister with blender

        Args:
            count (int): amount of log files which are kept simultaneously
        """
        dir = self.directory = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs")
        if not os.path.exists(dir):
            os.mkdir(dir)
        all_logs = os.listdir(dir)
        log_later = []
        while len(all_logs) >= count:
            try:
                # delete oldest file
                os.remove(min([os.path.join(dir, filename) for filename in all_logs], key=os.path.getctime))
            except PermissionError as err:
                log_later.append("File is already used -> PermissionError: %s" % str(err))
                break
            except FileNotFoundError as err:
                log_later.append("For some reason the File doesn't exists %s" % str(err))
                break
            all_logs = os.listdir(dir)
        name = ""
        for arg in sys.argv:
            if arg.endswith(".blend"):
                name = "%s_" % ".".join(os.path.basename(arg).split(".")[:-1])
        path = self.path = os.path.join(dir, "ActRec_%s%s.log" % (name, datetime.today().strftime('%d-%m-%Y_%H-%M-%S')))

        logger = logging.getLogger(__module__)
        logger.setLevel(logging.DEBUG)
        file_formatter = logging.Formatter(
            "%(levelname)s - %(relativeCreated)d - %(filename)s:%(funcName)s - %(message)s"
        )
        file_handler = logging.FileHandler(path, mode='w', encoding='utf-8', delay=True)
        file_handler.setLevel(logger.level)
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)
        logger.info(
            "Logging ActRec %s running on Blender %s"
            % (".".join([str(x) for x in config.version]), bpy.app.version_string)
        )
        for log_text in log_later:
            logger.info(log_text)
        self.logger = logger
        self.file_handler = file_handler

        sys.excepthook = self.exception_handler

    def exception_handler(self, exc_type, exc_value, exc_tb):
        traceback.print_exception(exc_type, exc_value, exc_tb)
        self.logger.error("Uncaught exception", exc_info=(exc_type, exc_value, exc_tb))

    def unregister(self):
        """
        unregister the logger, used when addon gets unregistered
        """
        self.file_handler.close()
        self.logger.removeHandler(self.file_handler)


# creates logger
log_sys = Log_system(5)
logger = log_sys.logger
# endregion
