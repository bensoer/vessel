import unittest
import configparser
import os
import inspect
import logging
from vessel.db.sqlitemanager import SQLiteManager
from db.models import Deployment
from vessel.db.models import DeploymentScript
from vessel.db.models import Engine
from vessel.db.models import Key
from vessel.db.models import Node
from vessel.db.models import Script
import random
import string
import test.utils.testutils as testutils
import uuid

class SqliteManagerTests(unittest.TestCase):

    _config = configparser.ConfigParser()
    _sqlite_manager = None

    @classmethod
    def setUpClass(cls):

        cls._config.read(os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe()))) + os.sep + ".."
                         + os.sep + "vessel" + os.sep + 'conf' + os.sep + 'service.ini')
        cls.logger = logging.getLogger("SqliteManagerTests")
        cls._sqlite_manager = SQLiteManager(cls._config, cls.logger)


    @classmethod
    def tearDownClass(cls):
        cls._sqlite_manager.closeEverything()

    def test_insertKey(self):

        key = Key()
        key.name = testutils.generate_random_string(10)
        key.description = testutils.generate_random_string(10)

        inserted_key = self._sqlite_manager.insertKey(key)

        self.assertIsNotNone(inserted_key)
        self.assertIsInstance(inserted_key, Key)
        self.assertIsNotNone(inserted_key.id)
        self.assertIsNotNone(inserted_key.guid)
        self.assertIsNotNone(inserted_key.name)
        self.assertEqual(inserted_key.name, key.name)
        self.assertIsNotNone(inserted_key.description)
        self.assertEqual(inserted_key.description, key.description)
        self.assertIsNotNone(inserted_key.key)

    def test_getKeyOfGuid(self):

        key = Key()
        key.name = testutils.generate_random_string(10)
        key.description = testutils.generate_random_string(10)

        inserted_key = self._sqlite_manager.insertKey(key)

        fetched_key = self._sqlite_manager.getKeyOfGuid(inserted_key.guid)

        self.assertIsNotNone(fetched_key)
        self.assertIsInstance(fetched_key, Key)
        self.assertIsNotNone(fetched_key.id)
        self.assertIsNotNone(fetched_key.guid)
        self.assertIsNotNone(fetched_key.name)
        self.assertIsNotNone(fetched_key.description)
        self.assertIsNotNone(fetched_key.key)

        self.assertEqual(inserted_key.name, fetched_key.name)
        self.assertEqual(inserted_key.description, fetched_key.description)

    def test_getKeyOfId(self):

        key = Key()
        key.name = testutils.generate_random_string(10)
        key.description = testutils.generate_random_string(10)

        inserted_key = self._sqlite_manager.insertKey(key)

        fetched_key = self._sqlite_manager.getKeyOfId(inserted_key.id)

        self.assertIsNotNone(fetched_key)
        self.assertIsInstance(fetched_key, Key)
        self.assertIsNotNone(fetched_key.id)
        self.assertIsNotNone(fetched_key.guid)
        self.assertIsNotNone(fetched_key.name)
        self.assertIsNotNone(fetched_key.description)
        self.assertIsNotNone(fetched_key.key)

        self.assertEqual(inserted_key.name, fetched_key.name)
        self.assertEqual(inserted_key.description, fetched_key.description)

    def test_getKeyOfName(self):

        key = Key()
        key.name = testutils.generate_random_string(10)
        key.description = testutils.generate_random_string(10)

        inserted_key = self._sqlite_manager.insertKey(key)

        fetched_key = self._sqlite_manager.getKeyOfName(inserted_key.name)

        self.assertIsNotNone(fetched_key)
        self.assertIsInstance(fetched_key, Key)
        self.assertIsNotNone(fetched_key.id)
        self.assertIsNotNone(fetched_key.guid)
        self.assertIsNotNone(fetched_key.name)
        self.assertIsNotNone(fetched_key.description)
        self.assertIsNotNone(fetched_key.key)

        self.assertEqual(inserted_key.name, fetched_key.name)
        self.assertEqual(inserted_key.description, fetched_key.description)

    def test_insertEngine(self):

        engine = Engine()
        engine.name = testutils.generate_random_string(10)
        engine.path = testutils.generate_random_string(10)

        inserted_engine = self._sqlite_manager.insertEngine(engine)

        self.assertIsNotNone(inserted_engine)
        self.assertIsInstance(inserted_engine, Engine)
        self.assertIsNotNone(inserted_engine.path)
        self.assertEqual(engine.path, inserted_engine.path)
        self.assertIsNotNone(inserted_engine.name)
        self.assertEqual(engine.name, inserted_engine.name)
        self.assertIsNotNone(inserted_engine.guid)
        self.assertIsNotNone(inserted_engine.id)

    def test_getAllEngines(self):

        all_engines = self._sqlite_manager.getAllEngines()

        self.assertIsNotNone(all_engines)
        for engine in all_engines:
            self.assertIsInstance(engine, Engine)

    def test_getEngineOfGuid(self):
        engine = Engine()
        engine.name = testutils.generate_random_string(10)
        engine.path = testutils.generate_random_string(10)

        inserted_engine = self._sqlite_manager.insertEngine(engine)

        self.assertIsNotNone(inserted_engine)
        self.assertIsInstance(inserted_engine, Engine)
        self.assertIsNotNone(engine.path)
        self.assertEqual(engine.path, inserted_engine.path)
        self.assertIsNotNone(engine.name)
        self.assertEqual(engine.name, inserted_engine.name)
        self.assertIsNotNone(inserted_engine.guid)
        self.assertIsNotNone(inserted_engine.id)

        fetched_engine = self._sqlite_manager.getEngineOfGuid(inserted_engine.guid)

        self.assertIsNotNone(fetched_engine)
        self.assertIsInstance(fetched_engine, Engine)
        self.assertIsNotNone(fetched_engine.path)
        self.assertEqual(fetched_engine.path, inserted_engine.path)
        self.assertIsNotNone(fetched_engine.name)
        self.assertEqual(fetched_engine.name, inserted_engine.name)
        self.assertIsNotNone(fetched_engine.guid)
        self.assertEqual(fetched_engine.guid, inserted_engine.guid)
        self.assertIsNotNone(fetched_engine.id)
        self.assertEqual(fetched_engine.id, inserted_engine.id)

    def test_getEngineOfName(self):
        engine = Engine()
        engine.name = testutils.generate_random_string(10)
        engine.path = testutils.generate_random_string(10)

        inserted_engine = self._sqlite_manager.insertEngine(engine)

        self.assertIsNotNone(inserted_engine)
        self.assertIsInstance(inserted_engine, Engine)
        self.assertIsNotNone(engine.path)
        self.assertEqual(engine.path, inserted_engine.path)
        self.assertIsNotNone(engine.name)
        self.assertEqual(engine.name, inserted_engine.name)
        self.assertIsNotNone(inserted_engine.guid)
        self.assertIsNotNone(inserted_engine.id)

        fetched_engine = self._sqlite_manager.getEngineOfName(inserted_engine.name)

        self.assertIsNotNone(fetched_engine)
        self.assertIsInstance(fetched_engine, Engine)
        self.assertIsNotNone(fetched_engine.path)
        self.assertEqual(fetched_engine.path, inserted_engine.path)
        self.assertIsNotNone(fetched_engine.name)
        self.assertEqual(fetched_engine.name, inserted_engine.name)
        self.assertIsNotNone(fetched_engine.guid)
        self.assertEqual(fetched_engine.guid, inserted_engine.guid)
        self.assertIsNotNone(fetched_engine.id)
        self.assertEqual(fetched_engine.id, inserted_engine.id)

    def test_deleteEngineOfGuid(self):
        engine = Engine()
        engine.name = testutils.generate_random_string(10)
        engine.path = testutils.generate_random_string(10)

        inserted_engine = self._sqlite_manager.insertEngine(engine)

        self.assertIsNotNone(inserted_engine)
        self.assertIsInstance(inserted_engine, Engine)
        self.assertIsNotNone(engine.path)
        self.assertEqual(engine.path, inserted_engine.path)
        self.assertIsNotNone(engine.name)
        self.assertEqual(engine.name, inserted_engine.name)
        self.assertIsNotNone(inserted_engine.guid)
        self.assertIsNotNone(inserted_engine.id)

        self._sqlite_manager.deleteEngineOfGuid(inserted_engine.guid)

        deleted_engine = self._sqlite_manager.getEngineOfGuid(inserted_engine.guid)

        self.assertIsNone(deleted_engine)

    def test_insertNode(self):

        node = Node()
        node.name = testutils.generate_random_string(10)
        node.state = "UP"
        node.key_guid = uuid.uuid4()
        node.ip = "127.0.0.1"
        node.port = "65535"

        inserted_node = self._sqlite_manager.insertNode(node)

        self.assertIsNotNone(inserted_node)
        self.assertIsNotNone(inserted_node.name)
        self.assertEqual(node.name, inserted_node.name)
        self.assertIsNotNone(inserted_node.state)
        self.assertEqual(node.state, inserted_node.state)
        self.assertIsNotNone(inserted_node.key_guid)
        self.assertEqual(inserted_node.key_guid, node.key_guid)
        self.assertIsNotNone(inserted_node.ip)
        self.assertEqual(inserted_node.ip, node.ip)
        self.assertIsNotNone(inserted_node.port)
        self.assertEqual(inserted_node.port, node.port)
        self.assertIsNotNone(inserted_node.id)
        self.assertIsNotNone(inserted_node.guid)

    def test_updateNode(self):
        node = Node()
        node.name = testutils.generate_random_string(10)
        node.state = "UP"
        node.key_guid = uuid.uuid4()
        node.ip = testutils.generate_random_string(10)
        node.port = testutils.generate_random_string(10)

        inserted_node = self._sqlite_manager.insertNode(node)

        self.assertIsNotNone(inserted_node)
        self.assertIsNotNone(inserted_node.name)
        self.assertEqual(node.name, inserted_node.name)
        self.assertIsNotNone(inserted_node.state)
        self.assertEqual(node.state, inserted_node.state)
        self.assertIsNotNone(inserted_node.key_guid)
        self.assertEqual(inserted_node.key_guid, node.key_guid)
        self.assertIsNotNone(inserted_node.ip)
        self.assertEqual(inserted_node.ip, node.ip)
        self.assertIsNotNone(inserted_node.port)
        self.assertEqual(inserted_node.port, node.port)
        self.assertIsNotNone(inserted_node.id)
        self.assertIsNotNone(inserted_node.guid)

        inserted_with_updates = Node()
        inserted_with_updates.id = inserted_node.id
        inserted_with_updates.name = testutils.generate_random_string(10)
        inserted_with_updates.state = "DOWN"
        inserted_with_updates.key_guid = uuid.uuid4()
        inserted_with_updates.ip = testutils.generate_random_string(10)
        inserted_with_updates.port = testutils.generate_random_string(10)
        inserted_with_updates.guid = uuid.uuid4()

        updated_node = self._sqlite_manager.updateNode(inserted_with_updates)

        self.assertIsNotNone(updated_node)
        self.assertIsNotNone(updated_node.state)
        self.assertNotEqual(inserted_node.state, updated_node.state)
        self.assertIsNotNone(updated_node.key_guid)
        self.assertNotEqual(inserted_node.key_guid, updated_node.key_guid)
        self.assertIsNotNone(updated_node.ip)
        self.assertNotEqual(updated_node.ip, inserted_node.ip)
        self.assertIsNotNone(updated_node.port)
        self.assertNotEqual(updated_node.port, inserted_node.port)
        self.assertIsNotNone(updated_node.port)
        self.assertNotEqual(updated_node.guid, inserted_node.guid)
        self.assertIsNotNone(updated_node.id)
        self.assertEqual(updated_node.id, inserted_node.id)

    def test_getNodeOfGuid(self):

        node = Node()
        node.name = testutils.generate_random_string(10)
        node.state = "UP"
        node.key_guid = uuid.uuid4()
        node.ip = testutils.generate_random_string(10)
        node.port = testutils.generate_random_string(10)

        inserted_node = self._sqlite_manager.insertNode(node)

        self.assertIsNotNone(inserted_node)
        self.assertIsNotNone(inserted_node.name)
        self.assertEqual(node.name, inserted_node.name)
        self.assertIsNotNone(inserted_node.state)
        self.assertEqual(node.state, inserted_node.state)
        self.assertIsNotNone(inserted_node.key_guid)
        self.assertEqual(inserted_node.key_guid, node.key_guid)
        self.assertIsNotNone(inserted_node.ip)
        self.assertEqual(inserted_node.ip, node.ip)
        self.assertIsNotNone(inserted_node.port)
        self.assertEqual(inserted_node.port, node.port)
        self.assertIsNotNone(inserted_node.id)
        self.assertIsNotNone(inserted_node.guid)

        fetched_node = self._sqlite_manager.getNodeOfGuid(inserted_node.guid)

        self.assertIsNotNone(fetched_node)
        self.assertIsNotNone(fetched_node.guid)
        self.assertEqual(fetched_node.guid, inserted_node.guid)
        self.assertIsNotNone(fetched_node.id)
        self.assertEqual(fetched_node.id, inserted_node.id)
        self.assertIsNotNone(fetched_node.key_guid)
        self.assertEqual(fetched_node.key_guid, inserted_node.key_guid)
        self.assertIsNotNone(fetched_node.state)
        self.assertEqual(fetched_node.state, inserted_node.state)
        self.assertIsNotNone(fetched_node.port)
        self.assertEqual(fetched_node.port, inserted_node.port)
        self.assertIsNotNone(fetched_node.ip)
        self.assertEqual(fetched_node.ip, inserted_node.ip)
        self.assertIsNotNone(fetched_node.name)
        self.assertEqual(fetched_node.name, inserted_node.name)

    def test_getNodeOfId(self):
        node = Node()
        node.name = testutils.generate_random_string(10)
        node.state = "UP"
        node.key_guid = uuid.uuid4()
        node.ip = testutils.generate_random_string(10)
        node.port = testutils.generate_random_string(10)

        inserted_node = self._sqlite_manager.insertNode(node)

        self.assertIsNotNone(inserted_node)
        self.assertIsNotNone(inserted_node.name)
        self.assertEqual(node.name, inserted_node.name)
        self.assertIsNotNone(inserted_node.state)
        self.assertEqual(node.state, inserted_node.state)
        self.assertIsNotNone(inserted_node.key_guid)
        self.assertEqual(inserted_node.key_guid, node.key_guid)
        self.assertIsNotNone(inserted_node.ip)
        self.assertEqual(inserted_node.ip, node.ip)
        self.assertIsNotNone(inserted_node.port)
        self.assertEqual(inserted_node.port, node.port)
        self.assertIsNotNone(inserted_node.id)
        self.assertIsNotNone(inserted_node.guid)

        fetched_node = self._sqlite_manager.getNodeOfId(inserted_node.id)

        self.assertIsNotNone(fetched_node)
        self.assertIsNotNone(fetched_node.guid)
        self.assertEqual(fetched_node.guid, inserted_node.guid)
        self.assertIsNotNone(fetched_node.id)
        self.assertEqual(fetched_node.id, inserted_node.id)
        self.assertIsNotNone(fetched_node.key_guid)
        self.assertEqual(fetched_node.key_guid, inserted_node.key_guid)
        self.assertIsNotNone(fetched_node.state)
        self.assertEqual(fetched_node.state, inserted_node.state)
        self.assertIsNotNone(fetched_node.port)
        self.assertEqual(fetched_node.port, inserted_node.port)
        self.assertIsNotNone(fetched_node.ip)
        self.assertEqual(fetched_node.ip, inserted_node.ip)
        self.assertIsNotNone(fetched_node.name)
        self.assertEqual(fetched_node.name, inserted_node.name)

    def test_getNodeOfIpAndPort(self):

        node = Node()
        node.name = testutils.generate_random_string(10)
        node.state = "UP"
        node.key_guid = uuid.uuid4()
        node.ip = testutils.generate_random_string(10)
        node.port = testutils.generate_random_string(10)

        inserted_node = self._sqlite_manager.insertNode(node)

        self.assertIsNotNone(inserted_node)
        self.assertIsNotNone(inserted_node.name)
        self.assertEqual(node.name, inserted_node.name)
        self.assertIsNotNone(inserted_node.state)
        self.assertEqual(node.state, inserted_node.state)
        self.assertIsNotNone(inserted_node.key_guid)
        self.assertEqual(inserted_node.key_guid, node.key_guid)
        self.assertIsNotNone(inserted_node.ip)
        self.assertEqual(inserted_node.ip, node.ip)
        self.assertIsNotNone(inserted_node.port)
        self.assertEqual(inserted_node.port, node.port)
        self.assertIsNotNone(inserted_node.id)
        self.assertIsNotNone(inserted_node.guid)

        fetched_node = self._sqlite_manager.getNodeOfIpAndPort(inserted_node.ip, inserted_node.port)

        self.assertIsNotNone(fetched_node)
        self.assertIsNotNone(fetched_node.guid)
        self.assertEqual(fetched_node.guid, inserted_node.guid)
        self.assertIsNotNone(fetched_node.id)
        self.assertEqual(fetched_node.id, inserted_node.id)
        self.assertIsNotNone(fetched_node.key_guid)
        self.assertEqual(fetched_node.key_guid, inserted_node.key_guid)
        self.assertIsNotNone(fetched_node.state)
        self.assertEqual(fetched_node.state, inserted_node.state)
        self.assertIsNotNone(fetched_node.port)
        self.assertEqual(fetched_node.port, inserted_node.port)
        self.assertIsNotNone(fetched_node.ip)
        self.assertEqual(fetched_node.ip, inserted_node.ip)
        self.assertIsNotNone(fetched_node.name)
        self.assertEqual(fetched_node.name, inserted_node.name)

    def test_deleteNodeOfGuid(self):
        node = Node()
        node.name = testutils.generate_random_string(10)
        node.state = "UP"
        node.key_guid = uuid.uuid4()
        node.ip = testutils.generate_random_string(10)
        node.port = testutils.generate_random_string(10)

        inserted_node = self._sqlite_manager.insertNode(node)

        self.assertIsNotNone(inserted_node)
        self.assertIsNotNone(inserted_node.name)
        self.assertEqual(node.name, inserted_node.name)
        self.assertIsNotNone(inserted_node.state)
        self.assertEqual(node.state, inserted_node.state)
        self.assertIsNotNone(inserted_node.key_guid)
        self.assertEqual(inserted_node.key_guid, node.key_guid)
        self.assertIsNotNone(inserted_node.ip)
        self.assertEqual(inserted_node.ip, node.ip)
        self.assertIsNotNone(inserted_node.port)
        self.assertEqual(inserted_node.port, node.port)
        self.assertIsNotNone(inserted_node.id)
        self.assertIsNotNone(inserted_node.guid)

        self._sqlite_manager.deleteNodeOfGuid(inserted_node.guid)

        deleted_node = self._sqlite_manager.getNodeOfGuid(inserted_node.guid)

        self.assertIsNone(deleted_node)

    def test_deleteKeyOfGuid(self):
        key = Key()
        key.name = testutils.generate_random_string(10)
        key.description = testutils.generate_random_string(10)

        inserted_key = self._sqlite_manager.insertKey(key)

        self.assertIsNotNone(inserted_key)
        self.assertIsInstance(inserted_key, Key)
        self.assertIsNotNone(inserted_key.id)
        self.assertIsNotNone(inserted_key.guid)
        self.assertIsNotNone(inserted_key.name)
        self.assertEqual(inserted_key.name, key.name)
        self.assertIsNotNone(inserted_key.description)
        self.assertEqual(inserted_key.description, key.description)
        self.assertIsNotNone(inserted_key.key)

        self._sqlite_manager.deleteKeyOfGuid(inserted_key.guid)

        deleted_key = self._sqlite_manager.getKeyOfGuid(inserted_key.guid)

        self.assertIsNone(deleted_key)

    def test_getAllNodes(self):

        all_nodes = self._sqlite_manager.getAllNodes()

        self.assertIsNotNone(all_nodes)
        for node in all_nodes:
            self.assertIsInstance(node, Node)

    def test_getAllScripts(self):

        all_scripts = self._sqlite_manager.getAllScripts()

        self.assertIsNotNone(all_scripts)
        for script in all_scripts:
            self.assertIsInstance(script, Script)

    def test_insertScript(self):

        script = Script()
        script.file_name = testutils.generate_random_string(10)
        script.file_path = testutils.generate_random_string(10)
        script.script_engine = testutils.generate_random_string(10)

        inserted_script = self._sqlite_manager.insertScript(script)

        self.assertIsNotNone(inserted_script)
        self.assertIsNotNone(inserted_script.id)
        self.assertIsNotNone(inserted_script.guid)
        self.assertIsNotNone(inserted_script.script_engine)
        self.assertEqual(inserted_script.script_engine, script.script_engine)
        self.assertIsNotNone(inserted_script.file_path)
        self.assertEqual(inserted_script.file_path, script.file_path)
        self.assertIsNotNone(inserted_script.file_name)
        self.assertEqual(inserted_script.file_name, script.file_name)
        self.assertIsNotNone(inserted_script.script_engine)
        self.assertEqual(inserted_script.script_engine, script.script_engine)

    def test_deleteScriptOfId(self):

        script = Script()
        script.file_name = testutils.generate_random_string(10)
        script.file_path = testutils.generate_random_string(10)
        script.script_engine = testutils.generate_random_string(10)

        inserted_script = self._sqlite_manager.insertScript(script)

        self.assertIsNotNone(inserted_script)
        self.assertIsNotNone(inserted_script.id)
        self.assertIsNotNone(inserted_script.guid)
        self.assertIsNotNone(inserted_script.script_engine)
        self.assertEqual(inserted_script.script_engine, script.script_engine)
        self.assertIsNotNone(inserted_script.file_path)
        self.assertEqual(inserted_script.file_path, script.file_path)
        self.assertIsNotNone(inserted_script.file_name)
        self.assertEqual(inserted_script.file_name, script.file_name)
        self.assertIsNotNone(inserted_script.script_engine)
        self.assertEqual(inserted_script.script_engine, script.script_engine)

        self._sqlite_manager.deleteScriptOfId(inserted_script.id)

        deleted_script = self._sqlite_manager.getScriptOfGuid(inserted_script.guid)

        self.assertIsNone(deleted_script)

    def test_getScriptOfGuid(self):

        script = Script()
        script.file_name = testutils.generate_random_string(10)
        script.file_path = testutils.generate_random_string(10)
        script.script_engine = testutils.generate_random_string(10)

        inserted_script = self._sqlite_manager.insertScript(script)

        self.assertIsNotNone(inserted_script)
        self.assertIsNotNone(inserted_script.id)
        self.assertIsNotNone(inserted_script.guid)
        self.assertIsNotNone(inserted_script.script_engine)
        self.assertEqual(inserted_script.script_engine, script.script_engine)
        self.assertIsNotNone(inserted_script.file_path)
        self.assertEqual(inserted_script.file_path, script.file_path)
        self.assertIsNotNone(inserted_script.file_name)
        self.assertEqual(inserted_script.file_name, script.file_name)
        self.assertIsNotNone(inserted_script.script_engine)
        self.assertEqual(inserted_script.script_engine, script.script_engine)

        fetched_script = self._sqlite_manager.getScriptOfGuid(inserted_script.guid)

        self.assertIsNotNone(fetched_script)
        self.assertIsNotNone(fetched_script.id)
        self.assertIsNotNone(fetched_script.guid)
        self.assertIsNotNone(fetched_script.script_engine)
        self.assertEqual(inserted_script.script_engine, fetched_script.script_engine)
        self.assertIsNotNone(fetched_script.file_path)
        self.assertEqual(inserted_script.file_path, fetched_script.file_path)
        self.assertIsNotNone(fetched_script.file_name)
        self.assertEqual(inserted_script.file_name, fetched_script.file_name)
        self.assertIsNotNone(fetched_script.script_engine)
        self.assertEqual(inserted_script.script_engine, fetched_script.script_engine)

    def test_getScriptOfId(self):

        script = Script()
        script.file_name = testutils.generate_random_string(10)
        script.file_path = testutils.generate_random_string(10)
        script.script_engine = testutils.generate_random_string(10)

        inserted_script = self._sqlite_manager.insertScript(script)

        self.assertIsNotNone(inserted_script)
        self.assertIsNotNone(inserted_script.id)
        self.assertIsNotNone(inserted_script.guid)
        self.assertIsNotNone(inserted_script.script_engine)
        self.assertEqual(inserted_script.script_engine, script.script_engine)
        self.assertIsNotNone(inserted_script.file_path)
        self.assertEqual(inserted_script.file_path, script.file_path)
        self.assertIsNotNone(inserted_script.file_name)
        self.assertEqual(inserted_script.file_name, script.file_name)
        self.assertIsNotNone(inserted_script.script_engine)
        self.assertEqual(inserted_script.script_engine, script.script_engine)

        fetched_script = self._sqlite_manager.getScriptOfId(inserted_script.id)

        self.assertIsNotNone(fetched_script)
        self.assertIsNotNone(fetched_script.id)
        self.assertIsNotNone(fetched_script.guid)
        self.assertIsNotNone(fetched_script.script_engine)
        self.assertEqual(inserted_script.script_engine, fetched_script.script_engine)
        self.assertIsNotNone(fetched_script.file_path)
        self.assertEqual(inserted_script.file_path, fetched_script.file_path)
        self.assertIsNotNone(fetched_script.file_name)
        self.assertEqual(inserted_script.file_name, fetched_script.file_name)
        self.assertIsNotNone(fetched_script.script_engine)
        self.assertEqual(inserted_script.script_engine, fetched_script.script_engine)

    def test_deleteAllScripts(self):

        script = Script()
        script.file_name = testutils.generate_random_string(10)
        script.file_path = testutils.generate_random_string(10)
        script.script_engine = testutils.generate_random_string(10)

        all_scripts = self._sqlite_manager.getAllScripts()
        self.assertIsNotNone(all_scripts)

        self._sqlite_manager.deleteAllScripts()
        deleted_all_scripts = self._sqlite_manager.getAllScripts()

        self.assertIsNotNone(deleted_all_scripts)
        self.assertEqual(len(deleted_all_scripts), 0)

    def test_insertScriptIfNotExists(self):

        script = Script()
        script.file_name = testutils.generate_random_string(10)
        script.file_path = testutils.generate_random_string(10)
        script.script_engine = testutils.generate_random_string(10)

        inserted_script = self._sqlite_manager.insertScriptIfNotExists(script)

        self.assertIsNotNone(inserted_script)
        self.assertIsNotNone(inserted_script.id)
        self.assertIsNotNone(inserted_script.guid)
        self.assertIsNotNone(inserted_script.script_engine)
        self.assertEqual(inserted_script.script_engine, script.script_engine)
        self.assertIsNotNone(inserted_script.file_path)
        self.assertEqual(inserted_script.file_path, script.file_path)
        self.assertIsNotNone(inserted_script.file_name)
        self.assertEqual(inserted_script.file_name, script.file_name)
        self.assertIsNotNone(inserted_script.script_engine)
        self.assertEqual(inserted_script.script_engine, script.script_engine)

        # second script here has the same file name so should get inserted_script returned
        second_script = Script()
        second_script.file_name = script.file_name
        second_script.file_path = testutils.generate_random_string(10)
        second_script.script_engine = testutils.generate_random_string(10)

        already_existing_script = self._sqlite_manager.insertScriptIfNotExists(second_script)

        self.assertIsNotNone(already_existing_script)
        self.assertIsNotNone(already_existing_script.id)
        self.assertEqual(already_existing_script.id, inserted_script.id)
        self.assertIsNotNone(already_existing_script.guid)
        self.assertEqual(already_existing_script.guid, inserted_script.guid)

        self.assertIsNotNone(already_existing_script.script_engine)
        self.assertEqual(inserted_script.script_engine, already_existing_script.script_engine)
        self.assertIsNotNone(already_existing_script.file_path)
        self.assertEqual(inserted_script.file_path, already_existing_script.file_path)
        self.assertIsNotNone(already_existing_script.file_name)
        self.assertEqual(inserted_script.file_name, already_existing_script.file_name)
        self.assertIsNotNone(already_existing_script.script_engine)
        self.assertEqual(inserted_script.script_engine, already_existing_script.script_engine)





