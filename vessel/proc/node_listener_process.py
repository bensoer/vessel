from socket import *
import errno
from db.models import Node, Ping
from db.models import Key
import logging
from logging.handlers import QueueHandler
from db import SQLiteManager
import threading
import utils.vesselhelper as vh
import json
import time
from threading import Lock
import uuid

ssl = None


def run_ping_cycle(logger, config, node_listener_process):
    logger.info("Starting Ping Cycle")

    sql_manager = SQLiteManager(config, logger)

    while True:
        time.sleep(120)  # - every 120 seconds
        logger.debug("Sleep Cycle Complete. Pinging All Nodes For Data")
        all_nodes = sql_manager.getAllNodes()

        for node in all_nodes:

            node.state = "PENDING"
            sql_manager.updateNode(node)

            command = dict()
            command["command"] = "SYS"
            command["params"] = "PING"
            command["to"] = "NODE"
            command["from"] = "MASTER"
            command["rawdata"] = (str(node.guid),)

            ping_record = Ping()
            ping_record.send_time = time.time()
            ping_record.node_guid = node.guid
            sql_manager.insertPing(ping_record)

            node_listener_process.forwardCommandToAppropriateNode(command, str(node.guid))

        del all_nodes

def pipe_recv_handler(node_listener_process, logger, child_pipe):
    logger.info("Pipe Recv Handler Spawned. Listening For Messages")
    while True:
        command = child_pipe.recv()
        logger.debug("Received Command: " + str(command))

        send_success = False
        if command['command'] == 'GET':
            node_guid = command['rawdata']
            send_success = node_listener_process.forwardCommandToAppropriateNode(command, node_guid)
        elif command['command'] == 'EXEC':
            node_guid = command['rawdata'][0]
            send_success = node_listener_process.forwardCommandToAppropriateNode(command, node_guid)
        elif command['command'] == 'MIG':
            node_guid = command['params'][0]
            send_success = node_listener_process.forwardCommandToAppropriateNode(command, node_guid)
        elif command['command'] == 'CREATE':
            node_guid = command['rawdata'][0]
            send_success = node_listener_process.forwardCommandToAppropriateNode(command, node_guid)
        elif command['command'] == 'SYS':
            node_guid = command['rawdata'][0]
            send_success = node_listener_process.forwardCommandToAppropriateNode(command, node_guid)
        else:
            error_response = dict()
            error_response['command'] = 'ERROR'
            error_response['from'] = 'pipe_recv_handler'
            error_response['to'] = command['from']
            # (command, command_from, command_to, send_success)
            error_response['params'] = (command['command'], command['from'], command['to'], send_success)
            error_response['rawdata'] = "A Handler For The Command: " + command["command"] + \
                                        " Does Not Exist. Could Not Process"

            logger.warn("Could Not Determine Handler For Received Command. Can't Process")
            logger.warn(str(error_response))
            child_pipe.send(error_response)

        # if the send fails or not of the IFs meet - then return an error back so the client can be informed
        if not send_success:
            error_response = dict()
            error_response['command'] = 'ERROR'
            error_response['from'] = 'pipe_recv_handler'
            error_response['to'] = command['from']
            # (command, command_from, command_to, send_success)
            error_response['params'] = (command['command'], command['from'], command['to'], send_success)
            error_response['rawdata'] = "Send Of Message To Node Failed"

            logger.warn(
                "Failed To Forward Command To Appropriate Node. Sending Error Response Back To Caller With Details")
            logger.warn(str(error_response))

            child_pipe.send(error_response)


