from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_OAEP
from Crypto.Cipher import AES
from Crypto import Random
from Crypto.Hash import SHA256 as libsha256
import base64
import json

def generate_private_key(password:str)->str:

    key = RSA.generate(4096)
    encrypted_key = key.exportKey(passphrase=password, pkcs=8, protection="scryptAndAES128-CBC")
    return encrypted_key.decode('utf-8')


def generate_public_key(encrypted_private_key:str, password:str)->str:
    '''
    generates a public key from the returned string of the exported private key along with the password to it

    :param encrypted_private_key: str
    :param password: str
    :return: str
    '''

    private_key = RSA.import_key(encrypted_private_key, password)
    return private_key.publickey().exportKey().decode('utf-8')


def generate_aes_key(password:str)->bytes:

    hash = libsha256.new()
    hash.update(bytes(password, 'utf-8'))
    return hash.digest()


def encrypt_string_with_aes_key_to_base64_bytes(message:str, aes_key:bytes)->bytes:

    iv = Random.new().read(AES.block_size)
    cipher = AES.new(aes_key, AES.MODE_CBC, iv)

    # need to pad for CBC
    padded_message = message + (AES.block_size - len(message) % AES.block_size) * chr(AES.block_size - len(message) % AES.block_size)
    encrypted_message = iv + cipher.encrypt(padded_message.encode())

    base64_encoded_bytes = base64.b64encode(encrypted_message)

    return base64_encoded_bytes


def decrypt_base64_bytes_with_aes_key_to_string(encrypted_base64_bytes:bytes, aes_key:bytes)->str:

    encrypted_message_with_iv = base64.b64decode(encrypted_base64_bytes)
    # bug in decoder doesn't handle not enough '=' eventhough they don't matter

    iv = encrypted_message_with_iv[:AES.block_size]
    encrypted_message = encrypted_message_with_iv[AES.block_size:]

    cipher = AES.new(aes_key, AES.MODE_CBC, iv)

    padded_plaintext_bytes = cipher.decrypt(encrypted_message)
    # strips out the padding put in for CBC
    plaintext_bytes = padded_plaintext_bytes[:-ord(padded_plaintext_bytes[len(padded_plaintext_bytes)-1:])]

    return plaintext_bytes.decode('utf-8')


def encrypt_bytes_with_public_key_to_base64_bytes(bytes_message:bytes, exported_public_key:str)->bytes:

    public_key = RSA.import_key(exported_public_key)
    cipher_rsa = PKCS1_OAEP.new(public_key, hashAlgo=libsha256)

    encrypted_bytes_message = cipher_rsa.encrypt(bytes_message)
    base64_encoded_bytes = base64.b64encode(encrypted_bytes_message)

    return base64_encoded_bytes

def encrypt_string_with_public_key_to_base64_bytes(string_message:str, exported_public_key:str)->bytes:
    '''
    pass in string representing message to be encrypted. pass also the public key to encrypt in its exported format
    (valid to be written to file if needed). This method will import it

    :param string_message: str
    :param exported_public_key: bytes
    :return: bytes
    '''

    public_key = RSA.import_key(exported_public_key.decode('utf8'))
    cipher_rsa = PKCS1_OAEP.new(public_key, hashAlgo=libsha256)

    encrypted_bytes_message = cipher_rsa.encrypt(string_message.encode())
    base64_encoded_bytes = base64.b64encode(encrypted_bytes_message)

    return base64_encoded_bytes

def decrypt_base64_bytes_with_private_key_to_bytes(base64_cipher_bytes:bytes, exported_private_key:str, private_key_password)->bytes:
    '''
    pass in rsa encrypted bytes that are then base64 encoded as bytes. pass also the private key and the private key password
    private key should be in expored format (valid to be written to file if needed). This method will import it

    :param base64_cipher_bytes: bytes
    :param exported_private_key: bytes
    :param private_key_password: str
    :return: str
    '''

    private_key = RSA.import_key(exported_private_key, private_key_password)
    cipher_rsa = PKCS1_OAEP.new(private_key, hashAlgo=libsha256)

    encrypted_bytes_message = base64.b64decode(base64_cipher_bytes)
    plaintext_bytes = cipher_rsa.decrypt(encrypted_bytes_message)

    return plaintext_bytes


def read_command(client_socket):

    full_command = ""

    buffer = ""
    # detected the start of a message
    while buffer != "{":
        buffer = client_socket.recv(1)

    full_command += buffer
    while buffer != "}":
        buffer = client_socket.recv(1)

        if buffer == "\\":
            # if escaped blindly accept the next byte
            full_command += client_socket.recv(1)
            continue

        full_command += buffer

    full_command += buffer

    return full_command

