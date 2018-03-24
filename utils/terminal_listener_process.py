from socket import *
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
    to_child_pipe = None
    _to_parent_pipe = None
    _port = None
    logger = None

    _master_private_key = None
    _master_public_key = None
    _private_key_password = None

    __connections = dict()

    # WRITE through parent_pipe, READ through child_pipe
    def __init__(self, initialization_tuple):
        to_parent_pipe, to_child_pipe, config = initialization_tuple

        self.to_child_pipe = to_child_pipe
        self._to_parent_pipe = to_parent_pipe

        self._port = config["TERMINALLISTENER"]["port"]
        self._log_dir = config["TERMINALLISTENER"]["log_dir"]
        self._private_key_password = config["DEFAULT"]["private_key_password"]
        log_path = self._log_dir + "/master-service.log"

        self.logger = logging.getLogger("TerminalListenerProcess")
        self.logger.setLevel(logging.DEBUG)
        handler = RotatingFileHandler(log_path, maxBytes=4096, backupCount=10)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)

        self.logger.info("TerminalListenerProcess Inialized. Creating Connection To SQL DB")

        self._sql_manager = SQLiteManager(config, self.logger)

        self.logger.info("Connection Complete")

    def read_command(self, client_socket):

        full_command = ""

        buffer = ""
        # detected the start of a message
        while buffer != "{":
            buffer = client_socket.recv(1)

        full_command += buffer
        while buffer != "}":
            buffer = client_socket.recv(1)

            if buffer == "\\":
                # if escaped blindly accept the next byte
                full_command += client_socket.recv(1)
                continue

            full_command += buffer

        full_command += buffer

        return full_command

    def start(self):
        try:

            self.logger.info("Initializing Listener Socket")
            # startup the listening socket
            # try:
            listener_socket = socket(AF_INET, SOCK_STREAM)
            # listener_socket.setsockopt(SOL_SOCKET, socket.SO_REUSEADDR, 1)
            # listener_socket.setsockopt(SOL_SOCKET, socket.SO_REUSEPORT, 1)
            # listener_socket.setblocking(0)
            listener_socket.bind(('localhost', int(self._port)))
            listener_socket.listen(10)

            while True:

                # limit to only 1 terminal socket per vessel
                node_socket, address = listener_socket.accept()

                # exchange keys ?

                session_active = True
                while session_active:
                    # listen for commands
                    command = self.read_command(node_socket)
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
