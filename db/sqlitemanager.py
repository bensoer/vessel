import sqlite3
import uuid

class SQLiteManager:

    _db_dir = None
    _db_path = None
    _cursor = None

    def __init__(self, config):
        self._db_dir = config["DATABASE"]["db_dir"]
        self._db_path = self._db_dir + "/vessel.db"
        self._conn = sqlite3.connect(self._db_path)

        # create all of our tables

        self._cursor = self._conn.cursor()

        self._cursor.execute('''CREATE TABLE IF NOT EXISTS nodes
                        (id INTEGER PRIMARY KEY, guid TEXT, name TEXT, ip TEXT, secure_key TEXT)''')

        self._cursor.execute('''CREATE TABLE IF NOT EXISTS  scripts
                          (id INTEGER PRIMARY KEY, guid TEXT, file_name TEXT, script_engine TEXT)''')

        self._conn.commit()


    def insertNode(self, node):

        guid = node.guid
        if node.guid == None:
            guid = uuid.uuid4()

        name = node.name
        ip = node.ip
        secure_key = node.secure_key

        self._cursor.execute("INSERT INTO nodes (guid, name, ip, secure_key) VALUES ('" + str(guid) + "', '" + name +
                             "', '" + ip + "', '" + secure_key + "')")

        node.id = self._cursor.lastrowid
        self._conn.commit()

        return node
