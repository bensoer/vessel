from socket import *
import errno
import select
from db.models.Node import Node
from db.models.Key import Key
import logging
from logging.handlers import RotatingFileHandler
from db.sqlitemanager import SQLiteManager
import threading
import utils.vesselhelper as vh



class TerminalListenerProcess:

    _sql_manager = None
    child_pipe = None
    _port = None
    logger = None

    _master_private_key = None
    _master_public_key = None
    _private_key_password = None

    __connections = dict()

    def __init__(self, initialization_tuple):
        child_pipe, config, logging_queue = initialization_tuple

        self.child_pipe = child_pipe

        self._port = config["TERMINALLISTENER"]["port"]
        self._bind_ip = config["TERMINALLISTENER"]["bind_ip"]
        self._log_dir = config["TERMINALLISTENER"]["log_dir"]
        self._private_key_password = config["DEFAULT"]["private_key_password"]

        qh = logging.handlers.QueueHandler(logging_queue)
        root = logging.getLogger()
        root.setLevel(logging.DEBUG)
        root.addHandler(qh)

        self.logger = logging.getLogger("TerminalListenerProcessLogger")
        self.logger.setLevel(logging.DEBUG)

        self.logger.info("TerminalListenerProcess Inialized. Creating Connection To SQL DB")

        self._sql_manager = SQLiteManager(config, self.logger)

        self.logger.info("Connection Complete")



    def start(self):
        try:

            self.logger.info("Initializing Listener Socket")
            # startup the listening socket
            # try:
            listener_socket = socket(AF_INET, SOCK_STREAM)
            listener_socket.bind((self._bind_ip, int(self._port)))
            listener_socket.listen(10)

            while True:

                # limit to only 1 terminal socket per vessel
                node_socket, address = listener_socket.accept()
                self.logger.info("A User Has Taken Hold Of The Terminal Session. Starting Timer And Auth")

                # exchange keys ?

                session_active = True
                while session_active:
                    # listen for commands
                    command = vh.read_command(node_socket)
                    # {something}


                    # get the command

                    # parse the command

                    # pass it to the main process ?

                    if command == "{exit}":
                        node_socket.shutdown()
                        node_socket.close()
                        session_active = False

        except Exception as e:
            self.logger.exception("Error Processing For Terminal Listener")