def socket_recv_handler(node_listener_process, logger, node_socket, child_pipe):
    logger.info("Starting Socket Receive Handler")
    while True:
        sql_manager = SQLiteManager(node_listener_process._config, node_listener_process.logger)
        try:
            valid_message_received = False
            raw_message: bytes = b''

            while not valid_message_received:
                base64_encrypted_bytes = node_socket.recv(4096)
                raw_message += base64_encrypted_bytes

                if len(raw_message) > 0:
                    if raw_message[:1] == b'{' and raw_message[len(raw_message) - 1:] == b'}':
                        valid_message_received = True
                        raw_message = raw_message[1:len(raw_message)-1]

            # find the node belonging to this socket
            address = node_listener_process.socketmap2portip[node_socket]
            ip, port = address

            node = sql_manager.getNodeOfIpAndPort(ip, port)
            # find the aes key for this node
            key = sql_manager.getKeyOfGuid(node.key_guid)
            # decrypt the key
            aes_key = vh.decrypt_base64_bytes_with_private_key_to_bytes(key.key.encode(),
                                                                        node_listener_process.master_private_key,
                                                                        node_listener_process.private_key_password)

            command = vh.decrypt_base64_bytes_with_aes_key_to_string(raw_message, aes_key)
            logger.info("Command Received From Socket: " + str(command))

            command_dict = json.loads(command)

            if command_dict["command"] == "SYS" and command_dict["to"] == "MASTER" and command_dict["params"] == "CONN.CLOSE":
                # this means the remote node is gracefully exiting. We should treate this as if it disconnected
                logger.info("Graceful Disconnect From Node Detected. Throwing Exception To Trigger Disconnection")
                os_error = OSError()
                os_error.errno = errno.ECONNRESET
                raise os_error

            elif command_dict["command"] == "SYS" and command_dict["to"] == "MASTER" and command_dict["params"] == "PING":
                logger.debug("Internal Ping Call Received. Processing")

                node_guid = command_dict["rawdata"][0]
                last_sent_ping = sql_manager.getLastUnReturnedPingOfNode(uuid.UUID(node_guid))
                if last_sent_ping is None:
                    logger.error("Failed to find last ping entry for node. Ping stats may be obscured over next while")
                else:
                    last_sent_ping.recv_time = time.time()
                    sql_manager.updatePing(last_sent_ping)

                pinged_node = sql_manager.getNodeOfGuid(node_guid)
                pinged_node.state = "UP"
                sql_manager.updateNode(pinged_node)

            else:
                child_pipe.send(command_dict)

        except OSError as se:
            if se.errno == errno.ECONNRESET:
                logger.info("Connection Reset Detected. Failed To Receive Message From Node. Node Does Not Exist")

                # cleanup socket information on our side
                try:
                    node_socket.shutdown(socket.SHUT_RDWR)
                except:
                    pass
                try:
                    node_socket.close()
                except:
                    pass

                logger.info("Removing Socket From Mappings")
                address = node_listener_process.socketmap2portip[node_socket]
                ip, port = address
                node_listener_process.portipmap2socket.pop(ip+":"+str(port), None)
                node_listener_process.connections.pop(node_socket.fileno(), None)

                logger.info("Removing Socket From Database")
                sql_manager = SQLiteManager(node_listener_process._config, node_listener_process.logger)
                node = sql_manager.getNodeOfIpAndPort(ip, port)

                sql_manager.deleteKeyOfGuid(node.key_guid)
                sql_manager.deleteNodeOfGuid(node.guid)

                logger.info("Removing Socket From Last Mapping")
                node_listener_process.socketmap2portip.pop(node_socket, None)
                logger.info("Diconnection Process Of Node Complete. Terminating Socket Receive Handler Thread")
                break
            else:
                logger.info("Other Error Thrown")
                logger.info(se.strerror)
        finally:
            sql_manager.closeEverything()


