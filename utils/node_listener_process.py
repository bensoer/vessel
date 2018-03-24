from socket import *
import select
from db.models.Node import Node
from db.models.Key import Key
import logging
from logging.handlers import RotatingFileHandler
from db.sqlitemanager import SQLiteManager
import threading
import utils.vesselhelper as vh


def pipe_recv_handler(node_listener_process):
    node_listener_process.logger.info("Pipe Recv Handler Spawned. Listening For Messages")
    while True:
        command = node_listener_process.to_child_pipe.recv()
        node_listener_process.logger.info("Received Command: " + str(command))

class NodeListenerProcess:

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

        self._port = config["NODELISTENER"]["port"]
        self._log_dir = config["NODELISTENER"]["log_dir"]
        self._private_key_password = config["DEFAULT"]["private_key_password"]
        log_path = self._log_dir + "/master-service.log"

        self.logger = logging.getLogger("NodeListenerProcess")
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

            self.logger.info("Fetching/Generating Public And Private Keys For Node Communication")

            private_key = self._sql_manager.getKeyOfName("master-me.key.private")
            public_key = self._sql_manager.getKeyOfName("master-me.key.public")

            # FIXME: There is no proper handling IF one of the keys exists and the other doesn't!
            if private_key is None or public_key is None:
                self._master_private_key = vh.generate_private_key(self._private_key_password)
                self._master_public_key = vh.generate_public_key(self._master_private_key, self._private_key_password)

                private_key = Key()
                private_key.name = "master-me.key.private"
                private_key.key = self._master_private_key.decode('utf-8')
                self._sql_manager.insertKey(private_key)

                public_key = Key()
                public_key.name = "master-me.key.public"
                public_key.key = self._master_public_key.decode('utf-8')
                self._sql_manager.insertKey(public_key)
            else:
                self._master_private_key = private_key.key
                self._master_public_key = public_key.key

            self.logger.info("Initializing Listener Socket")
            # startup the listening socket
            #try:
            listener_socket = socket(AF_INET, SOCK_STREAM)
            #listener_socket.setsockopt(SOL_SOCKET, socket.SO_REUSEADDR, 1)
            #listener_socket.setsockopt(SOL_SOCKET, socket.SO_REUSEPORT, 1)
            #listener_socket.setblocking(0)
            listener_socket.bind(('localhost', int(self._port)))
            listener_socket.listen(10)


            self.logger.info("Storing Socket Information")
            # store listening socket fd
            self.__connections[listener_socket.fileno()] = listener_socket

            # store pipe connection socket
            #self.__connections[self.to_child_pipe.fileno()] = self.to_child_pipe

            self.logger.info("Launching Pipe Listening Thread")
            t = threading.Thread(target=pipe_recv_handler, args=(self,))
            t.daemon = True
            t.start()

            self.logger.info("Preparing Select")
            # start select
            all_to_read = [listener_socket]
            all_to_write = []

            self.logger.info("Now Entering Select Loop")
            ready_to_read, ready_to_write, ready_to_exception = select.select(all_to_read, all_to_write, all_to_read)

            # TODO: Error Handling
            for error_socket in ready_to_exception:
                pass

            for readable_socket in ready_to_read:
                if readable_socket.fileno() == listener_socket.fileno():
                    # this is a new connection - A NEW NODE
                    self.logger.info("New Connection Detected. Processing And Adding To System")

                    node_socket, address = listener_socket.accept()
                    self.__connections[node_socket.fileno()] = node_socket

                    # read the public key from the node for the system
                    node_public_key = node_socket.recv(2048)
                    # send our public key for the node
                    node_socket.send(self._master_public_key)

                    client_ip, client_port = address

                    # add the key to our db
                    key = Key()
                    key.key = node_public_key.decode('utf-8')
                    key.name = "node.key.public"
                    key = self._sql_manager.insertKey(key)

                    # add this node to our db
                    node = Node()
                    node.ip = client_ip
                    node.name = "node"
                    node.key_guid = key.guid

                    self._sql_manager.insertNode(node)

                elif readable_socket.fileno() == self.to_child_pipe.fileno():
                    # this is a message from the service
                    pass
                else:
                    # this is one of the already connected sockets with something to say
                    pass

        except Exception as e:
            self.logger.exception("Error Processing For Node Listener")