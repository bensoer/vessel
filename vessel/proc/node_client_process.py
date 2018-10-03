from socket import *
import errno
import logging
from logging.handlers import QueueHandler
from db import SQLiteManager
import utils.vesselhelper as vh
import utils.script_manager as sm
from db.models import Key
import json
import utils.taskrunner as taskrunner
import time

ssl = None

class NodeClientProcess:

    _node_private_key = None
    _node_public_key = None
    _master_public_key = None
    _node_aes_key = None

    _script_dir = None
    _node_name = None

    _client_socket = None
    _config = None

    failed_initializing = False

    def __init__(self, initialization_tuple):
        child_pipe, config, logging_queue = initialization_tuple

        self.child_pipe = child_pipe
        self._config = config

        self._master_host = config["DEFAULT"]["master_domain"]
        self._master_port = config["DEFAULT"]["master_port"]
        self._log_dir = config["LOGGING"]["log_dir"]
        self._root_dir = config["DEFAULT"]["root_dir"]
        self._node_name = config["DEFAULT"].get("name", "node")

        self._script_dir = config["DEFAULT"].get("scripts_dir", self._root_dir + "/scripts")

        self._private_key_password = config["DEFAULT"]["private_key_password"]

        # setup logging
        qh = logging.handlers.QueueHandler(logging_queue)
        root = logging.getLogger()
        root.setLevel(logging.DEBUG)
        root.addHandler(qh)

        self.logger = logging.getLogger("NodeClientProcessLogger")
        self.logger.setLevel(logging.DEBUG)

        self.logger.info("NodeClientProcess Inialized. Creating Connection To SQL DB")

        self._sql_manager = SQLiteManager(config, self.logger)

        self.logger.info("Connection Complete")

    def _send_message(self, message:str, encrypt_with_key=None)->int:
        try:
            if encrypt_with_key is not None:

                node_private_key, node_private_key_password, node_aes_key = encrypt_with_key
                aes_key = vh.decrypt_base64_bytes_with_private_key_to_bytes(node_aes_key,
                                                                             node_private_key,
                                                                             node_private_key_password)

                base64_encrypted_bytes = vh.encrypt_string_with_aes_key_to_base64_bytes(message, aes_key)
                base64_encrypted_bytes = b'{' + base64_encrypted_bytes + b'}'
                return self._client_socket.send(base64_encrypted_bytes)
            else:
                return self._client_socket.send(message.encode())
        except OSError as se:
            if se.errno == errno.ECONNRESET:
                self.logger.info(
                    "Connection Reset Detected While Trying To Send Message. Attempting Connection Reestablishment")

                # close socket
                try:
                    self._client_socket.shutdown(socket.SHUT_RDWR)
                except:
                    pass
                try:
                    self._client_socket.close()
                except:
                    pass

                reconnect_succeeded = self.execute_connect_to_host_procedure()
                if not reconnect_succeeded:
                    self.logger.fatal("Connection Reestablishment Failed. Not Bothering Again. Terminating Process")

                    action = dict()
                    action['command'] = "SYS"
                    action['from'] = "CLIENT"
                    action['to'] = "NODE"
                    action['params'] = "SHUTDOWN"
                    self.child_pipe.send(action)

                    exit()
                    return 0
                else:
                    return self._send_message(message, encrypt_with_key=encrypt_with_key)
            else:
                self.logger.info("An OSError Was Thrown While Trying To Send Message")
                self.logger.info(se)
                return 0

    def _recv_message(self, buffer_size, decrypt_with_key_pass=None):
        try:

            raw_message: bytes = b''
            valid_message_received = False

            if decrypt_with_key_pass is not None:

                while not valid_message_received:
                    base64_encrypted_bytes = self._client_socket.recv(buffer_size)
                    raw_message += base64_encrypted_bytes

                    if len(raw_message) > 0:
                        if raw_message[:1] == b'{' and raw_message[len(raw_message) - 1:] == b'}':
                            valid_message_received = True
                            raw_message = raw_message[1:len(raw_message)-1]

                node_private_key, node_private_key_password, node_aes_key = decrypt_with_key_pass
                aes_key = vh.decrypt_base64_bytes_with_private_key_to_bytes(node_aes_key,
                                                                             node_private_key,
                                                                             node_private_key_password)
                message = vh.decrypt_base64_bytes_with_aes_key_to_string(raw_message, aes_key)
                return message
            else:
                return self._client_socket.recv(buffer_size).decode('utf8')

        except OSError as se:
            if se.errno == errno.ECONNRESET:
                self.logger.info("Connection Reset Detected While Trying To Receive Message. Attempting Connection Reestablishment")

                # close socket
                try:
                    self._client_socket.shutdown(socket.SHUT_RDWR)
                except:
                    pass
                try:
                    self._client_socket.close()
                except:
                    pass

                reconnect_succeeded = self.execute_connect_to_host_procedure()
                if not reconnect_succeeded:
                    self.logger.fatal("Connection Reestablishment Failed. Not Bothering Again. Terminating Process")
                    return None
            else:
                self.logger.info("An OSError Was Thrown While Trying To Receive Message")
                self.logger.info(se)
                return None

    def execute_connect_to_host_procedure(self)->bool:

        if self._config["SSL"]["enabled"] == 'True':
            self.logger.info("SSL Sockets Enabled. Configuring SSL")

            global ssl
            if ssl is None:
                try:
                    import ssl
                except ImportError:
                    self.logger.exception("Failed to Import SSL Module!. Your system may be missing openssl or python" +
                                          "version does not support it. Disable SSL or install SSL dependencies" +
                                          "for python")
                    return False

            try:
                address_results = getaddrinfo(self._master_host, int(self._master_port))
                master_ip = address_results[0][4][0]

                client_socket = socket(AF_INET, SOCK_STREAM)
                client_socket.connect((master_ip, int(self._master_port)))

                ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
                ssl_context.load_verify_locations(self._config["SSL"]["master_cert"],
                                                  self._config["SSL"]["master_key"])

                ssl_client_socket = ssl_context.wrap_socket(client_socket, server_hostname=self._master_host)
                self._client_socket = ssl_client_socket

            except ssl.SSLEOFError:
                self.logger.exception("SSLEOFError Occurred. Connection Was Terminated Abruptly. Can't Use " +
                                      "Anything From Sockets")
                return False
            except ssl.CertificateError:
                self.logger.exception("Certificate Error Occurred. Client Certificate Validation Failed. Not " +
                                      "Accepting Connection. Note you MUST include the master certs " +
                                      "(self-signed or not) in the configuration of each node for SSL to work " +
                                      "correctly")
                # python 3.7 has additional output that can be done here
                return False
            except ssl.SSLError:
                self.logger.exception("Generic SSL Error Occurred. Aborting Connection Attempt")
                return False
            except (Exception, OSError) as e:
                self.logger.exception("Resolution Of Master Domain Or Connection Failed. Aborting Processing")
                self.failed_initializing = True
                return False

        else: # else this is not an SSL setup, so don't import anything and use our sockets as usual

            try:
                address_results = getaddrinfo(self._master_host, int(self._master_port))
                master_ip = address_results[0][4][0]

                client_socket = socket(AF_INET, SOCK_STREAM)
                client_socket.connect((master_ip, int(self._master_port)))

                self._client_socket = client_socket

            except (Exception, OSError) as e:
                self.logger.exception("Resolution Of Master Domain Or Connection Failed. Aborting Processing")
                self.failed_initializing = True
                return False


        try:

            self.logger.info("Connection Established With Master. Securing Connection With Keys")

            self._master_public_key = self._recv_message(2048)
            if self._master_public_key is None:
                self.logger.fatal("Failed To Receive Master Node Public Key. Terminating")
                # TODO: Pass Message to node process to shut service down

                action = dict()
                action['command'] = "SYS"
                action['from'] = "CLIENT"
                action['to'] = "NODE"
                action['params'] = "SHUTDOWN"
                self.child_pipe.send(action)

                exit()

            aes_key = vh.decrypt_base64_bytes_with_private_key_to_bytes(self._node_aes_key,
                                                                        self._node_private_key,
                                                                        self._private_key_password)

            encrypted_aes_key = vh.encrypt_bytes_with_public_key_to_base64_bytes(aes_key,
                                                                                 self._master_public_key)

            self._send_message(encrypted_aes_key.decode('utf-8'))

            self.logger.info("Key Received From Master")
            self.logger.info(self._master_public_key)

            self.logger.info("Connection Secured")

        except:
            self.logger.exception("Connection With Master Node Failed. Aborting Processing")
            self.failed_initializing = True
            return False

        return True

    def start(self):
        command_dict = None
        try:
            self.logger.info("Configuring Local Keys")

            # generate our RSA Private And Public Keys
            private_key = self._sql_manager.getKeyOfName("node-me.key.private")
            public_key = self._sql_manager.getKeyOfName("node-me.key.public")
            found_aes_key = self._sql_manager.getKeyOfName("node-me.key.aes")

            # FIXME: There is no proper handling IF one of the keys exists and the other doesn't!
            if private_key is None or public_key is None or found_aes_key is None:
                self.logger.info("Keys Have Not Been Generated Before On This Node. This May Take Some Time...")
                self._node_private_key = vh.generate_private_key(self._private_key_password)
                self._node_public_key = vh.generate_public_key(self._node_private_key, self._private_key_password)
                new_aes_key = vh.generate_aes_key(self._private_key_password)

                # our aes key is stored encrypted with our public key
                self._node_aes_key = vh.encrypt_bytes_with_public_key_to_base64_bytes(new_aes_key, self._node_public_key)

                private_key = Key()
                private_key.name = "node-me.key.private"
                private_key.key = self._node_private_key
                self._sql_manager.insertKey(private_key)

                public_key = Key()
                public_key.name = "node-me.key.public"
                public_key.key = self._node_public_key
                self._sql_manager.insertKey(public_key)

                key = Key()
                key.key = self._node_aes_key.decode('utf-8')  # note this key is encrypted with our public key and then base64 encoded
                key.name = "node-me.key.aes"
                self._sql_manager.insertKey(key)

            else:
                self._node_private_key = private_key.key
                self._node_public_key = public_key.key
                self._node_aes_key = found_aes_key.key.encode()

            self.logger.info("Local Key Generation Complete")
            self.logger.info("Initializing Socket To Master")

            connection_succeeded = self.execute_connect_to_host_procedure()
            if not connection_succeeded:
                self.logger.fatal("Failed To Connect To Master. Node Is Unable To Continue. Terminating")
                action = dict()
                action['command'] = "SYS"
                action['from'] = "CLIENT"
                action['to'] = "NODE"
                action['params'] = "SHUTDOWN"
                self.child_pipe.send(action)
                exit()


            while True:

                self.logger.info("Reading Command From Socket")
                command = self._recv_message(4096, decrypt_with_key_pass=(self._node_private_key,
                                                                          self._private_key_password,
                                                                          self._node_aes_key))

                if command is None:
                    self.logger.error("Failed To Receive Command. Disconnection From Master Likely Occurred. Can't "
                                      "Process Command")

                    action = dict()
                    action['command'] = "SYS"
                    action['from'] = "CLIENT"
                    action['to'] = "NODE"
                    action['params'] = "SHUTDOWN"
                    self.child_pipe.send(action)

                    exit()

                command_dict = json.loads(command)
                self.logger.info("COMMAND RECEIVED")
                self.logger.info(command)

                try:

                    if command_dict["command"] == "GET" and command_dict["params"] == "SCRIPTS":
                        self.logger.info("Fetch Node Scripts Request Detected. Executing")

                        response = taskrunner.fetch_node_scripts(self._sql_manager, command_dict, self.logger)

                        self.logger.info("Fetched Data. Now Serializing For Response")
                        serialized_data = json.dumps(response)
                        self._send_message(str(serialized_data), encrypt_with_key=(self._node_private_key,
                                                                                   self._private_key_password,
                                                                                   self._node_aes_key))
                        self.logger.info("Response Sent")

                    elif command_dict["command"] == "EXEC" and command_dict["params"] == "SCAN.SCRIPTS":
                        self.logger.info("Scan Scripts Request Detected. Executing")

                        sm.catalogue_local_scripts(self._sql_manager, self._script_dir, self.logger)
                        response = taskrunner.fetch_node_scripts(self._sql_manager, command_dict, self.logger)

                        self.logger.info("Fetched Data. Now Serializing For Response")
                        serialized_data = json.dumps(response)
                        self._send_message(str(serialized_data), encrypt_with_key=(self._node_private_key,
                                                                                   self._private_key_password,
                                                                                   self._node_aes_key))
                        self.logger.info("Response Sent")

                    elif command_dict["command"] == "GET" and command_dict["params"] == "PING":
                        self.logger.info("Get Ping Request Detected. Executing")

                        response = taskrunner.get_ping_info(command_dict, self._config)
                        self.logger.info("Fetched Data. Now Serializing For Response")
                        serialized_data = json.dumps(response)
                        self._send_message(str(serialized_data), encrypt_with_key=(self._node_private_key,
                                                                                   self._private_key_password,
                                                                                   self._node_aes_key))
                        self.logger.info("Response Sent")

                    elif command_dict["command"] == "CREATE" and command_dict["params"] == "DEPLOYMENT":
                        self.logger.info("Create Deployment Request Detected. Executing")

                        response = taskrunner.create_deployment(self._sql_manager, command_dict, self.logger)

                        self.logger.info("Fetched Data. Now Serializing For Response")
                        serialized_data = json.dumps(response)
                        self._send_message(str(serialized_data), encrypt_with_key=(self._node_private_key,
                                                                                   self._private_key_password,
                                                                                   self._node_aes_key))
                        self.logger.info("Response Sent")

                    elif command_dict["command"] == "GET" and command_dict["params"] == "DEPLOYMENTS":
                        self.logger.info("Fetch Node Deployments Request Detected. Executing")

                        response = taskrunner.fetch_node_deployments(self._sql_manager, command_dict, self.logger)

                        self.logger.info("Fetched Data. Now Serializing For response")
                        serialized_data = json.dumps(response)
                        self._send_message(str(serialized_data), encrypt_with_key=(self._node_private_key,
                                                                                   self._private_key_password,
                                                                                   self._node_aes_key))
                        self.logger.info("Response Sent")

                    elif command_dict["command"] == "EXEC" and command_dict["params"] == "DEPLOYMENTS.EXECUTE":
                        self.logger.info("Executing Deployment On Node Request Detected. Executing")

                        response = taskrunner.execute_deployment_on_node(self._sql_manager, command_dict, self.logger)

                        self.logger.info("Fetched Data. Now Serializing For response")
                        serialized_data = json.dumps(response)
                        self._send_message(str(serialized_data), encrypt_with_key=(self._node_private_key,
                                                                                   self._private_key_password,
                                                                                   self._node_aes_key))
                        self.logger.info("Response Sent")

                    elif command_dict["command"] == "EXEC" and command_dict["params"] == "SCRIPTS.EXECUTE":
                        self.logger.info("Executing Script On Node Request Detected. Executing")

                        response = taskrunner.execute_script_on_node(self._sql_manager, command_dict, self.logger)

                        serialized_data = json.dumps(response)
                        self._send_message(str(serialized_data), encrypt_with_key=(self._node_private_key,
                                                                               self._private_key_password,
                                                                               self._node_aes_key))

                    elif command_dict["command"] == "MIG":
                        self.logger.info("Script Migration Request Received. Importing Script")

                        response = taskrunner.migrate(self._root_dir, self._sql_manager, command_dict, self.logger)

                        self.logger.info("Fetched Data. Now Serializing For Response")
                        serialized_data = json.dumps(response)
                        self._send_message(str(serialized_data), encrypt_with_key=(self._node_private_key,
                                                                                   self._private_key_password,
                                                                                   self._node_aes_key))
                        self.logger.info("Response Sent")

                    elif command_dict["command"] == "SYS" and command_dict["params"] == "PING":
                        # response is basically just to send what we got back
                        self.logger.debug("System Ping Call Received. Were Still Alive. Replying")

                        temp = command_dict["to"]
                        command_dict["to"] = command_dict["from"]
                        command_dict["from"] = temp

                        serialized_data = json.dumps(command_dict)
                        self._send_message(str(serialized_data), encrypt_with_key=(self._node_private_key,
                                                                                   self._private_key_password,
                                                                                   self._node_aes_key))
                        self.logger.info("Response Sent")

                    elif command_dict["command"] == "SYS" and command_dict["params"] == "RESTART":
                        self.logger.info("Master Node Restart Request Received. Disconnecting and Starting "
                                         "Reconnect Loop")

                        # send back a clean exit
                        response = dict()
                        response["to"] = "MASTER"
                        response["from"] = command_dict["to"]
                        response["command"] = "SYS"
                        response["param"] = "CONN.CLOSE"
                        response["rawdata"] = command_dict["rawdata"]

                        serialized_data = json.dumps(response)
                        self._send_message(str(serialized_data), encrypt_with_key=(self._node_private_key,
                                                                                   self._private_key_password,
                                                                                   self._node_aes_key))
                        self.logger.info("Response Sent")

                        # disconnect from master. Sleep for 2 minutes, then start reconnecting
                        try:
                            self._client_socket.shutdown(socket.SHUT_RDWR)
                        except:
                            pass
                        try:
                            self._client_socket.close()
                        except:
                            pass

                        self.logger.info("Diconnect From Master Node Complete. Sleeping For 2 Minutes")
                        time.sleep(120)

                        self.logger.info("Sleep Period Completed. Starting Reconnection")
                        attempt_count = 0
                        while not self.execute_connect_to_host_procedure():
                            attempt_count += 1
                            self.logger.info("Reconnection Failed. Sleeping For 30 Seconds and Trying Again " +
                                             "(Attempts: " + str(attempt_count) + ")")
                            time.sleep(30)
                        self.logger.info("Reconnection Successful. SYS.RESTART Complete")

                    else:
                        self.logger.info("Received Command Has Not Been Configured A Handling. Cannot Process Command")

                        error_response = dict()
                        error_response['command'] = 'ERROR'
                        error_response['from'] = 'node_client'
                        error_response['to'] = command_dict['from']
                        error_response['params'] = "Command: " + command_dict['command'] + " From: " + command_dict['from'] + \
                                                  " To: " + command_dict['to']
                        error_response['rawdata'] = ("Received Command Has No Mapping On This Node. Cannot Process Command",
                                                     command_dict)

                        serialized_data = json.dumps(error_response)
                        self._send_message(str(serialized_data), encrypt_with_key=(self._node_private_key,
                                                                                   self._private_key_password,
                                                                                   self._node_aes_key))
                except Exception as e:
                    self.logger.exception("Unexpected Error Thrown While Processing a Request.")

                    if command_dict is not None:

                        error_response = dict()
                        error_response['command'] = 'ERROR'
                        error_response['from'] = 'node_client'
                        error_response['to'] = command_dict['from']
                        error_response['params'] = "Command: " + command_dict['command'] + " From: " + command_dict['from'] + \
                                                  " To: " + command_dict['to']
                        error_response['rawdata'] = "UnExpected Error Executing Request: " + str(e)

                        serialized_data = json.dumps(error_response)
                        self._send_message(str(serialized_data), encrypt_with_key=(self._node_private_key,
                                                                                   self._private_key_password,
                                                                                   self._node_aes_key))

        except Exception as e:
            self.logger.exception("Fatal Error Processing For Node Client")

            if command_dict is not None:

                error_response = dict()
                error_response['command'] = 'ERROR'
                error_response['from'] = 'node_client'
                error_response['to'] = command_dict['from']
                error_response['params'] = "Command: " + command_dict['command'] + " From: " + command_dict['from'] + \
                                          " To: " + command_dict['to']
                error_response['rawdata'] = "UnExpected Error: " + str(e) + " WARNING: Node Has Likely Terminated From " \
                                                                            "This Event Or Is In A Broken State. Restart " \
                                                                            "To Recover"

                serialized_data = json.dumps(error_response)
                self._send_message(str(serialized_data), encrypt_with_key=(self._node_private_key,
                                                                           self._private_key_password,
                                                                           self._node_aes_key))