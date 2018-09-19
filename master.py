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
from proc.node_listener_process import NodeListenerProcess
from proc.terminal_listener_process import TerminalListenerProcess
from proc.http_listener_process import HttpListenerProcess
import threading
import utils.taskrunner as taskrunner
import utils.script_manager as sm
import time


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
            master_process.sendMessageToNodeProcess(command)
        elif message_for == "TERMINAL":
            master_process.sendMessageToTerminalProcess(command)
        elif message_for == "HTTP":
            master_process.sendMessageToHttpProcess(command)
        elif message_for == "MASTER":
            answer = master_process.handle_master_requests(command)
            # send the answer back wherever it came (most likely the http)
            # send answer if it is not None
            if answer is not None:
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
    _script_dir = None

    _node_process = None
    _terminal_process = None
    _http_process = None

    terminal_parent_pipe = None
    node_parent_pipe = None
    http_parent_pipe = None

    shutdown_occurring = False
    shutdown_processing_complete = False


    def __init__(self,args):
        win32serviceutil.ServiceFramework.__init__(self,args)
        self.hWaitStop = win32event.CreateEvent(None, 0, 0, None)

        self._config.read(os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
                          + os.sep + 'conf' + os.sep + 'service.ini')

        self._log_dir = self._config["LOGGING"]["log_dir"]
        self._root_dir = self._config["DEFAULT"]["root_dir"]
        self._script_dir = self._config["DEFAULT"].get("scripts_dir", self._root_dir + "/scripts")


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
        self.shutdown_occurring = True

        self._logger.info("Service Is Stopping")

        self._logger.info("Fetching All Nodes To Send Restart Requests")
        # get list of all the nodes
        sql_manager = SQLiteManager(self._config, self._logger)
        all_nodes = sql_manager.getAllNodes()
        self._logger.info("Nodes Fetched. Parsing")

        self._logger.info("Parsing Complete")

        self._logger.info("Nodes Fetched. Now Sending")
        # send message to each node to disconnect, sleep and then start infinite reconnect attempts
        for node in all_nodes:
            action = dict()
            action['command'] = "SYS"
            action['from'] = "MASTER"
            action['to'] = "NODE"
            action['params'] = "RESTART"
            action['rawdata'] = (str(node.guid),)

            self.sendMessageToNodeProcess(action)

        self._logger.info("Now Waiting For Nodes To Disconnect")
        # wait for all the nodes to disconnect via checking the db
        while len(sql_manager.getAllNodes()) > 0:
            time.sleep(2)
            pass

        self._logger.info("Parse Complete. Closing Connection")
        sql_manager.closeEverything()

        # now it is safe to terminate
        self.shutdown_processing_complete = True
        self._logger.info("Shutdown Processing Completed")

    def SvcDoRun(self):
        self.ReportServiceStatus(win32service.SERVICE_RUNNING)
        servicemanager.LogMsg(servicemanager.EVENTLOG_INFORMATION_TYPE,
                              servicemanager.PYS_SERVICE_STARTED,
                              (self._svc_name_,''))

        self._logger.info("Service Is Starting")
        self.main()

    def handle_master_requests(self, command):

        # TODO: This is called if there is an error made by a request sent by master process. If master process
        # TODO: makes calls using the pipes, it would be able to wait at the calling code point for the response
        # TODO: this may be more ideal ??
        if command['command'] == "ERROR":
            self._logger.error("Error Command Received")
            self._logger.error(command)
            return None

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

        if command['command'] == "EXEC" and command['params'] == "SCRIPTS.EXECUTE":

            sqlite_manager = SQLiteManager(self._config, self._logger)
            response = taskrunner.execute_script_on_node(sqlite_manager, command, self._logger)
            sqlite_manager.closeEverything()

            return response

        if command['command'] == "GET" and command['params'] == "PING":
            return taskrunner.get_ping_info(command, self._config)


    def main(self):

        self._logger.info("Service Is Initializing...")

        # setup database
        sqlite_manager = SQLiteManager(self._config, self._logger)

        self._logger.info("Master Role Detected. Setting Up Service For Master Role")

        # catalogue all the scripts in the system
        self._logger.info("Catalogueing Scripts On The System")
        sm.catalogue_local_scripts(sqlite_manager, self._script_dir, self._logger)

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

        self._logger.info("Service Shutdown Detected In Main Loop. Waiting For Shutdown Process To Complete")
        # don't terminate processes until all of the shutdown procedure has completed
        while not self.shutdown_processing_complete:
            # loop until its done
            pass

        self._logger.info("Shutdown Process Completed. Terminating Other Processes")
        # now temrinate processes
        self._node_process.terminate()
        self._terminal_process.terminate()
        self._http_process.terminate()

        self._logger.info("Main Loop Termination Completed. Terminating")


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