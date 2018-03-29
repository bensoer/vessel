import sqlite3
import uuid
from db.models.Key import Key
from db.models.Script import Script
from db.models.Node import Node

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
                        (id INTEGER PRIMARY KEY, guid TEXT, name TEXT, ip TEXT, port TEXT, key_guid TEXT)''')

        self._cursor.execute('''CREATE TABLE IF NOT EXISTS  scripts
                          (id INTEGER PRIMARY KEY, guid TEXT, node_guid TEXT, file_name TEXT, script_engine TEXT)''')

        self._conn.commit()

    def closeEverything(self):
        try:
            self._cursor.close()
            self._conn.close()
        except:
            self._logger.exception("Exception Was Thrown While Shutting Down the SQLite Connection. But Were Shutting "
                                   "Down - So Do We Care ?")

    def insertNode(self, node):

        guid = node.guid
        if node.guid == None:
            guid = uuid.uuid4()

        name = node.name
        ip = node.ip
        key_guid = node.key_guid
        port = node.port

        query = "INSERT INTO nodes (guid, name, ip, port, key_guid) VALUES ('{guid}', '{name}', '{ip}', '{port}', '{key_guid}')"
        query = query.format(guid=str(guid), name=name, ip=ip, port=port, key_guid=str(key_guid))

        self._logger.info("Inserting Node Record")
        self._cursor.execute(query)

        node.id = self._cursor.lastrowid
        self._conn.commit()

        return node

    def getNodeOfGuid(self, node_guid):
        self._logger.info("Getting Node Of Guid: " + node_guid)

        all_nodes = self.getAllNodes()
        for node in all_nodes:
            if node.guid == uuid.UUID(node_guid):
                return node

        return None

    def getNodeOfIpAndPort(self, node_ip, node_port):
        self._logger.info("Getting Node Of IP: " + node_ip + " And Port: " + str(node_port))

        all_nodes = self.getAllNodes()
        for node in all_nodes:
            if node.ip == node_ip and node.port == str(node_port):
                return node

        return None


    def deleteNodeOfGuid(self, node_guid):
        self._logger.info("Deleting Node Of Guid: " + node_guid)

        query = "DELETE FROM nodes WHERE guid = '" + str(node_guid) + "'"
        self._cursor.execute(query)
        self._conn.commit()

    def deleteKeyOfGuid(self, key_guid):
        self._logger.info("Deleting Key Of Guid: " + key_guid)

        query = "DELETE FROM keys WHERE guid = '" + str(key_guid) + "'"
        self._cursor.execute(query)
        self._conn.commit()

    def getAllNodes(self):
        query = "SELECT id, guid, name, ip, port, key_guid FROM nodes"

        self._logger.info("Getting All Nodes")
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
            all_nodes.append(node_model)

        return all_nodes

    def getKeyOfName(self, name):

        query = "SELECT id, name, description, guid, key FROM keys WHERE name = '" + name + "'"

        self._logger.info("Getting Key Of Name: " + name)
        self._cursor.execute(query)
        key = self._cursor.fetchone()

        if key is None:
            return None

        self._logger.info(key)

        secure_key = Key()
        secure_key.key = key[4].encode()
        secure_key.id = key[0]
        secure_key.name = key[1]
        secure_key.description = key[2]
        secure_key.guid = uuid.UUID(key[3])

        return secure_key

    def getKeyOfId(self, key_id):

        query = "SELECT id, name, description, guid, key FROM keys WHERE id = " + str(key_id) + ""

        self._logger.info("Getting Key Of Id: " + str(key_id))
        self._cursor.execute(query)
        key = self._cursor.fetchone()

        if key is None:
            return None

        self._logger.info(key)

        secure_key = Key()
        secure_key.key = key[4].encode()
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

        self._logger.info("Inserting Key Record")
        self._cursor.execute(query)

        key_id = self._cursor.lastrowid
        self._conn.commit()

        return self.getKeyOfId(int(key_id))

    def getAllScripts(self):
        query = "SELECT id, guid, file_name, script_engine, node_guid FROM scripts"

        self._logger.info("Getting All Scripts")
        self._cursor.execute(query)

        all_scripts = list()
        for script in self._cursor.fetchall():
            script_model = Script()
            script_model.id = script[0]
            script_model.guid = uuid.UUID(script[1])
            script_model.file_name = script[2]
            script_model.script_engine = script[3]
            script_model.node_guid = script[4]
            all_scripts.append(script_model)

        return all_scripts

    def deleteScriptOfId(self, script_id):
        query = "DELETE FROM scripts WHERE id = " + str(script_id)

        self._logger.info("Deleting Script Of id: " + str(script_id))
        self._cursor.execute(query)
        self._conn.commit()

    def getScriptOfId(self, script_id):

        query = "SELECT id, guid, file_name, script_engine FROM scripts WHERE id = " + str(script_id) + ""

        self._logger.info("Getting Script Of ID: " + str(script_id))
        self._cursor.execute(query)
        script = self._cursor.fetchone()

        if script is None:
            return None

        self._logger.info(script)

        script_model = Script()
        script_model.id = script[0]
        script_model.guid = uuid.UUID(script[1])
        script_model.file_name = script[2]
        script_model.script_engine = script[3]

        return script_model

    def deleteAllScripts(self):

        query = "DELETE FROM scripts"

        self._logger.info("Deleting All Script Entries")
        self._cursor.execute(query)
        self._conn.commit()


    def insertScript(self, script):

        guid = script.guid
        if script.guid == None:
            guid = uuid.uuid4()

        file_name = script.file_name
        script_engine = script.script_engine

        query = "INSERT INTO scripts (guid, file_name, script_engine) VALUES ('{guid}', '{file_name}', '{script_engine}')"
        query = query.format(guid=str(guid), file_name=file_name, script_engine=script_engine)

        self._logger.info("Inserting Script")
        self._cursor.execute(query)

        script_id = self._cursor.lastrowid
        self._conn.commit()

        return self.getScriptOfId(int(script_id))
