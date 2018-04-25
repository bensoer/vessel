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
import os
import base64

class HttpListenerProcess:

    #_sql_manager = None
    _config = None
    child_pipe = None
    _port = None
    logger = None

    _master_private_key = None
    _master_public_key = None
    _private_key_password = None

    _root_dir = None

    __connections = dict()

    _use_ssl = False

    def __init__(self, initialization_tuple):
        child_pipe, config = initialization_tuple

        self.child_pipe = child_pipe
        self._pipe_lock = Lock()

        self._config = config
        self._port = config["HTTPLISTENER"]["port"]
        self._bind_ip = config["HTTPLISTENER"]["bind_ip"]
        self._log_dir = config["HTTPLISTENER"]["log_dir"]
        self._root_dir = config["DEFAULT"]["root_dir"]
        #self._vessel_version = config["META"]["version"]

        if config["HTTPLISTENER"].get("ssl", "False") == "False":
            self._use_ssl = False
        else:
            self._use_ssl = True

        self._cert_path = config["DEFAULT"].get("cert_path", None)
        self._key_path = config["DEFAULT"].get("key_path", None)

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

        #self._sql_manager = SQLiteManager(config, self.logger)

        self.logger.info("Connection Complete")

    def start(self):
        self.logger.info("Initializing And Defining Flask Server")
        app = Flask(__name__)

        def handle_internal_error(command):
            return jsonify(command), 500

        @app.errorhandler(400)
        def bad_request(e):

            error = dict()
            error["message"] = str(e)
            error["details"] = e.description

            return jsonify(error), 400

        @app.errorhandler(405)
        def method_not_allowed(e):
            return jsonify(message=str(e)), 405

        @app.errorhandler(404)
        def page_not_found(e):
            return jsonify(message=str(e)), 404

        @app.errorhandler(501)
        def not_implemented(e):
            return jsonify(message=str(e)), 501

        @app.route('/api/ping', methods=['GET'])
        def GETPing():
            self.logger.info("Pinging Self")

            self._pipe_lock.acquire()
            action = dict()
            action['command'] = "GET"
            action['from'] = "HTTP"
            action['to'] = "MASTER"
            action['params'] = "PING"

            self.child_pipe.send(action)

            answer = self.child_pipe.recv()
            self._pipe_lock.release()

            if answer['command'] == "ERROR":
                return handle_internal_error(answer)
            else:
                return jsonify(answer['rawdata'])

        @app.route('/api/node/<node_guid>/ping', methods=['GET'])
        def GETPingOfNode(node_guid):
            self.logger.info("Pinging Node Of Guid: " + node_guid)

            try:
                uuid.UUID(node_guid, version=4)
            except:
                abort(400, "The Passed In Node Guid Is Invalid")

            self._pipe_lock.acquire()
            action = dict()
            action['command'] = "GET"
            action['from'] = "HTTP"
            action['to'] = "NODE"
            action['params'] = "PING"
            action['rawdata'] = node_guid

            self.child_pipe.send(action)

            answer = self.child_pipe.recv()
            self._pipe_lock.release()

            if answer['command'] == "ERROR":
                return handle_internal_error(answer)
            else:
                return jsonify(answer['rawdata'])


        @app.route("/api/script", methods=['GET'])
        def GETAllScripts():
            self.logger.info("Fetching All Scripts")

            sql_manager = SQLiteManager(self._config, self.logger)
            all_scripts = sql_manager.getAllScripts()

            all_scripts_as_dictionaries = list()
            for script in all_scripts:
                dict_script = script.toDictionary()
                dict_script.pop("file_path", None)
                all_scripts_as_dictionaries.append(dict_script)

            sql_manager.closeEverything()
            return jsonify(all_scripts_as_dictionaries)

        @app.route("/api/script/scan", methods=['POST'])
        def POSTScanForScripts():
            self.logger.info("Scanning Local System For Scripts")

            self._pipe_lock.acquire()
            # now query to get the scripts
            action = dict()
            action['command'] = "EXEC"
            action['from'] = "HTTP"
            action['to'] = "MASTER"
            action['params'] = "SCAN.SCRIPTS"
            action['rawdata'] = ""

            self.child_pipe.send(action)

            answer = self.child_pipe.recv()
            self._pipe_lock.release()

            if answer['command'] == "ERROR":
                return handle_internal_error(answer)
            else:
                return GETAllScripts()

        @app.route("/api/node/<node_guid>/script/scan", methods=['POST'])
        def POSTScanForScriptsOnNode(node_guid):
            self.logger.info("Scanning Node Of Guid " + node_guid + " For Scripts")

            try:
                uuid.UUID(node_guid, version=4)
            except:
                abort(400, "The Passed In Node Guid Is Invalid")

            self._pipe_lock.acquire()
            # now query to get the scripts
            action = dict()
            action['command'] = "EXEC"
            action['from'] = "HTTP"
            action['to'] = "NODE"
            action['params'] = "SCAN.SCRIPTS"
            action['rawdata'] = (node_guid,)

            self.child_pipe.send(action)

            answer = self.child_pipe.recv()
            self._pipe_lock.release()

            if answer['command'] == "ERROR":
                return handle_internal_error(answer)
            else:
                return GETAllScriptsOfNodeGuid(node_guid)

        @app.route("/api/script/<script_guid>", methods=['GET'])
        def GETScriptOfGuid(script_guid):
            self.logger.info("Fetching Script Of Guid: " + script_guid)

            try:
                uuid.UUID(script_guid, version=4)
            except:
                abort(400, "The Passed In Script Guid Is Invalid")

            uuid_script_guid = uuid.UUID(script_guid)

            sql_manager = SQLiteManager(self._config, self.logger)
            all_scripts = sql_manager.getAllScripts()
            for script in all_scripts:
                if script.guid == uuid_script_guid:
                    script_dict = script.toDictionary()
                    script_dict.pop("file_path", None)

                    sql_manager.closeEverything()
                    return jsonify(script_dict)

            sql_manager.closeEverything()
            return abort(404)

        @app.route("/api/node", methods=['GET'])
        def GETAllNodes():
            self.logger.info("Fetching All Nodes")

            sql_manager = SQLiteManager(self._config, self.logger)
            all_nodes = sql_manager.getAllNodes()

            all_nodes_as_dictionaries = list()
            for node in all_nodes:
                dict_node = node.toDictionary()
                dict_node.pop("ip", None)
                all_nodes_as_dictionaries.append(dict_node)

            sql_manager.closeEverything()
            return jsonify(all_nodes_as_dictionaries)

        @app.route("/api/node/<node_guid>", methods=['GET'])
        def GETNodeOfGuid(node_guid):
            self.logger.info("Fetching Node Of Guid: " + node_guid)

            try:
                uuid.UUID(node_guid, version=4)
            except:
                abort(400, "The Passed In Node Guid Is Invalid")


            uuid_node_guid = uuid.UUID(node_guid)

            sql_manager = SQLiteManager(self._config, self.logger)
            all_nodes = sql_manager.getAllNodes()
            for node in all_nodes:
                if node.guid == uuid_node_guid:
                    node_dict = node.toDictionary()
                    node_dict.pop("ip", None)

                    sql_manager.closeEverything()
                    return jsonify(node_dict)

            sql_manager.closeEverything()
            return abort(404)

        @app.route("/api/node/<node_guid>/script", methods=['GET'])
        def GETAllScriptsOfNodeGuid(node_guid):
            self.logger.info("Fetching Scripts On Node Of Guid: " + node_guid)

            try:
                uuid.UUID(node_guid, version=4)
            except:
                abort(400, "The Passed In Node Guid Is Invalid")

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
            all_scripts = answer["rawdata"]
            self._pipe_lock.release()

            for script in all_scripts:
                script.pop("file_path", None)

            if answer['command'] == "ERROR":
                return handle_internal_error(answer)
            else:
                return jsonify(all_scripts)

        @app.route("/api/node/<node_guid>/script/<script_guid>/execute", methods=['POST'])
        def POSTExecuteScriptOnNode(node_guid, script_guid):
            self.logger.info("Executing Script Of Guid: " + script_guid + " On Node Of Guid: " + node_guid)

            try:
                uuid.UUID(node_guid, version=4)
            except:
                abort(400, "The Passed In Node Guid Is Invalid")

            try:
                uuid.UUID(script_guid, version=4)
            except:
                abort(400, "The Passed In Script Guid Is Invalid")

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
                response["node_execution_status"] = answer['params']
                response["results"] = answer["rawdata"]

                if answer["params"] == "FAILED.NOTFOUND":
                    return jsonify(response), 404

                return jsonify(response)

        @app.route("/api/script/<script_guid>/execute", methods=['POST'])
        def POSTExecuteScriptLocaly(script_guid):
            self.logger.info("Executing Script Of Guid: " + script_guid + " Locally")

            try:
                uuid.UUID(script_guid, version=4)
            except:
                abort(400, "The Passed In Script Guid Is Invalid")

            self._pipe_lock.acquire()

            action = dict()
            action['command'] = "EXEC"
            action['from'] = "HTTP"
            action['to'] = "MASTER"
            action['params'] = "SCRIPTS.EXECUTE"
            action['rawdata'] = (None, script_guid)

            self.child_pipe.send(action)

            answer = self.child_pipe.recv()
            self._pipe_lock.release()

            if answer['command'] == "ERROR":
                return handle_internal_error(answer)
            else:
                response = dict()
                response["script_guid"] = script_guid
                response["node_execution_status"] = answer['params']
                response["results"] = answer['rawdata']

                if answer['params'] == "FAILED.NOTFOUND":
                    return jsonify(response), 404

                return jsonify(response)

        @app.route("/api/script/<script_guid>/migrate", methods=['POST'])
        def POSTMigrateScriptToNode(script_guid):
                node_guid = request.json["node_guid"]

                if node_guid is None:
                    abort(400, "A Node Guid Is Required For Migration")

                try:
                    uuid.UUID(script_guid, version=4)
                except:
                    abort(400, "The Passed In Script Guid Is Invalid")

                try:
                    uuid.UUID(node_guid, version=4)
                except:
                    abort(400, "The Passed In Node Guid Is Invalid")

                self.logger.info("Migrating Script Of Guid: " + script_guid + " To Node Of Guid: " + node_guid)

                sql_manager = SQLiteManager(self._config, self.logger)
                all_scripts = sql_manager.getAllScripts()
                for script in all_scripts:
                    if script.guid == uuid.UUID(script_guid):

                        # found our script
                        action = dict()
                        action['command'] = "MIG"
                        action['from'] = "HTTP"
                        action['to'] = "NODE"
                        action['params'] = (str(node_guid), script.toDictionary())

                        # rag the raw file content and put into binary string
                        file_path = script.file_path + os.sep + script.file_name
                        fp = open(file_path, 'rb')
                        all_file_contents = fp.read()
                        fp.close()

                        action['rawdata'] = base64.b64encode(all_file_contents).decode('utf-8')

                        self._pipe_lock.acquire()
                        self.child_pipe.send(action)

                        answer = self.child_pipe.recv()
                        self._pipe_lock.release()

                        sql_manager.closeEverything()
                        if answer['command'] == "ERROR":
                            return handle_internal_error(answer)
                        else:

                            response = dict()
                            response["migrationStatus"] = answer["params"]
                            response["fileName"] = answer['rawdata']["file_name"]
                            response["destinationFilePath"] = answer['rawdata']["file_path"]
                            response["scriptGuid"] = answer['rawdata']["guid"]

                            return jsonify(response)

                sql_manager.closeEverything()
                abort(404)

        @app.route("/api/node/<node_guid>/deployment", methods=['GET'])
        def GETAllDeploymentsOfNode(node_guid):
            self.logger.info("Fetching Deployments On Node Of Guid: " + node_guid)

            try:
                uuid.UUID(node_guid, version=4)
            except:
                abort(400, "The Passed In Node Guid Is Invalid")

            self._pipe_lock.acquire()
            # now query to get the scripts
            action = dict()
            action['command'] = "GET"
            action['from'] = "HTTP"
            action['to'] = "NODE"
            action['params'] = "DEPLOYMENTS"
            action['rawdata'] = node_guid

            self.child_pipe.send(action)

            answer = self.child_pipe.recv()
            self._pipe_lock.release()

            if answer['command'] == "ERROR":
                return handle_internal_error(answer)
            else:
                return jsonify(answer["rawdata"])

        @app.route("/api/node/<node_guid>/deployment", methods=['POST'])
        def POSTCreateDeploymentOfNode(node_guid):
            deployment_name = request.json.get("deploymentName", None)
            deployment_description = request.json.get("description", None)
            deployment_script_guids = request.json.get("scriptGuids", None)

            if deployment_name is None or deployment_description is None or deployment_script_guids is None:
                abort(400, "Invalid Body Content")

            for deployment_script_guid in deployment_script_guids:
                if "priority" not in deployment_script_guid or "scriptGuid" not in deployment_script_guid:
                    abort(400, "Invalid Body Content")

            try:
                uuid.UUID(node_guid, version=4)
            except:
                abort(400, "The Passed In Node Guid Is Invalid")

            self._pipe_lock.acquire()
            action = dict()
            action['command'] = "CREATE"
            action['from'] = "HTTP"
            action['to'] = "NODE"
            action['params'] = "DEPLOYMENT"
            action['rawdata'] = (node_guid, deployment_name, deployment_description, deployment_script_guids)

            self.child_pipe.send(action)
            answer = self.child_pipe.recv()
            self._pipe_lock.release()

            if answer['command'] == "ERROR":
                return handle_internal_error(answer)
            elif answer['params'] == "SUCCESS":
                deployment = answer['rawdata'][0]
                scripts = answer['rawdata'][1]

                response = dict()
                response["deploymentName"] = deployment.name
                response["description"] = deployment.description

                script_list = list()
                for script in scripts:
                    script_dict = dict()
                    script_dict["priority"] = script.priority
                    script_dict["scriptGuid"] = script.guid

                    script_list.append(script_dict)

                response["deploymentScriptGuids"] = script_list

                return jsonify(response)

            elif answer['params'] == "FAILED":
                # currently this only happens if the script doesn't exist on the node - so 404
                return jsonify({'message': answer['rawdata']}), 404
            else:
                return jsonify(answer["rawdata"])

        @app.route("/api/deployment/<deployment_guid>/node/<node_guid>/execute", methods=['POST'])
        def POSTExecuteDeploymentOfNode(node_guid, deployment_guid):
            self.logger.info("Executing Deployment Of Guid: " + deployment_guid + " On Node Of Guid: " + node_guid)

            try:
                uuid.UUID(node_guid, version=4)
            except:
                abort(400, "The Passed In Node Guid Is Invalid")

            try:
                uuid.UUID(deployment_guid, version=4)
            except:
                abort(400, "The Passed In Deployment Guid Is Invalid")

            self._pipe_lock.acquire()

            action = dict()
            action['command'] = "EXEC"
            action['from'] = "HTTP"
            action['to'] = "NODE"
            action['params'] = "DEPLOYMENTS.EXECUTE"
            action['rawdata'] = (node_guid, deployment_guid)

            self.child_pipe.send(action)

            answer = self.child_pipe.recv()
            self._pipe_lock.release()

            if answer['command'] == "ERROR":
                return handle_internal_error(answer)
            else:

                response = dict()
                response["deployment_guid"] = deployment_guid
                response["node_guid"] = node_guid
                response["node_execution_status"] = answer['params']
                response["results"] = answer['rawdata']

                if answer['params'] == "FAILED.NOTFOUND":
                    return jsonify(response), 404

                return jsonify(response)


        self.logger.info("Now Starting Flask Server")

        if self._use_ssl:
            self.logger.info("Use SSL Configuration Detected. Checking If Certificates Were Included")
            if self._cert_path is not None and self._key_path is not None:
                self.logger.info("Certificates Were Included. Starting Server With Them")
                app.run(self._bind_ip, debug=False, port=int(self._port), threaded=True,
                        ssl_context=(self._cert_path, self._key_path))
            else:
                self.logger.info("Certificates Were Not Included. Generating Own")
                app.run(self._bind_ip, debug=False, port=int(self._port), threaded=True,
                        ssl_context='adhoc')
        else:
            self.logger.info("No SSL Supplied. Building HTTP Server")
            app.run(self._bind_ip, debug=False, port=int(self._port), threaded=True)

        self.logger.info("Flask Server Started. Call Complete")
