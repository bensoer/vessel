from socket import *
import select
from db.models.Node import Node
import logging
from logging.handlers import RotatingFileHandler
from db.sqlitemanager import SQLiteManager
import threading
import utils.vesselhelper as vh
from db.models.Key import Key

class NodeClientProcess:

    _node_private_key = None
    _node_public_key = None
    _master_public_key = None

    def __init__(self, initialization_tuple):
        to_parent_pipe, to_child_pipe, config = initialization_tuple

        self.to_child_pipe = to_child_pipe
        self._to_parent_pipe = to_parent_pipe

        self._port = config["NODELISTENER"]["port"]
        self._master_host = config["DEFAULT"]["master_domain"]
        self._log_dir = config["DEFAULT"]["log_dir"]
        self._private_key_password = config["DEFAULT"]["private_key_password"]
        log_path = self._log_dir + "/node-service.log"

        self.logger = logging.getLogger("NodeClientProcess")
        self.logger.setLevel(logging.DEBUG)
        handler = RotatingFileHandler(log_path, maxBytes=4096, backupCount=10)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)

        self.logger.info("NodeListenerProcess Inialized. Creating Connection To SQL DB")

        self._sql_manager = SQLiteManager(config, self.logger)

        self.logger.info("Connection Complete")

    def start(self):
        try:
            self.logger.info("Initializing Socket To Master")

            client_socket = socket(AF_INET, SOCK_STREAM)
            #client_socket.setblocking(0)
            client_socket.connect((self._master_host, int(self._port)))

            self.logger.info("Connection Established With Master. Securing Connection")

            # generate our RSA Private And Public Keys
            private_key = self._sql_manager.getKeyOfName("node-me.key.private")
            public_key = self._sql_manager.getKeyOfName("node-me.key.public")

            # FIXME: There is no proper handling IF one of the keys exists and the other doesn't!
            if private_key is None or public_key is None:
                self._node_private_key = vh.generate_private_key(self._private_key_password)
                self._node_public_key = vh.generate_public_key(self._node_private_key, self._private_key_password)

                private_key = Key()
                private_key.name = "node-me.key.private"
                private_key.key = self._node_private_key.decode('utf-8')
                self._sql_manager.insertKey(private_key)

                public_key = Key()
                public_key.name = "node-me.key.public"
                public_key.key = self._node_public_key.decode('utf-8')
                self._sql_manager.insertKey(public_key)
            else:
                self._node_private_key = private_key.key
                self._node_public_key = public_key.key

            client_socket.send(self._node_public_key)
            self._master_public_key = client_socket.recv(2048)

            self.logger.info("Connection Secured")

            


        except Exception as e:
            self.logger.exception("Error Processing For Node Client")