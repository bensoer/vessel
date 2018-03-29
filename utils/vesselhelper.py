from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_OAEP
import base64
import json

def generate_private_key(password:str)->str:

    key = RSA.generate(2048)
    encrypted_key = key.exportKey(passphrase=password, pkcs=8, protection="scryptAndAES128-CBC")
    return encrypted_key

def generate_public_key(encrypted_private_key:str, password:str)->str:
    '''
    generates a public key from the returned string of the exported private key along with the password to it

    :param encrypted_private_key: str
    :param password: str
    :return: str
    '''

    private_key = RSA.import_key(encrypted_private_key, password)
    return private_key.publickey().exportKey()

def encrypt_string_with_public_key_to_base64_bytes(string_message:str, exported_public_key:bytes)->bytes:
    '''
    pass in string representing message to be encrypted. pass also the public key to encrypt in its exported format
    (valid to be written to file if needed). This method will import it

    :param string_message: str
    :param exported_public_key: bytes
    :return: bytes
    '''

    public_key = RSA.import_key(exported_public_key.decode('utf8'))
    cipher_rsa = PKCS1_OAEP.new(public_key)

    encrypted_bytes_message = cipher_rsa.encrypt(string_message.encode())
    base64_encoded_bytes = base64.b64encode(encrypted_bytes_message)

    return base64_encoded_bytes

def decrypt_base64_bytes_with_private_key_to_string(base64_cipher_bytes:bytes, exported_private_key:bytes, private_key_password)->str:
    '''
    pass in rsa encrypted bytes that are then base64 encoded as bytes. pass also the private key and the private key password
    private key should be in expored format (valid to be written to file if needed). This method will import it

    :param base64_cipher_bytes: bytes
    :param exported_private_key: bytes
    :param private_key_password: str
    :return: str
    '''

    private_key = RSA.import_key(exported_private_key, private_key_password)
    cipher_rsa = PKCS1_OAEP.new(private_key)

    encrypted_bytes_message = base64.b64decode(base64_cipher_bytes)
    plaintext_bytes = cipher_rsa.decrypt(encrypted_bytes_message)

    return plaintext_bytes.decode('utf8')

def determine_engine_for_script(script_name):

    filetype2engine = {
        'ps1': 'powershell.exe',
        'py': 'python',
        'sql': 'sqlcmd',
        'bat': '',
        'exe': ''
    }

    file_type = script_name[script_name.rfind('.')+1:]
    return filetype2engine.get(file_type, None)


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