class NodeListenerProcess:

    _sql_manager = None
    child_pipe = None
    _port = None
    logger = None

    master_private_key = None
    master_public_key = None
    private_key_password = None
    aes_key = None

    connections = dict()
    portipmap2socket = dict()
    socketmap2portip = dict()

    _config = None

    _all_to_read = []

    forwarding_mutex = Lock()

    def __init__(self, initialization_tuple):
        child_pipe, config, logging_queue = initialization_tuple

        self.child_pipe = child_pipe
        self._config = config

        self._port = config["NODELISTENER"]["port"]
        self._bind_ip = config["NODELISTENER"]["bind_ip"]
        self._log_dir = config["LOGGING"]["log_dir"]
        self.private_key_password = config["DEFAULT"]["private_key_password"]

        qh = logging.handlers.QueueHandler(logging_queue)
        root = logging.getLogger()
        root.setLevel(logging.DEBUG)
        root.addHandler(qh)

        self.logger = logging.getLogger("NodeListenerProcessLogger")
        self.logger.setLevel(logging.DEBUG)

        self.logger.info("NodeListenerProcess Inialized. Creating Connection To SQL DB")
        self._sql_manager = SQLiteManager(config, self.logger)
        self.logger.info("Connection Complete")

    def forwardCommandToAppropriateNode(self, command, node_guid: str)->bool:
        self.forwarding_mutex.acquire(blocking=True)
        self.logger.info("Now Attempting Forwarding Command To Appropriate Node")
        self.logger.info(("Searching For Socket Matching Node Guid: " + str(node_guid)))

        sql_manager = SQLiteManager(self._config, self.logger)

        node = sql_manager.getNodeOfGuid(str(node_guid))
        if node is None:
            self.logger.warning("Could Not Find Node Belonging To Guid: " + str(node_guid) +
                                ". Unable To Forward Message")
            self.forwarding_mutex.release()
            return False

        self.logger.info("Search Mapped To IP: " + node.ip + " And PORT: " + node.port)
        node_socket2 = self.portipmap2socket.get(node.ip + ":" + str(node.port), None)
        self.logger.info("Socket: " + str(node_socket2))

        if node_socket2 is None:
            self.logger.info("WARNING: IP and Port Mapping Did Not Resolve To A Socket. Can't Forward Command")
            self.forwarding_mutex.release()
            return False

        serialized_command = json.dumps(command)
        self.logger.info("Serialized Command: >" + str(serialized_command) + "<")

        try:
            key = sql_manager.getKeyOfGuid(node.key_guid)
            aes_key = vh.decrypt_base64_bytes_with_private_key_to_bytes(key.key.encode(),
                                                                         self.master_private_key,
                                                                         self.private_key_password)

            base64_encrypted_bytes = vh.encrypt_string_with_aes_key_to_base64_bytes(serialized_command,
                                                                                    aes_key)
            base64_encrypted_bytes = b'{' + base64_encrypted_bytes + b'}'
            node_socket2.send(base64_encrypted_bytes)
            self.logger.info("Serialized Message Sent")

            sql_manager.closeEverything()  # can't use sql_manager after this
            self.forwarding_mutex.release()
            del sql_manager
            return True
        except error as se:
            if se.errno == errno.ECONNRESET:
                self.logger.info("Connection Reset Detected. Failed To Send Message To Node. Node Does Not Exist")

                # cleanup socket information on our side
                try:
                    node_socket2.shutdown(socket.SHUT_RDWR)
                except:
                    pass
                try:
                    node_socket2.close()
                except:
                    pass

                self.logger.info("Removing Socket From Mappings")
                self.portipmap2socket.pop(node.ip+":"+str(node.port), None)
                self.connections.pop(node_socket2, None)

                self.logger.info("Removing Socket From Database")
                sql_manager.deleteKeyOfGuid(node.key_guid)
                sql_manager.deleteNodeOfGuid(node.guid)
                sql_manager.closeEverything()  # can't use sql_manager after this

                self.logger.info("Removing Socket From Last Mapping")
                self.socketmap2portip.pop(node_socket2, None)

                # return False to tell caller
                self.forwarding_mutex.release()
                return False
            else:
                self.logger.info("ERROR: Unknown Socket Error Occured In Node Listener Process. Error Code " + str(se.errno))
                self.logger.info("Error Details: " + se.strerror)
                self.logger.info(se)
        finally:
            sql_manager.closeEverything()  # can't use sql_manager after this
            del sql_manager


    def start(self):
        try:

            self.logger.info("Fetching/Generating Public And Private Keys For Node Communication")

            private_key = self._sql_manager.getKeyOfName("master-me.key.private")
            public_key = self._sql_manager.getKeyOfName("master-me.key.public")

            # FIXME: There is no proper handling IF one of the keys exists and the other doesn't!
            if private_key is None or public_key is None:
                self.master_private_key = vh.generate_private_key(self.private_key_password)
                self.master_public_key = vh.generate_public_key(self.master_private_key, self.private_key_password)

                private_key = Key()
                private_key.name = "master-me.key.private"
                private_key.key = self.master_private_key
                self._sql_manager.insertKey(private_key)

                public_key = Key()
                public_key.name = "master-me.key.public"
                public_key.key = self.master_public_key
                self._sql_manager.insertKey(public_key)
            else:
                self.master_private_key = private_key.key
                self.master_public_key = public_key.key

            self.logger.info("Launching Pipe Listening Thread")
            t = threading.Thread(target=pipe_recv_handler, args=(self, self.logger, self.child_pipe))
            t.daemon = True
            t.start()

            self.logger.info("Initializing Listener Socket")
            # startup the listening socket
            #try:
            listener_socket = socket(AF_INET, SOCK_STREAM)
            listener_socket.bind((self._bind_ip, int(self._port)))
            listener_socket.listen(10)

            if self._config["SSL"]["enabled"] == 'True':
                self.logger.info("SSL Sockets Enabled. Configuring SSL")

                global ssl
                import ssl

                ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
                ssl_context.load_cert_chain(self._config["SSL"]["master_cert"], self._config["SSL"]["master_key"])
                listener_socket = ssl_context.wrap_socket(listener_socket, server_side=True)

            self.logger.info("Storing Socket Information")
            # store listening socket fd
            self.connections[listener_socket.fileno()] = listener_socket

            self.logger.info("Now Starting Pinging Thread")
            p_thread = threading.Thread(target=run_ping_cycle,
                                        args=(self.logger, self._config, self))
            p_thread.daemon = True
            p_thread.start()

            self.logger.info("Now Entering Connection Acceptance Loop")

            while True:

                node_socket = None
                address = None

                if self._config["SSL"]["enabled"] == 'True':
                    try:
                        tpl_node_socket, tpl_address = listener_socket.accept()
                        node_socket = tpl_node_socket
                        address = tpl_address
                        self.logger.info("New Connection Detected. Processing And Adding To System")
                    except ssl.SSLEOFError:
                        self.logger.exception("SSLEOFError Occurred. Connection Was Terminated Abruptly. Can't Use " +
                                              "Anything From Sockets")
                        continue
                    except ssl.CertificateError as ce:
                        self.logger.exception("Certificate Error Occurred. Client Certificate Validation Failed. Not " +
                                              "Accepting Connection")
                        # python 3.7 has additional output that can be done here
                        continue
                    except ssl.SSLError:
                        self.logger.exception("Generic SSL Error Occurred. Aborting Connection Attempt")
                        continue
                else:
                    try:
                        tpl_node_socket, tpl_address = listener_socket.accept()
                        node_socket = tpl_node_socket
                        address = tpl_address
                        self.logger.info("New Connection Detected. Processing And Adding To System")
                    except:
                        self.logger.exception("Acceptance Of New Connection Failed. Aborting")
                        continue

                self.logger.info("Enabling Keep Alive Policy In New Connection")
                node_socket.ioctl(SIO_KEEPALIVE_VALS, (1, 10000, 3000))

                self.logger.info("Updating Memory Mappings For New Connection")
                # add mapping table records
                self.connections[node_socket.fileno()] = node_socket
                self.socketmap2portip[node_socket] = address
                client_ip, client_port = address
                self.portipmap2socket[client_ip + ":" + str(client_port)] = node_socket

                self.logger.info("Passing Security Keys To The New Node")

                #send the public key
                node_socket.send(self.master_public_key.encode())
                #get the encrypted aes key
                aes_key_encrypted = node_socket.recv(4096)

                # verify this key is valid
                try:
                    aes_key = vh.decrypt_base64_bytes_with_private_key_to_bytes(aes_key_encrypted,
                                                                                self.master_private_key,
                                                                                self.private_key_password)
                    decoded = aes_key_encrypted.decode('utf-8')
                except:
                    self.logger.exception("Incoming AES Key Is Invalid Or Failed Validation. Assuming Connection"
                                          "Is Invalid. Closing Connection")
                    node_socket.close()
                    continue

                self.logger.info("Making Ping Request To Retrieve Node Information")

                # pass a command to the node to fetch ping information and get the node name
                action = dict()
                action['command'] = "GET"
                action['from'] = "LISTENER"
                action['to'] = "NODE"
                action['params'] = "PING"

                serialized_command = json.dumps(action)
                aes_key = vh.decrypt_base64_bytes_with_private_key_to_bytes(aes_key_encrypted,
                                                                            self.master_private_key,
                                                                            self.private_key_password)
                base64_encrypted_bytes = vh.encrypt_string_with_aes_key_to_base64_bytes(serialized_command,
                                                                                        aes_key)

                node_socket.send(b'{' + base64_encrypted_bytes + b'}')
                self.logger.info("Request Sent")

                valid_message_received = False
                full_encrypted_bytes: bytes = b''

                while not valid_message_received:
                    self.logger.info("Getting Segment of Response")
                    encrypted_bytes = node_socket.recv(4096)
                    full_encrypted_bytes += encrypted_bytes

                    if len(full_encrypted_bytes) > 0:
                        if full_encrypted_bytes[:1] == b'{' and full_encrypted_bytes[len(full_encrypted_bytes) - 1:] == b'}':
                            valid_message_received = True
                            self.logger.info("Full Message Segment Parsed. Now Processing")

                # place back into encrypted_bytes the trimmed and fixed message
                encrypted_bytes = full_encrypted_bytes[1:len(full_encrypted_bytes)]
                command = vh.decrypt_base64_bytes_with_aes_key_to_string(encrypted_bytes, aes_key)
                command_dict = json.loads(command)

                if command_dict["command"] == "ERROR":
                    # connection had a fatal error
                    self.logger.info("Fatal Error Trying To Ping Recently Established Node. Failed To Complete "
                                           "Connection Sequence. Connection Will Be Terminated")
                    self.logger.info(command)
                    node_socket.close()
                    continue

                self.logger.info("Adding Key To DB")
                # add the key to our db
                key = Key()
                key.key = aes_key_encrypted.decode(
                    'utf-8')  # note this key is encrypted with our public key and then base64 encoded
                key.name = "node.key.aes"
                key = self._sql_manager.insertKey(key)

                node_name = command_dict['rawdata']['node-name']

                self.logger.info("Adding Node To DB")
                # add this node to our db
                node = Node()
                node.ip = client_ip
                node.port = client_port
                node.name = node_name
                node.key_guid = key.guid
                node.state = "UP"

                self._sql_manager.insertNode(node)
                self.logger.info("New Connection Establishment Complete")
                self.logger.info("Now Spawning Processing Thread To Handle Future Reads By This Socket")

                self.logger.info("Launching Socket Listening Thread")
                t = threading.Thread(target=socket_recv_handler, args=(self,
                                                                       self.logger,
                                                                       node_socket,
                                                                       self.child_pipe))
                t.daemon = True
                t.start()

                self.logger.info("Processing Of New Connection Complete")

        except Exception as e:
            self.logger.exception("Fatal / Unknown Error Processing For Node Listener. Node Listener Process"
                                  " Will Terminate")