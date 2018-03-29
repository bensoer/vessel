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
from utils.terminal_listener_process import TerminalListenerProcess
from utils.http_listener_process import HttpListenerProcess
import utils.vesselhelper as vh
from db.models.Script import Script
import threading
import json


def bootstrapper(wrapper_object, initialization_tuple):
    instance = wrapper_object(initialization_tuple)
    instance.start()
    exit(0)

def pipe_recv_handler(master_process, parent_pipe):
    master_process._logger.info("Pipe Recv Handler Spawned. Listening For Messages")
    while True:
        command = parent_pipe.recv()
        master_process._logger.info("Received Command: " + str(command))

        message_for = command["to"]

        if message_for == "NODE":
            master_process._logger.info("Message Is For NODE. Forwarding To Node Process")
            master_process.sendMessageToNodeProcess(command)
        elif message_for == "TERMINAL":
            master_process.sendMessageToTerminalProcess(command)
        elif message_for == "HTTP":
            master_process.sendMessageToHttpProcess(command)
        elif message_for == "MASTER":
            answer = master_process.handle_master_requests(command)
            # send the answer back wherever it came (most likely the http)
            parent_pipe.send(answer)
        else:
            master_process._logger.warning("Could Not Determine What Message Is For. Can't Forward Appropriatly")



class AppServerSvc (win32serviceutil.ServiceFramework):
    _svc_name_ = "VesselService"
    _svc_display_name_ = "Vessel Service Engine"

    _config = configparser.ConfigParser()

    _log_dir = None
    _root_dir = None
    _role = None

    _node_process = None
    _terminal_process = None
    _http_process = None

    terminal_parent_pipe = None
    node_parent_pipe = None
    http_parent_pipe = None

    def __init__(self,args):
        win32serviceutil.ServiceFramework.__init__(self,args)
        self.hWaitStop = win32event.CreateEvent(None, 0, 0, None)

        self._config.read(os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
                          + '/conf/service.ini')

        self._log_dir = self._config["LOGGING"]["log_dir"]
        self._root_dir = self._config["DEFAULT"]["root_dir"]
        log_path = self._log_dir + "/master-service.log"

        self._logger = logging.getLogger(self._svc_name_)
        self._logger.setLevel(logging.DEBUG)
        handler = RotatingFileHandler(log_path, maxBytes=4096, backupCount=10)
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
                              (self._svc_name_,''))

        self._logger.info("Service Is Starting")
        self.main()

    def handle_master_requests(self, command):

        if command['command'] == "EXEC" and command['params'] == "SCAN.SCRIPTS":
            sqlite_manager = SQLiteManager(self._config, self._logger)
            self.catalogue_local_scripts(sqlite_manager)
            sqlite_manager.closeEverything()

            old_from = command['from']
            command['from'] = command['to']
            command['to'] = old_from
            command['param'] = "SUCCESS"
            command['rawdata'] = ""

            return command

    def catalogue_local_scripts(self, sqlite_manager):
        self._logger.info("Searching For New Scripts On The System")
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


    def main(self):

        self._logger.info("Service Is Initializing...")

        # setup database
        sqlite_manager = SQLiteManager(self._config, self._logger)

        self._logger.info("Master Role Detected. Setting Up Service For Master Role")

        # catalogue all the scripts in the system
        self._logger.info("Catalogueing Scripts On The System")
        #sqlite_manager.deleteAllScripts()
        self.catalogue_local_scripts(sqlite_manager)

        # create process for listening for terminal connections
        try:
            self._logger.info("Now Creating Pipe For Terminal Process")
            terminal_parent_pipe, terminal_child_pipe = Pipe()
            self.terminal_parent_pipe = terminal_parent_pipe
            self._logger.info("Now Creating TerminalListenerProcess Class")
            self._logger.info("Now Creating Process With Boostrapper")
            self._terminal_process = Process(target=bootstrapper, args=(TerminalListenerProcess, (terminal_child_pipe, self._config)))
            self._logger.info("Now Starting Process")
            self._terminal_process.start()
            self._logger.info("Termina Process Has Started Running")
        except Exception as e:
            self._logger.exception("An Exception Was Thrown Starting The Node Listener Process")
            self._logger.error("Later - An Exception Was Thrown")

            return

        # create process for listening for node connections
        #  READ through parent_pipe, WRITE through child_pipe
        try:
            self._logger.info("Now Creating Pipe For Node Process")
            node_parent_pipe, node_child_pipe = Pipe()
            self.node_parent_pipe = node_parent_pipe
            self._logger.info("Now Creating NodeListenerProcess Class")
            #node_listener = NodeListenerProcess(to_parent_pipe, to_child_pipe, self._config)
            self._logger.info("Now Creating Process With BootStrapper")
            self._node_process = Process(target=bootstrapper, args=(NodeListenerProcess,(node_child_pipe, self._config)))
            self._logger.info("Now Starting Process")
            self._node_process.start()
            self._logger.info("Http Process Has Started Running")
        except Exception as e:
            self._logger.exception("An Exception Was Thrown Starting The Node Listener Process")
            self._logger.error("Later - An Exception Was Thrown")

            return

        # create process for listening for http connections
        try:
            self._logger.info("Now Creating Pipe For Http Process")
            http_parent_pipe, http_child_pipe = Pipe()
            self.http_parent_pipe = http_parent_pipe
            self._logger.info("Now Creating HttpListenerProcess Class")
            self._logger.info("Now Creating Process With Bootstrapper")
            self._http_process = Process(target=bootstrapper, args=(HttpListenerProcess, (http_child_pipe, self._config)))
            self._logger.info("Now Starting Http Process")
            self._http_process.start()
            self._logger.info("Http Process Has Started Running")
        except Exception as e:
            self._logger.exception("An Exception Was Thrown Starting The Http Listener Process")
            self._logger.error("Later - An Exception Was Thrown")

            return

        # spawn threads to handle listening for commands from these three sources

        self._logger.info("Launching Pipe Listening Thread For Terminal Process")
        t_thread = threading.Thread(target=pipe_recv_handler,
                                    args=(self, terminal_parent_pipe))
        t_thread.daemon = True
        t_thread.start()

        self._logger.info("Launching Pipe Listening Thread For Node Process")
        n_thread = threading.Thread(target=pipe_recv_handler,
                                    args=(self, node_parent_pipe))
        n_thread.daemon = True
        n_thread.start()

        self._logger.info("Launching Pipe Listening Thread For Http Process")
        h_thread = threading.Thread(target=pipe_recv_handler,
                                    args=(self, http_parent_pipe))
        h_thread.daemon = True
        h_thread.start()


        rc = None
        while rc != win32event.WAIT_OBJECT_0:
            self._logger.info("Service Is Now Running")


            # hang for 1 minute or until service is stopped - whichever comes first
            rc = win32event.WaitForSingleObject(self.hWaitStop, (1 * 60 * 1000))

        self._node_process.terminate()
        self._terminal_process.terminate()
        self._http_process.terminate()


    def sendMessageToNodeProcess(self, message):
        self._logger.info("Sending Message To Node Process")
        self.node_parent_pipe.send(message)

    def sendMessageToHttpProcess(self, message):
        self._logger.info("Sending Message To Http Process")
        self.http_parent_pipe.send(message)

    def sendMessageToTerminalProcess(self, message):
        self._logger.info("Sending Message To Terminal Process")
        self.terminal_parent_pipe(message)


if __name__ == '__main__':
    win32serviceutil.HandleCommandLine(AppServerSvc)