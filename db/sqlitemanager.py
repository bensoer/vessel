import sqlite3
import uuid
from db.models.Key import Key

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
                        (id INTEGER PRIMARY KEY, guid TEXT, name TEXT, ip TEXT, key_guid TEXT)''')

        self._cursor.execute('''CREATE TABLE IF NOT EXISTS  scripts
                          (id INTEGER PRIMARY KEY, guid TEXT, file_name TEXT, script_engine TEXT)''')

        self._conn.commit()


    def insertNode(self, node):

        guid = node.guid
        if node.guid == None:
            guid = uuid.uuid4()

        name = node.name
        ip = node.ip
        key_guid = node.key_guid

        query = "INSERT INTO nodes (guid, name, ip, key_guid) VALUES ('{guid}', '{name}', '{ip}', '{key_guid}')"
        query = query.format(guid=str(guid), name=name, ip=ip, key_guid=str(key_guid))

        self._logger.info("Inserting Node Record")
        self._cursor.execute(query)

        node.id = self._cursor.lastrowid
        self._conn.commit()

        return node

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
