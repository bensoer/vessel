from socket import *
import select
import errno
from db.models.Node import Node
import logging
from logging.handlers import RotatingFileHandler
from db.sqlitemanager import SQLiteManager
import threading
import utils.vesselhelper as vh
import utils.script_manager as sm
from db.models.Key import Key
import json
from db.models.Script import Script
import uuid
import subprocess
from subprocess import CalledProcessError
import utils.taskrunner as taskrunner

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
        child_pipe, config = initialization_tuple

        self.child_pipe = child_pipe
        self._config = config

        self._master_host = config["DEFAULT"]["master_domain"]
        self._master_port = config["DEFAULT"]["master_port"]
        self._log_dir = config["LOGGING"]["log_dir"]
        self._root_dir = config["DEFAULT"]["root_dir"]
        self._node_name = config["DEFAULT"].get("name", "node")

        self._script_dir = config["DEFAULT"].get("scripts_dir", self._root_dir + "/scripts")

        self._private_key_password = config["DEFAULT"]["private_key_password"]
        log_path = self._log_dir + "/node-client.log"

        self.logger = logging.getLogger("NodeClientProcess")
        self.logger.setLevel(logging.DEBUG)
        max_file_size = config["LOGGING"]["max_file_size"]
        max_file_count = config["LOGGING"]["max_file_count"]
        handler = RotatingFileHandler(log_path, maxBytes=int(max_file_size), backupCount=int(max_file_count))
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)

        self.logger.info("NodeListenerProcess Inialized. Creating Connection To SQL DB")

        self._sql_manager = SQLiteManager(config, self.logger)

        self.logger.info("Connection Complete")

    def _send_message(self, message:str, encrypt_with_key=None):
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
                message = '{' + message + "}"
                return self._client_socket.send(message.encode())
        except error as se:
            if se.errno == errno.ECONNRESET:
                self.logger.info(
                    "Connection Reset Detected While Trying To Receive Message. Attempting Connection Reestablishment")

                # close socket
                try:
                    self._client_socket.shutdown(socket.SHUT_RDWR)
                except:
                    pass
                try:
                    self._client_socket.close()
                except:
                    pass

            # connect again to master
            self._client_socket = socket(AF_INET, SOCK_STREAM)
            self._client_socket.connect((self._master_host, int(self._master_port)))

            try:

                # exchange keys
                self._master_public_key = self._recv_message(2048)

                node_private_key, node_private_key_password, node_aes_key = encrypt_with_key
                aes_key = vh.decrypt_base64_bytes_with_private_key_to_bytes(node_aes_key,
                                                                             node_private_key,
                                                                             node_private_key_password)

                encrypted_aes_key = vh.encrypt_bytes_with_public_key_to_base64_bytes(aes_key,
                                                                                      self._master_public_key)
                self._client_socket.send(encrypted_aes_key)

                # return _recv_message again
                return self._send_message(message, encrypt_with_key=encrypt_with_key)
            except:
                # if connection fails here - then host prob is down. so stop trying
                self.logger.fatal("Connection Reestablishment Failed. Not Bothering Again. Terminating Process")
                exit(1)
                return None

    def _recv_message(self, buffer_size, decrypt_with_key_pass=None)->str:
        try:

            raw_message: bytes = b''
            valid_message_received = False

            while not valid_message_received:
                base64_encrypted_bytes = self._client_socket.recv(buffer_size)
                raw_message += base64_encrypted_bytes

                if len(raw_message) > 0:
                    if raw_message[0] == '{' and raw_message[len(raw_message) - 1] == '}':
                        valid_message_received = True
                        raw_message = raw_message[1:len(raw_message)-1]

            if decrypt_with_key_pass is not None:
                node_private_key, node_private_key_password, node_aes_key = decrypt_with_key_pass
                aes_key = vh.decrypt_base64_bytes_with_private_key_to_bytes(node_aes_key,
                                                                             node_private_key,
                                                                             node_private_key_password)
                message = vh.decrypt_base64_bytes_with_aes_key_to_string(raw_message, aes_key)
                return message
            else:
                message = raw_message.decode('utf8')
                return message

        except error as se:
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

            # connect again to master
            self._client_socket = socket(AF_INET, SOCK_STREAM)
            self._client_socket.connect((self._master_host, int(self._master_port)))

            try:

                # exchange keys
                self._master_public_key = self._recv_message(2048)

                node_private_key, node_private_key_password, node_aes_key = decrypt_with_key_pass
                aes_key = vh.decrypt_base64_bytes_with_private_key_to_bytes(node_aes_key,
                                                                             node_private_key,
                                                                             node_private_key_password)

                encrypted_aes_key = vh.encrypt_bytes_with_public_key_to_base64_bytes(aes_key,
                                                                                      self._master_public_key)
                self._client_socket.send(encrypted_aes_key)

                # return _recv_message again
                return self._recv_message(buffer_size, decrypt_with_key_pass=decrypt_with_key_pass)
            except:
                # if connection fails here - then host prob is down. so stop trying
                self.logger.fatal("Connection Reestablishment Failed. Not Bothering Again. Terminating Process")
                exit(1)
                return None

    def start(self):
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

            try:
                address_results = getaddrinfo(self._master_host, int(self._master_port))
                self._master_host = address_results[0][4][0]

                self._client_socket = socket(AF_INET, SOCK_STREAM)
                self._client_socket.connect((self._master_host, int(self._master_port)))
            except:
                self.logger.exception("Resolution Of Master Domain Or Connection Failed. Aborting Processing")
                self.failed_initializing = True
                return

            self.logger.info("Connection Established With Master. Securing Connection With Keys")

            self._master_public_key = self._recv_message(2048)

            aes_key = vh.decrypt_base64_bytes_with_private_key_to_bytes(self._node_aes_key,
                                                               self._node_private_key,
                                                               self._private_key_password)

            encrypted_aes_key = vh.encrypt_bytes_with_public_key_to_base64_bytes(aes_key,
                                                                                 self._master_public_key)

            self._send_message(encrypted_aes_key.decode('utf-8'))


            self.logger.info("Key Received From Master")
            self.logger.info(self._master_public_key)

            self.logger.info("Connection Secured")

            while True:

                self.logger.info("Reading Command From Socket")
                command = self._recv_message(4096, decrypt_with_key_pass=(self._node_private_key,
                                                                          self._private_key_password,
                                                                          self._node_aes_key))
                self.logger.info("COMMAND RECEIVED")
                self.logger.info(command)

                command_dict = json.loads(command)

                self.logger.info("COMMAND RECEIVED 2")
                self.logger.info(command_dict)

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

                    else:
                        self.logger.info("Received Command Has Not Been Configured A Handling. Cannot Process Command")

                        error_response = dict()
                        error_response['command'] = 'ERROR'
                        error_response['from'] = 'node_client'
                        error_response['to'] = command_dict['from']
                        error_response['params'] = "Command: " + command_dict['command'] + " From: " + command_dict['from'] + \
                                                  " To: " + command_dict['to']
                        error_response['rawdata'] = "Received Command Has No Mapping On This Node. Cannot Process Command"

                        serialized_data = json.dumps(error_response)
                        self._send_message(str(serialized_data), encrypt_with_key=(self._node_private_key,
                                                                                   self._private_key_password,
                                                                                   self._node_aes_key))
                except Exception as e:
                    self.logger.exception("Unexpected Error Thrown While Processing a Request.")

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