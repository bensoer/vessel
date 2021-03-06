import win32serviceutil
import win32service
import win32event
import servicemanager
import configparser
import os
import inspect
from multiprocessing import Process, Pipe
from db.sqlitemanager import SQLiteManager
from proc.node_client_process import NodeClientProcess
import utils.script_manager as sm
import utils.logging as logutils


def pipe_recv_handler(node_process, parent_pipe):
    node_process._logger.info("Node Pipe Recv Handler Spawned. Listening For Messages")
    while True:
        command = parent_pipe.recv()
        node_process._logger.info("Received Command: " + str(command))

        message_for = command["to"]

        if message_for == "NODE":
            answer = node_process.handle_node_requests(command)
            # send the answer back wherever it came (most likely the http)
            # send answer if it is not None
            if answer is not None:
                parent_pipe.send(answer)
        else:
            node_process._logger.warning("Could Not Determine What Message Is For. Can't Forward Appropriatly")


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
    _script_dir = None

    def __init__(self, args):
        win32serviceutil.ServiceFramework.__init__(self, args)
        self.hWaitStop = win32event.CreateEvent(None, 0, 0, None)

        self._config.read(os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
                          + '/conf/service.ini')

        self._log_dir = self._config["LOGGING"]["log_dir"]
        self._root_dir = self._config["DEFAULT"]["root_dir"]
        self._script_dir = self._config["DEFAULT"].get("scripts_dir", self._root_dir + "/scripts")

        logutils.initialize_all_logging_configuration(self._log_dir)
        self._logger = logutils.node_logger


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

    def handle_node_requests(self, command):

        if command["command"] == "SYS" and command["param"] == "SHUTDOWN":
            self._logger.info("Shutdown Request Received. Terminating Node")
            self.SvcStop()
            return None

    def main(self):

        self._logger.info("Service Is Initializing...")

        # setup database
        sqlite_manager = SQLiteManager(self._config, self._logger)

        # catalogue all the scripts in the system
        self._logger.info("Catalogueing Engines On The System")
        sm.catalogue_local_engines(sqlite_manager, self._logger)
        self._logger.info("Catalogueing Scripts On The System")
        sm.catalogue_local_scripts(sqlite_manager, self._script_dir, self._logger)

        # create process for listening for node connections
        #  READ through parent_pipe, WRITE through child_pipe
        try:
            self._logger.info("Now Creating Pipe")
            parent_pipe, child_pipe = Pipe()
            self._logger.info("Now Creating NodeClientProcess Class")
            # node_listener = NodeListenerProcess(to_parent_pipe, to_child_pipe, self._config)
            self._logger.info("Now Creating Process With BootStrapper")
            self._node_process = Process(target=bootstrapper,
                                         args=(NodeClientProcess, (child_pipe, self._config, logutils.logging_queue)))
            self._logger.info("Now Starting Process")
            self._node_process.start()
            self._logger.info("Node Process Has Started Running")
        except Exception as e:
            self._logger.exception("An Exception Was Thrown Starting The Node Listener Process")
            self._logger.error("Later - An Exception Was Thrown")

            return

        # create process for listening for http connections

        # start logging thread
        l_thread = logutils.start_logging_thread()

        rc = None
        while rc != win32event.WAIT_OBJECT_0:
            self._logger.info("Service Is Now Running")

            # hang for 1 minute or until service is stopped - whichever comes first
            rc = win32event.WaitForSingleObject(self.hWaitStop, (1 * 60 * 1000))

        self._node_process.terminate()


if __name__ == '__main__':
    win32serviceutil.HandleCommandLine(AppServerSvc)