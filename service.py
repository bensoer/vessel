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
from utils.node_listener_process import NodeListenerProcess


def bootstrapper(wrapper_object, initialization_tuple):
    instance = wrapper_object(initialization_tuple)
    instance.start()


class AppServerSvc (win32serviceutil.ServiceFramework):
    _svc_name_ = "VesselService"
    _svc_display_name_ = "Vessel Service Engine"

    _config = configparser.ConfigParser()

    _log_dir = None
    _role = None

    _node_process = None

    def __init__(self,args):
        win32serviceutil.ServiceFramework.__init__(self,args)
        self.hWaitStop = win32event.CreateEvent(None, 0, 0, None)

        self._config.read(os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
                          + '/conf/service.ini')

        self._log_dir = self._config["DEFAULT"]["log_dir"]
        log_path = self._log_dir + "/service.log"

        self._logger = logging.getLogger(self._svc_name_)
        self._logger.setLevel(logging.DEBUG)
        handler = RotatingFileHandler(log_path, maxBytes=4096, backupCount=10)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        self._logger.addHandler(handler)

        self._role = self._config["DEFAULT"]["role"]

    def SvcStop(self):
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        win32event.SetEvent(self.hWaitStop)

    def SvcDoRun(self):
        self.ReportServiceStatus(win32service.SERVICE_RUNNING)
        servicemanager.LogMsg(servicemanager.EVENTLOG_INFORMATION_TYPE,
                              servicemanager.PYS_SERVICE_STARTED,
                              (self._svc_name_,''))

        self._logger.info("Service Is Starting")
        self.main()

    def main(self):

        self._logger.info("Service Is Initializing...")

        # setup database
        sqlite_manager = SQLiteManager(self._config)

        if self._role == "master":
            self._logger.info("Master Role Detected. Setting Up Service For Master Role")

            # create process for listening for terminal connections

            # create process for listening for node connections
            #  READ through parent_pipe, WRITE through child_pipe
            try:
                self._logger.info("Now Creaitng Pipe")
                to_parent_pipe, to_child_pipe = Pipe()
                self._logger.info("Now Creating NodeListenerProcess Class")
                #node_listener = NodeListenerProcess(to_parent_pipe, to_child_pipe, self._config)
                self._logger.info("Now Creating Process With BootStrapper")
                self._node_process = Process(target=bootstrapper, args=(NodeListenerProcess,(to_parent_pipe, to_child_pipe, self._config)))
                self._logger.info("Now Starting Process")
                self._node_process.start()
                self._logger.info("Node Process Has Started Running")
            except Exception as e:
                self._logger.exception("An Exception Was Thrown")
                self._logger.error("Later - An Exception Was Thrown")

                return

            # create process for listening for http connections


        elif self._role == "node":
            pass
        else:
            self._logger.error("Role Is Required In Configuration. Vessel Can't Operate. Terminating")
            return


        rc = None
        while rc != win32event.WAIT_OBJECT_0:
            self._logger.info("Service Is Now Running")


            # hang for 1 minute or until service is stopped - whichever comes first
            rc = win32event.WaitForSingleObject(self.hWaitStop, (1 * 60 * 1000))

        self._node_process.terminate()

if __name__ == '__main__':
    win32serviceutil.HandleCommandLine(AppServerSvc)