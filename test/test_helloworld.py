import unittest

class HelloWorldTests(unittest.TestCase):

    def test_1(self):
        message = "Hello World!"
        self.assertEqual(message, "Hello World!")
        self.assertTrue(True)

