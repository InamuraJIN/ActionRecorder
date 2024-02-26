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

# relative imports
from . import config
# endregion

__module__ = __package__.split(".")[0]

# region Log system


class Log_system:
    """logging system for the addon"""

    def __init__(self, count: int) -> None:
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
        self.path = os.path.join(dir, "ActRec_%s%s.log" % (name, datetime.today().strftime('%d-%m-%Y_%H-%M-%S')))

        logger = logging.getLogger(__module__)
        self.logger = logger
        logger.setLevel(logging.DEBUG)

        logger.info(
            "Logging ActRec %s running on Blender %s"
            % (".".join([str(x) for x in config.version]), bpy.app.version_string)
        )
        for log_text in log_later:
            logger.info(log_text)

        sys.excepthook = self.exception_handler

    def exception_handler(self, exc_type, exc_value, exc_tb) -> None:
        traceback.print_exception(exc_type, exc_value, exc_tb)
        self.logger.error("Uncaught exception", exc_info=(exc_type, exc_value, exc_tb))

    def detach_file(self) -> None:
        """
        remove file of the logger
        """
        self.file_handler.close()
        self.logger.removeHandler(self.file_handler)

    def append_file(self) -> None:
        """
        adds a file to the logger
        """
        file_formatter = logging.Formatter(
            "%(levelname)s - %(relativeCreated)d - %(filename)s:%(funcName)s - %(message)s"
        )
        file_handler = logging.FileHandler(self.path, mode='a', encoding='utf-8', delay=True)
        file_handler.setLevel(self.logger.level)
        file_handler.setFormatter(file_formatter)
        self.logger.addHandler(file_handler)
        self.file_handler = file_handler


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
