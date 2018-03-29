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
import json
from queue import Queue


def logging_handler(node_listener_process, logging_queue):
    while True:
        queue_item = logging_queue.get(block=True)
        node_listener_process.logger.info(queue_item)


def pipe_recv_handler(node_listener_process, logging_queue, child_pipe):
    logging_queue.put("Pipe Recv Handler Spawned. Listening For Messages")
    while True:
        logging_queue.put("CHECKING")
        command = child_pipe.recv()
        logging_queue.put("GOT SOMETHING")
        logging_queue.put("Received Command: " + str(command))

        send_success = False
        if command['command'] == 'GET':
            node_guid = command['rawdata']
            send_success = node_listener_process.forwardCommandToAppropriateNode(command, node_guid)
        elif command['command'] == 'EXEC':
            node_guid = command['rawdata'][0]
            send_success = node_listener_process.forwardCommandToAppropriateNode(command, node_guid)
        elif command['command'] == 'MIG':
            node_guid = command['rawdata'][0]
            send_success = node_listener_process.forwardCommandToAppropriateNode(command, node_guid)

        # if the send fails or not of the IFs meet - then return an error back so the client can be informed
        if not send_success:
            error_response = dict()
            error_response['command'] = 'ERROR'
            error_response['from'] = 'pipe_recv_handler'
            error_response['to'] = command['from']
            # (command, command_from, command_to, send_success)
            error_response['param'] = (command['command'], command['from'], command['to'], send_success)
            error_response['rawdata'] = "Send Of Message To Node Failed OR IF Condition To Parse node_guid failed"
            child_pipe.send(error_response)


def socket_recv_handler(node_listener_process, logging_queue, node_socket, child_pipe):
    logging_queue.put("Starting Socket Receive Handler")
    while True:
        try:
            command = node_socket.recv(4096)
            logging_queue.put("COMMAND RECEIVED FROM SOCKET")
            logging_queue.put(command)

            command_dict = json.loads(command)
            child_pipe.send(command_dict)
        except error as se:
            if se.errno == errno.ECONNRESET:
                logging_queue.put("Connection Reset Detected. Failed To Send Message To Node. Node Does Not Exist")

                # cleanup socket information on our side
                try:
                    node_socket.shutdown(socket.SHUT_RDWR)
                except:
                    pass
                try:
                    node_socket.close()
                except:
                    pass

                address = node_listener_process.__socketmap2portip[node_socket]
                ip, port = address
                del node_listener_process.__portipmap2socket[ip + ":" + str(port)]
                del node_listener_process.__connections[node_socket.fileno()]

                sql_manager = SQLiteManager(node_listener_process._config, node_listener_process.logger)
                node = sql_manager.getNodeOfIpAndPort(ip, port)

                sql_manager.deleteKeyOfGuid(node.key_guid)
                sql_manager.deleteNodeOfGuid(node.guid)
                sql_manager.closeEverything()  # can't use sql_manager after this

                del node_listener_process.__socketmap2portip[node_socket]

