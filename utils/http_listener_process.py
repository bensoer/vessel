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
from flask import Flask, jsonify, abort, request
import platform
import uuid
from multiprocessing import Lock
import json


class HttpListenerProcess:

    _sql_manager = None
    child_pipe = None
    _port = None
    logger = None

    _master_private_key = None
    _master_public_key = None
    _private_key_password = None

    _root_dir = None

    __connections = dict()

    def __init__(self, initialization_tuple):
        child_pipe, config = initialization_tuple

        self.child_pipe = child_pipe
        self._pipe_lock = Lock()

        self._port = config["HTTPLISTENER"]["port"]
        self._bind_ip = config["HTTPLISTENER"]["bind_ip"]
        self._log_dir = config["HTTPLISTENER"]["log_dir"]
        self._root_dir = config["DEFAULT"]["root_dir"]
        self._vessel_version = config["META"]["version"]

        self._private_key_password = config["DEFAULT"]["private_key_password"]
        log_path = self._log_dir + "/master-http.log"

        self.logger = logging.getLogger("HttpListenerProcess")
        self.logger.setLevel(logging.DEBUG)
        max_file_size = config["LOGGING"]["max_file_size"]
        max_file_count = config["LOGGING"]["max_file_count"]
        handler = RotatingFileHandler(log_path, maxBytes=int(max_file_size), backupCount=int(max_file_count))
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)

        self.logger.info("HttpListenerProcess Initialized. Creating Connection To SQL DB")

        self._sql_manager = SQLiteManager(config, self.logger)

        self.logger.info("Connection Complete")

    def start(self):
        self.logger.info("Initializing And Defining Flask Server")
        app = Flask(__name__)

        def handle_internal_error(command):
            return jsonify(command), 500

        @app.errorhandler(400)
        def page_not_found(e):
            return jsonify(message=str(e)), 400

        @app.errorhandler(404)
        def page_not_found(e):
            return jsonify(message=str(e)), 404

        @app.errorhandler(501)
        def not_implemented(e):
            return jsonify(message=str(e)), 501

        @app.route('/api/ping', methods=['GET'])
        def GETHelloWorld():

            return jsonify({
                'vessel-version': self._vessel_version,
                'python-version': platform.python_version(),
                'python-compiler': platform.python_compiler()
            })

        @app.route("/api/script", methods=['GET'])
        def GETAllScripts():
            self.logger.info("Fetching All Scripts")

            all_scripts = self._sql_manager.getAllScripts()

            all_scripts_as_dictionaries = list()
            for script in all_scripts:
                dict_script = script.toDictionary()
                all_scripts_as_dictionaries.append(dict_script)

            return jsonify(all_scripts_as_dictionaries)

        @app.route("/api/script/<script_guid>", methods=['GET'])
        def GETScriptOfGuid(script_guid):
            self.logger.info("Fetching Script Of Guid: " + script_guid)
            uuid_script_guid = uuid.UUID(script_guid)

            all_scripts = self._sql_manager.getAllScripts()
            for script in all_scripts:
                if script.guid == uuid_script_guid:
                    return jsonify(script.toDictionary())

            return abort(404)

        @app.route("/api/node", methods=['GET'])
        def GETAllNodes():
            self.logger.info("Fetching All Nodes")

            all_nodes = self._sql_manager.getAllNodes()

            all_nodes_as_dictionaries = list()
            for node in all_nodes:
                dict_node = node.toDictionary()
                all_nodes_as_dictionaries.append(dict_node)

            return jsonify(all_nodes_as_dictionaries)

        @app.route("/api/node/<node_guid>", methods=['GET'])
        def GETNodeOfGuid(node_guid):
            self.logger.info("Fetching Node Of Guid: " + node_guid)
            uuid_node_guid = uuid.UUID(node_guid)

            all_nodes = self._sql_manager.getAllNodes()
            for node in all_nodes:
                if node.guid == uuid_node_guid:
                    return jsonify(node.toDictionary())

            return abort(404)

        @app.route("/api/node/<node_guid>/script", methods=['GET'])
        def GETAllScriptsOfGuid(node_guid):
            self.logger.info("Fetching Scripts On Node Of Guid: " + node_guid)

            self._pipe_lock.acquire()
            # now query to get the scripts
            action = dict()
            action['command'] = "GET"
            action['from'] = "HTTP"
            action['to'] = "NODE"
            action['params'] = "SCRIPTS"
            action['rawdata'] = node_guid

            self.child_pipe.send(action)

            answer = self.child_pipe.recv()
            self._pipe_lock.release()

            if answer['command'] == "ERROR":
                return handle_internal_error(answer)
            else:
                return jsonify(answer["rawdata"])

        @app.route("/api/node/<node_guid>/script/<script_guid>/execute", methods=['POST'])
        def POSTExecuteScriptOnNode(node_guid, script_guid):
            self.logger.info("Executing Script Of Guid: " + script_guid + " On Node Of Guid: " + node_guid)

            self._pipe_lock.acquire()

            action = dict()
            action['command'] = "EXEC"
            action['from'] = "HTTP"
            action['to'] = "NODE"
            action['params'] = "SCRIPTS.EXECUTE"
            action['rawdata'] = (node_guid, script_guid)

            self.child_pipe.send(action)

            answer = self.child_pipe.recv()
            self._pipe_lock.release()

            if answer['command'] == "ERROR":
                return handle_internal_error(answer)
            else:

                response = dict()
                response["script_guid"] = script_guid
                response["node_guid"] = node_guid
                response["node_execution_status"] = answer['param']
                response["stdout"] = answer['rawdata'][0]
                response["stderr"] = answer['rawdata'][1]
                response["return_code"] = answer['rawdata'][2]

                return jsonify(response)

        @app.route("/api/script/<script_guid>/migrate", methods=['POST'])
        def POSTMigrateScriptToNode(script_guid):
                node_guid = request.json["node_guid"]
                if node_guid is None:
                    abort(400)

                self.logger.info("Migrating Script Of Guid: " + script_guid + " To Node Of Guid: " + node_guid)

                all_scripts = self._sql_manager.getAllScripts()
                for script in all_scripts:
                    if script.guid == uuid.UUID(script_guid):

                        # found our script
                        action = dict()
                        action['command'] = "MIG"
                        action['from'] = "HTTP"
                        action['to'] = "NODE"
                        action['params'] = (node_guid, script.toDictionary())

                        # rag the raw file content and put into binary string
                        file_path = self._root_dir + "/scripts/" + script.file_name
                        fp = open(file_path, 'rb')
                        all_file_contents = fp.read()
                        fp.close()

                        action['rawdata'] = all_file_contents

                        self._pipe_lock.acquire()
                        self.child_pipe.send(action)

                        answer = self.child_pipe.recv()

                        if answer['command'] == "ERROR":
                            return handle_internal_error(answer)
                        else:
                            return jsonify(answer)

                abort(404)

        self.logger.info("Now Starting Flask Server")
        app.run(debug=True, use_reloader=False, port=int(self._port), host=self._bind_ip)
        self.logger.info("Flask Server Started. Call Complete")
