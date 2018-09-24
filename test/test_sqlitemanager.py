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

    def test_createKey(self):

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