class NodeListenerProcess:

    _sql_manager = None
    child_pipe = None
    _port = None
    logger = None
    logging_queue = Queue(2048)

    _master_private_key = None
    _master_public_key = None
    _private_key_password = None

    __connections = dict()
    __portipmap2socket = dict()
    __socketmap2portip = dict()

    _config = None

    _all_to_read = []

    def __init__(self, initialization_tuple):
        child_pipe, config = initialization_tuple

        self.child_pipe = child_pipe
        self._config = config

        self._port = config["NODELISTENER"]["port"]
        self._bind_ip = config["NODELISTENER"]["bind_ip"]
        self._log_dir = config["NODELISTENER"]["log_dir"]
        self._private_key_password = config["DEFAULT"]["private_key_password"]
        log_path = self._log_dir + "/master-node.log"

        self.logger = logging.getLogger("NodeListenerProcess")
        self.logger.setLevel(logging.DEBUG)
        max_file_size = self._config["LOGGING"]["max_file_size"]
        max_file_count = self._config["LOGGING"]["max_file_count"]
        handler = RotatingFileHandler(log_path, maxBytes=int(max_file_size), backupCount=int(max_file_count))
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)

        self.logger.info("NodeListenerProcess Inialized. Creating Connection To SQL DB")

        self._sql_manager = SQLiteManager(config, self.logger)

        self.logger.info("Connection Complete")

    def forwardCommandToAppropriateNode(self, command, node_guid):
        self.logging_queue.put("Now Attempting Forwarding Command To Appropriate Node")
        self.logging_queue.put("Searching For Socket Matching Node Guid: " + node_guid)

        sql_manager = SQLiteManager(self._config, self.logger)
        node = sql_manager.getNodeOfGuid(node_guid)
        self.logging_queue.put("Search Mapped To IP: " + node.ip + " And PORT: " + node.port)
        node_socket2 = self.__portipmap2socket[node.ip + ":" + str(node.port)]

        serialized_command = json.dumps(command)
        self.logging_queue.put("Serialized Command: >" + str(serialized_command) + "<")

        try:
            node_socket2.send(str(serialized_command).encode())
            self.logging_queue.put("Serialized Message Sent")
            sql_manager.closeEverything()  # can't use sql_manager after this
            return True
        except error as se:
            if se.errno == errno.ECONNRESET:
                self.logging_queue.put("Connection Reset Detected. Failed To Send Message To Node. Node Does Not Exist")

                # cleanup socket information on our side
                try:
                    node_socket2.shutdown(socket.SHUT_RDWR)
                except:
                    pass
                try:
                    node_socket2.close()
                except:
                    pass

                address = self.__socketmap2portip[node_socket2]
                ip, port = address
                del self.__portipmap2socket[node.ip + ":" + str(node.port)]
                del self.__connections[node_socket2.fileno()]

                sql_manager.deleteKeyOfGuid(node.key_guid)
                sql_manager.deleteNodeOfGuid(node.guid)
                sql_manager.closeEverything()  # can't use sql_manager after this

                del self.__socketmap2portip[node_socket2]

                # return False to tell caller
                return False
        finally:
            sql_manager.closeEverything()  # can't use sql_manager after this

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

            self.logger.info("Setting Up Queue For MultiThread Handling Of Logging")

            self.logger.info("Launching Logging Queue Thread")
            l = threading.Thread(target=logging_handler, args=(self, self.logging_queue))
            l.daemon = True
            l.start()

            self.logging_queue.put("Launching Pipe Listening Thread")
            t = threading.Thread(target=pipe_recv_handler, args=(self, self.logging_queue, self.child_pipe))
            t.daemon = True
            t.start()

            self.logging_queue.put("Initializing Listener Socket")
            # startup the listening socket
            #try:
            listener_socket = socket(AF_INET, SOCK_STREAM)
            listener_socket.bind((self._bind_ip, int(self._port)))
            listener_socket.listen(10)
            self.logging_queue.put("Storing Socket Information")
            # store listening socket fd
            self.__connections[listener_socket.fileno()] = listener_socket
            self.logging_queue.put("Now Entering Connection Acceptance Loop")

            while True:

                node_socket, address = listener_socket.accept()
                self.logging_queue.put("New Connection Detected. Processing And Adding To System")

                # add mapping table records
                self.__connections[node_socket.fileno()] = node_socket
                self.__socketmap2portip[node_socket] = address
                client_ip, client_port = address
                self.__portipmap2socket[client_ip + ":" + str(client_port)] = node_socket

                self.logging_queue.put("Passing Security Keys To The New Node")
                # read the public key from the node for the system
                node_public_key = node_socket.recv(2048)
                # send our public key for the node
                node_socket.send(self._master_public_key)



                self.logging_queue.put("Adding Key To DB")
                # add the key to our db
                key = Key()
                key.key = node_public_key.decode('utf-8')
                key.name = "node.key.public"
                key = self._sql_manager.insertKey(key)

                self.logging_queue.put("Adding Node To DB")
                # add this node to our db
                node = Node()
                node.ip = client_ip
                node.port = client_port
                node.name = "node"
                node.key_guid = key.guid

                self._sql_manager.insertNode(node)

                self.logging_queue.put("New Connection Establishment Complete")

                self.logging_queue.put("Now Spawning Processing Thread To Handle Future Reads By This Socket")

                self.logging_queue.put("Launching Socket Listening Thread")
                t = threading.Thread(target=socket_recv_handler, args=(self, self.logging_queue, node_socket, self.child_pipe))
                t.daemon = True
                t.start()

                self.logging_queue.put("Processing Of New Connection Complete")

        except Exception as e:
            self.logger.exception("Error Processing For Node Listener")