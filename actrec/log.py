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

# region Logsystem 
class log_system:
    def __init__(self, count: int) -> None:
        dirc = self.directory = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs")
        if not os.path.exists(dirc):
            os.mkdir(dirc)
        all_logs = os.listdir(dirc)
        loglater = []
        while len(all_logs) >= count:
            try:
                os.remove(min([os.path.join(dirc, filename) for filename in all_logs], key= os.path.getctime)) # delete oldest file
            except PermissionError as err:
                loglater.append("File is already used -> PermissionError: %s" %str(err))
                break
            except FileNotFoundError as err:
                loglater.append("For some reason the File doesn't exists %s" %str(err))
                break
            all_logs = os.listdir(dirc)
        name = ""
        for arg in sys.argv:
            if arg.endswith(".blend"):
                name = "%s_" %".".join(os.path.basename(arg).split(".")[:-1])
        path = self.path = os.path.join(dirc, "ActRec_%s%s.log" %(name, datetime.today().strftime('%d-%m-%Y_%H-%M-%S')))

        logger = logging.getLogger(__module__)
        logger.setLevel(logging.DEBUG)
        file_formatter = logging.Formatter("%(levelname)s - %(relativeCreated)d - %(filename)s:%(funcName)s - %(message)s")
        file_handler = logging.FileHandler(path, mode= 'w', encoding= 'utf-8', delay= True)
        file_handler.setLevel(logger.level)
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)
        logger.info("Logging ActRec %s %s %s" %(".".join([str(x) for x in config.version]), "running on Blender", bpy.app.version_string))
        for log_text in loglater:
            logger.info(log_text)
        self.logger = logger
        self.file_handler = file_handler
        
        sys.excepthook = self.exception_handler
    
    def exception_handler(self, exc_type, exc_value, exc_tb) -> None:
        traceback.print_exception(exc_type, exc_value, exc_tb)
        self.logger.error("Uncaught exception", exc_info= (exc_type, exc_value, exc_tb))

    def unregister(self) -> None:
        self.file_handler.close()
        self.logger.removeHandler(self.file_handler)
log_sys = log_system(5)
logger = log_sys.logger
#endregion 
