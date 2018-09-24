import unittest
import vessel.utils.vesselhelper as vh

class VesselHelperTests(unittest.TestCase):

    password = "mysupersecretsecurepassword"
    string_message = "Hi this is a plaintext message that will be encrypted"
    bytes_message = b'Hi this is a bytes messages that will be encrypted'

    def test_generatersakey(self):
        try:
            rsa_key = vh.generate_aes_key(self.password)
            self.assertIsNotNone(rsa_key)
        except Exception as e:
            print(e)
            self.fail("Generation of AES Key Threw An Exception")

    def test_generateprivatekey(self):
        try:
            private_key = vh.generate_private_key(self.password)
            self.assertIsNotNone(private_key)
        except Exception as e:
            print(e)
            self.fail("Generation of Private Key Threw An Exception")

    def test_generatepublickey(self):
        try:
            private_key = vh.generate_private_key(self.password)
            public_key = vh.generate_public_key(private_key, self.password)
            self.assertIsNotNone(private_key)
            self.assertIsNotNone(public_key)
        except Exception as e:
            print(e)
            self.fail("Generation of Public Key Threw An Exception")

    def test_encrypt_publickey_string(self):
        try:
            private_key = vh.generate_private_key(self.password)
            public_key = vh.generate_public_key(private_key, self.password)

            encrypted_message = vh.encrypt_string_with_public_key_to_base64_bytes(self.string_message, public_key)
            self.assertIsNotNone(encrypted_message)
            self.assertIs(type(encrypted_message), bytes)
        except Exception as e:
            print(e)
            self.fail("Encryption Of Message Threw An Exception")

    def test_encrypt_publickey_bytes(self):
        try:
            private_key = vh.generate_private_key(self.password)
            public_key = vh.generate_public_key(private_key, self.password)

            encrypted_message = vh.encrypt_bytes_with_public_key_to_base64_bytes(self.bytes_message, public_key)
            self.assertIsNotNone(encrypted_message)
            self.assertIs(type(encrypted_message), bytes)
        except Exception as e:
            print(e)
            self.fail("Encryption OF Message Threw An Exception")

    def test_decryption_privatekey_bytes(self):
        try:
            private_key = vh.generate_private_key(self.password)
            public_key = vh.generate_public_key(private_key, self.password)

            encrypted_message = vh.encrypt_bytes_with_public_key_to_base64_bytes(self.bytes_message, public_key)
            self.assertIsNotNone(encrypted_message)
            self.assertIs(type(encrypted_message), bytes)

            decrypted_message = vh.decrypt_base64_bytes_with_private_key_to_bytes(encrypted_message,
                                                                                  private_key,
                                                                                  self.password)
            self.assertIsNotNone(decrypted_message)
            self.assertIs(type(decrypted_message), bytes)
            self.assertEqual(decrypted_message, self.bytes_message)

        except Exception as e:
            print(e)
            self.fail("Encryption OF Message Threw An Exception")

    def test_encrypt_aeskey_string(self):
        try:
            aes_key = vh.generate_aes_key(self.password)

            encrypted_message = vh.encrypt_string_with_aes_key_to_base64_bytes(self.string_message, aes_key)
            self.assertIsNotNone(encrypted_message)
            self.assertIs(type(encrypted_message), bytes)
        except Exception as e:
            print(e)
            self.fail("Encryption Of Message Threw An Exception")

    def test_decrypt_aeskey_string(self):

        try:
            aes_key = vh.generate_aes_key(self.password)

            encrypted_message = vh.encrypt_string_with_aes_key_to_base64_bytes(self.string_message, aes_key)
            self.assertIsNotNone(encrypted_message)
            self.assertIs(type(encrypted_message), bytes)

            decrypted_message = vh.decrypt_base64_bytes_with_aes_key_to_string(encrypted_message, aes_key)
            self.assertIsNotNone(decrypted_message)
            self.assertIs(type(decrypted_message), str)
            self.assertEqual(decrypted_message, self.string_message)

        except Exception as e:
            print(e)
            self.fail("Encryption Of Message Threw An Exception")
