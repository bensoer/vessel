import win32serviceutil
import win32service
import win32event
import servicemanager
import configparser
import os
import inspect
import logging
from multiprocessing import Process, Pipe
from logging.handlers import RotatingFileHandler
from db.sqlitemanager import SQLiteManager
from utils.node_client_process import NodeClientProcess
from db.models.Script import Script
import utils.vesselhelper as vh


def bootstrapper(wrapper_object, initialization_tuple):
    instance = wrapper_object(initialization_tuple)
    instance.start()
    exit(0)

class AppServerSvc(win32serviceutil.ServiceFramework):
    _svc_name_ = "VesselNode"
    _svc_display_name_ = "Vessel Service Node"

    _config = configparser.ConfigParser()

    _log_dir = None
    _role = None

    _node_process = None

    def __init__(self, args):
        win32serviceutil.ServiceFramework.__init__(self, args)
        self.hWaitStop = win32event.CreateEvent(None, 0, 0, None)

        self._config.read(os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
                          + '/conf/service.ini')

        self._log_dir = self._config["LOGGING"]["log_dir"]
        self._root_dir = self._config["DEFAULT"]["root_dir"]
        log_path = self._log_dir + "/node-service.log"

        self._logger = logging.getLogger(self._svc_name_)
        self._logger.setLevel(logging.DEBUG)
        max_file_size = self._config["LOGGING"]["max_file_size"]
        max_file_count = self._config["LOGGING"]["max_file_count"]
        handler = RotatingFileHandler(log_path, maxBytes=int(max_file_size), backupCount=int(max_file_count))
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        self._logger.addHandler(handler)

    def SvcStop(self):
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        win32event.SetEvent(self.hWaitStop)

    def SvcDoRun(self):
        self.ReportServiceStatus(win32service.SERVICE_RUNNING)
        servicemanager.LogMsg(servicemanager.EVENTLOG_INFORMATION_TYPE,
                              servicemanager.PYS_SERVICE_STARTED,
                              (self._svc_name_, ''))

        self._logger.info("Service Is Starting")
        self.main()

    def main(self):

        self._logger.info("Service Is Initializing...")

        # setup database
        sqlite_manager = SQLiteManager(self._config, self._logger)

        # catalogue all the scripts in the system
        self._logger.info("Catalogueing Scripts On The System")
        known_scripts = sqlite_manager.getAllScripts()
        script_files = os.listdir(self._root_dir + "/scripts")
        for script_file in script_files:
            if len([known_script for known_script in known_scripts if known_script.file_name == script_file]) == 0:
                # this script is not known
                engine_name = vh.determine_engine_for_script(script_file)

                if engine_name is None:
                    self._logger.error("Could Not Determine Appropriate Engine For Script: " + str(script_file)
                                       + " Script Will Not Be Catalogued")
                    continue

                script = Script()
                script.file_name = script_file
                script.script_engine = engine_name
                sqlite_manager.insertScript(script)

        self._logger.info("Removing Record Entries For Scripts No Longer On The System")
        for known_script in known_scripts:
            if len([script_file for script_file in script_files if script_file == known_script.file_name]) == 0:
                # this script doesn't exist in the file system
                sqlite_manager.deleteScriptOfId(known_script.id)

        # create process for listening for node connections
        #  READ through parent_pipe, WRITE through child_pipe
        try:
            self._logger.info("Now Creaitng Pipe")
            parent_pipe, child_pipe = Pipe()
            self._logger.info("Now Creating NodeClientProcess Class")
            # node_listener = NodeListenerProcess(to_parent_pipe, to_child_pipe, self._config)
            self._logger.info("Now Creating Process With BootStrapper")
            self._node_process = Process(target=bootstrapper,
                                         args=(NodeClientProcess, (child_pipe, self._config)))
            self._logger.info("Now Starting Process")
            self._node_process.start()
            self._logger.info("Node Process Has Started Running")
        except Exception as e:
            self._logger.exception("An Exception Was Thrown Starting The Node Listener Process")
            self._logger.error("Later - An Exception Was Thrown")

            return

        # create process for listening for http connections

        rc = None
        while rc != win32event.WAIT_OBJECT_0:
            self._logger.info("Service Is Now Running")

            # hang for 1 minute or until service is stopped - whichever comes first
            rc = win32event.WaitForSingleObject(self.hWaitStop, (1 * 60 * 1000))

        self._node_process.terminate()


if __name__ == '__main__':
    win32serviceutil.HandleCommandLine(AppServerSvc)