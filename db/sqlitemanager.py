import sqlite3
import uuid
from db.models.Key import Key
from db.models.Script import Script
from db.models.Node import Node
from db.models.Deployment import Deployment
from db.models.DeploymentScript import DeploymentScript
from db.models.Engine import Engine

class SQLiteManager:

    _db_dir = None
    _db_path = None
    _cursor = None
    _logger = None

    def __init__(self, config, logger):
        self._db_dir = config["DATABASE"]["db_dir"]
        self._db_path = self._db_dir + "/vessel.db"
        self._conn = sqlite3.connect(self._db_path)
        self._logger = logger

        # create all of our tables

        self._cursor = self._conn.cursor()

        self._cursor.execute('''CREATE TABLE IF NOT EXISTS keys
                        (id INTEGER PRIMARY KEY , guid TEXT, name TEXT, description TEXT, key TEXT)''')

        self._cursor.execute('''CREATE TABLE IF NOT EXISTS nodes
                        (id INTEGER PRIMARY KEY, guid TEXT, name TEXT, ip TEXT, port TEXT, key_guid TEXT, state TEXT)''')

        self._cursor.execute('''CREATE TABLE IF NOT EXISTS  scripts
                          (id INTEGER PRIMARY KEY, guid TEXT, node_guid TEXT, file_path TEXT, file_name TEXT, script_engine TEXT)''')

        self._cursor.execute('''CREATE TABLE IF NOT EXISTS deployments
                            (id INTEGER PRIMARY KEY, guid TEXT, name TEXT, description TEXT)''')

        self._cursor.execute('''CREATE TABLE IF NOT EXISTS deployment_scripts
                            (id INTEGER PRIMARY KEY, guid TEXT, deployment INTEGER, script INTEGER, priority INTEGER)''')

        self._cursor.execute('''CREATE TABLE IF NOT EXISTS engines
                            (id INTEGER PRIMARY KEY, guid TEXT, name TEXT, path TEXT)''')

        self._conn.commit()

    def closeEverything(self):
        try:
            self._cursor.close()
            self._conn.close()
        except:
            self._logger.exception("SQLiteManager - Exception Was Thrown While Shutting Down the SQLite Connection. " +
                                   "But Were Shutting Down - So Do We Care ?")

    def insertEngine(self, engine):

        guid = engine.guid
        if engine.guid == None:
            guid = uuid.uuid4()

        name = engine.name
        path = engine.path

        query = "INSERT INTO engines (guid, [name], path) VALUES ('{guid}', '{name}', '{path}')"
        query = query.format(guid=guid, name=name, path=path)

        self._logger.debug("SQLiteManager - Inserting Engine Record")
        self._cursor.execute(query)

        engine.id = self._cursor.lastrowid
        self._conn.commit()

        return engine

    def getAllEngines(self):
        query = "SELECT id, guid, name, path FROM engines"

        self._logger.debug("SQLiteManager - Getting All Engines")
        self._cursor.execute(query)

        all_engines = list()
        for engine in self._cursor.fetchall():
            engine_model = Engine()
            engine_model.id = engine[0]
            engine_model.guid = uuid.UUID(engine[1])
            engine_model.name = engine[2]
            engine_model.path = engine[3]

            all_engines.append(engine_model)

        return all_engines

    def getEngineOfGuid(self, engine_guid):
        self._logger.debug("SQLiteManager - Getting Engine Of Guid: " + str(engine_guid))

        all_engines = self.getAllEngines()
        for engine in all_engines:
            if engine.guid == uuid.UUID(str(engine_guid)):
                return engine
        return None

    def getEngineOfName(self, engine_name):
        self._logger.debug("SQLiteManager - Getting Engine Of Name: " + str(engine_name))

        all_engines = self.getAllEngines()
        for engine in all_engines:
            if engine.name == engine_name:
                return engine
        return None

    def deleteEngineOfGuid(self, engine_guid):

        query = "DELETE FROM engine WHERE guid = '" + str(engine_guid) + "'"
        self._cursor.execute(query)
        self._conn.commit()


    def insertNode(self, node):

        guid = node.guid
        if node.guid == None:
            guid = uuid.uuid4()

        name = node.name
        ip = node.ip
        key_guid = node.key_guid
        port = node.port
        state = node.state

        query = "INSERT INTO nodes (guid, name, ip, port, key_guid, state) VALUES ('{guid}', '{name}', '{ip}', '{port}', '{key_guid}', '{state}')"
        query = query.format(guid=str(guid), name=name, ip=ip, port=port, key_guid=str(key_guid), state=state)

        self._logger.debug("SQLiteManager - Inserting Node Record")
        self._cursor.execute(query)

        node.id = self._cursor.lastrowid
        self._conn.commit()

        return node

    def updateNode(self, node):

        name = node.name
        ip = node.ip
        key_guid = node.key_guid
        port = node.port
        state = node.state
        guid = node.guid

        query = "UPDATE nodes SET name='{name}', ip='{ip}', port='{port}', key_guid='{key_guid}', state='{state}' WHERE guid='{guid}'"
        query = query.format(guid=str(guid), name=name, ip=ip, port=port, key_guid=str(key_guid), state=state)

        self._logger.debug("SQLiteManager - Updating Node Record")
        self._cursor.execute(query)

        self._conn.commit()

        return self.getNodeOfGuid(guid)


    def getNodeOfGuid(self, node_guid):
        self._logger.debug("SQLiteManager - Getting Node Of Guid: " + str(node_guid))

        all_nodes = self.getAllNodes()
        for node in all_nodes:
            if node.guid == uuid.UUID(str(node_guid)):
                return node

        return None

    def getNodeOfIpAndPort(self, node_ip, node_port):
        self._logger.debug("SQLiteManager - Getting Node Of IP: " + node_ip + " And Port: " + str(node_port))

        all_nodes = self.getAllNodes()
        for node in all_nodes:
            if node.ip == node_ip and node.port == str(node_port):
                return node

        return None


    def deleteNodeOfGuid(self, node_guid):
        self._logger.debug("SQLiteManager - Deleting Node Of Guid: " + str(node_guid))

        query = "DELETE FROM nodes WHERE guid = '" + str(node_guid) + "'"
        self._cursor.execute(query)
        self._conn.commit()

    def deleteKeyOfGuid(self, key_guid):
        self._logger.debug("SQLiteManager - Deleting Key Of Guid: " + str(key_guid))

        query = "DELETE FROM keys WHERE guid = '" + str(key_guid) + "'"
        self._cursor.execute(query)
        self._conn.commit()

    def getAllNodes(self):
        query = "SELECT id, guid, name, ip, port, key_guid, state FROM nodes"

        self._logger.debug("SQLiteManager - Getting All Nodes")
        self._cursor.execute(query)

        all_nodes = list()
        for node in self._cursor.fetchall():
            node_model = Node()
            node_model.id = node[0]
            node_model.guid = uuid.UUID(node[1])
            node_model.name = node[2]
            node_model.ip = node[3]
            node_model.port = node[4]
            node_model.key_guid = uuid.UUID(node[5])
            node_model.state = node[6]
            all_nodes.append(node_model)

        return all_nodes

    def getKeyOfGuid(self, key_guid):

        self._logger.debug("SQLiteManager - Getting Key Of Guid: " + str(key_guid))
        query = "SELECT id, guid, name, description, key FROM keys WHERE guid = '" + str(key_guid) + "'"
        self._cursor.execute(query)
        key = self._cursor.fetchone()

        if key is None:
            return None

        secure_key = Key()
        secure_key.id = key[0]
        secure_key.guid = uuid.UUID(key[1])
        secure_key.name = key[2]
        secure_key.description = key[3]
        secure_key.key = key[4]

        return secure_key

    def getKeyOfName(self, name):

        query = "SELECT id, name, description, guid, key FROM keys WHERE name = '" + name + "'"

        self._logger.debug("SQLiteManager - Getting Key Of Name: " + name)
        self._cursor.execute(query)
        key = self._cursor.fetchone()

        if key is None:
            return None

        self._logger.debug(key)

        secure_key = Key()
        secure_key.key = key[4]
        secure_key.id = key[0]
        secure_key.name = key[1]
        secure_key.description = key[2]
        secure_key.guid = uuid.UUID(key[3])

        return secure_key

    def getKeyOfId(self, key_id):

        query = "SELECT id, name, description, guid, key FROM keys WHERE id = " + str(key_id) + ""

        self._logger.debug("SQLiteManager - Getting Key Of Id: " + str(key_id))
        self._cursor.execute(query)
        key = self._cursor.fetchone()

        if key is None:
            return None

        self._logger.debug(key)

        secure_key = Key()
        secure_key.key = key[4]
        secure_key.id = key[0]
        secure_key.name = key[1]
        secure_key.description = key[2]
        secure_key.guid = uuid.UUID(key[3])

        return secure_key


    def insertKey(self, key):

        guid = key.guid
        if key.guid == None:
            guid = uuid.uuid4()

        name = key.name
        description = key.description
        secure_key = key.key

        query = "INSERT INTO keys (guid, name, description, key) VALUES ('{guid}', '{name}', '{description}', '{key}')"
        query = query.format(guid=str(guid), name=name, description=description, key=secure_key)

        self._logger.debug("SQLiteManager - Inserting Key Record")
        self._cursor.execute(query)

        key_id = self._cursor.lastrowid
        self._conn.commit()

        return self.getKeyOfId(int(key_id))

    def getAllScripts(self):
        query = "SELECT id, guid, file_name, script_engine, node_guid, file_path FROM scripts"

        self._logger.debug("SQLiteManager - Getting All Scripts")
        self._cursor.execute(query)

        all_scripts = list()
        for script in self._cursor.fetchall():
            script_model = Script()
            script_model.id = script[0]
            script_model.guid = uuid.UUID(script[1])
            script_model.file_name = script[2]
            script_model.script_engine = script[3]
            script_model.node_guid = script[4]
            script_model.file_path = script[5]
            all_scripts.append(script_model)

        return all_scripts

    def deleteScriptOfId(self, script_id):
        query = "DELETE FROM scripts WHERE id = " + str(script_id)

        self._logger.debug("SQLiteManager - Deleting Script Of id: " + str(script_id))
        self._cursor.execute(query)
        self._conn.commit()

    def getScriptOfGuid(self, script_guid):
        query = "SELECT id, guid, file_name, script_engine, file_path FROM scripts WHERE guid = '" + str(script_guid) + "'"

        self._logger.debug("SQLiteManager - Getting Script Of Guid: " + str(script_guid))
        self._cursor.execute(query)
        script = self._cursor.fetchone()

        if script is None:
            return None

        script_model = Script()
        script_model.id = script[0]
        script_model.guid = uuid.UUID(script[1])
        script_model.file_name = script[2]
        script_model.script_engine = script[3]
        script_model.file_path = script[4]

        return script_model


    def getScriptOfId(self, script_id):

        query = "SELECT id, guid, file_name, script_engine, file_path FROM scripts WHERE id = " + str(script_id) + ""

        self._logger.debug("SQLiteManager - Getting Script Of ID: " + str(script_id))
        self._cursor.execute(query)
        script = self._cursor.fetchone()

        if script is None:
            return None

        self._logger.debug(script)

        script_model = Script()
        script_model.id = script[0]
        script_model.guid = uuid.UUID(script[1])
        script_model.file_name = script[2]
        script_model.script_engine = script[3]
        script_model.file_path = script[4]

        return script_model

    def deleteAllScripts(self):

        query = "DELETE FROM scripts"

        self._logger.debug("SQLiteManager - Deleting All Script Entries")
        self._cursor.execute(query)
        self._conn.commit()

    def insertScriptIfNotExists(self, script):
        guid = script.guid
        if script.guid == None:
            guid = uuid.uuid4()

        file_name = script.file_name
        script_engine = script.script_engine
        file_path = script.file_path

        query = "SELECT id, guid, file_name, script_engine, file_path FROM scripts WHERE file_name = '" + file_name + "'"
        self._cursor.execute(query)
        existing_script = self._cursor.fetchone()

        if existing_script is None:

            query = "INSERT INTO scripts (guid, file_name, script_engine, file_path) VALUES('{guid}', '{file_name}', '{script_engine}', '{file_path}')"
            query = query.format(guid=str(guid), file_name=file_name, script_engine=script_engine, file_path=file_path)
            self._cursor.execute(query)

            script_id = self._cursor.lastrowid
            self._conn.commit()

            script.id = script_id
            return script

        else:
            script.id = existing_script[0]
            script.guid = existing_script[1]
            script.file_name = existing_script[2]
            script.script_engine = existing_script[3]
            script.file_path = existing_script[4]

            return script



    def insertScript(self, script):

        guid = script.guid
        if script.guid == None:
            guid = uuid.uuid4()

        file_name = script.file_name
        script_engine = script.script_engine
        file_path = script.file_path

        query = "INSERT INTO scripts (guid, file_name, script_engine, file_path) VALUES ('{guid}', '{file_name}', '{script_engine}', '{file_path}')"
        query = query.format(guid=str(guid), file_name=file_name, script_engine=script_engine, file_path=file_path)

        self._logger.debug("SQLiteManager - Inserting Script")
        self._cursor.execute(query)

        script_id = self._cursor.lastrowid
        self._conn.commit()

        return self.getScriptOfId(int(script_id))

    def getDeploymentOfId(self, deployment_id):
        query = "SELECT id, guid, name, description FROM deployments WHERE id = " + str(deployment_id) + ""

        self._logger.debug("SQLiteManager - Getting Deployment Of ID: " + str(deployment_id))
        self._cursor.execute(query)
        deployment = self._cursor.fetchone()

        if deployment is None:
            return None

        deployment_model = Deployment()
        deployment_model.description = deployment[3]
        deployment_model.guid = uuid.UUID(deployment[1])
        deployment_model.name = deployment[2]
        deployment_model.id = deployment[0]

        return deployment_model

    def getDeploymentOfGuid(self, deployment_guid):
        query = "SELECT id, guid, name, description FROM deployments WHERE guid = '{deployment_guid}'"
        query = query.format(deployment_guid=deployment_guid)

        self._logger.debug("SQLiteManager - Getting Deployment Of Guid: " + str(deployment_guid))
        self._cursor.execute(query)
        deployment = self._cursor.fetchone()

        if deployment is None:
            return None

        deployment_model = Deployment()
        deployment_model.description = deployment[3]
        deployment_model.guid = uuid.UUID(deployment[1])
        deployment_model.name = deployment[2]
        deployment_model.id = deployment[0]

        return deployment_model

    def getAllDeployments(self):
        query = "SELECT id, guid, name, description FROM deployments"

        self._logger.debug("SQLiteManager - Getting All Deployments")
        self._cursor.execute(query)
        deployments = self._cursor.fetchall()

        deployment_models = list()
        for deployment in deployments:

            deployment_model = Deployment()
            deployment_model.id = deployment[0]
            deployment_model.guid = uuid.UUID(deployment[1])
            deployment_model.name = deployment[2]
            deployment_model.description = deployment[3]

            deployment_models.append(deployment)

        return deployment_models

    def insertDeployment(self, deployment):
        guid = deployment.guid
        if deployment.guid == None:
            guid == uuid.uuid4()

        name = deployment.name
        description = deployment.description

        query = "INSERT INTO deployments(guid, name, description VALUES('{guid}', '{name}', '{description}')"
        query = query.format(guid=str(guid), name=name, description=description)

        self._logger.debug("SQLiteManager - Inserting Deployment")
        self._cursor.execute(query)
        deployment_id = self._cursor.lastrowid
        self._conn.commit()

        return self.getDeploymentOfId(int(deployment_id))

    def getDeploymentScriptOfId(self, deployment_script_id):
        query = "SELECT id, guid, deployment, script FROM deployment_scripts WHERE id = " + str(deployment_script_id) + ""

        self._logger.debug("SQLiteManager - Getting Deployment Script Of ID: " + str(deployment_script_id))
        self._cursor.execute(query)
        deployment_script = self._cursor.fetchone()

        if deployment_script is None:
            return None

        deployment_script_model = DeploymentScript()
        deployment_script_model.id = deployment_script[0]
        deployment_script_model.guid = deployment_script[1]
        deployment_script_model.deployment = deployment_script[2]
        deployment_script_model.script = deployment_script[3]

        return deployment_script_model


    def insertDeploymentScript(self, deploymentScript):
        guid = deploymentScript.guid
        if deploymentScript.guid == None:
            guid = uuid.uuid4()

        deployment = deploymentScript.deployment
        script = deploymentScript.script
        priority = deploymentScript.priority

        query = "INSERT INTO deployment_scripts(guid, deploymnet, script, priority) VALUES({guid}, {deployment}, {script}, {priority})"
        query = query.format(guid=str(guid), deployment=deployment, script=script, priority=priority)

        self._logger.debug("SQLiteManager - Inserting Deployment Script")
        self._cursor.execute(query)
        deployment_script_id = self._cursor.lastrowid
        self._conn.commit()

        return self.getDeploymentScriptOfId(int(deployment_script_id))


    def getScriptsOfDeploymentGuid(self, deployment_guid):
        query = "SELECT s.id, s.guid, s.file_name, s.script_engine, s.file_path" \
                "FROM deployments d JOIN deployment_scripts ds ON d.id = ds.deployment JOIN scripts s ON s.id = ds.script" \
                "ORDER BY ds.priority DESC" \
                "WHERE d.guid = {deployment_guid}"

        query = query.format(deployment_guid=str(deployment_guid))
        self._logger.debug("Getting Scripts Of Deployment Guid: " + str(deployment_guid))
        self._cursor.execute(query)
        scripts = self._cursor.fetchall()

        script_models = list()
        for script in scripts:

            script_model = Script()
            script_model.id = script[0]
            script_model.guid = uuid.UUID(script[1])
            script_model.file_name = script[2]
            script_model.script_engine = script[3]
            script_model.file_path = script[4]

            script_models.append(script_model)

        return script_models
