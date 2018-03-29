from Crypto.PublicKey import RSA
import json

def generate_private_key(password):
    key = RSA.generate(2048)
    encrypted_key = key.exportKey(passphrase=password, pkcs=8, protection="scryptAndAES128-CBC")
    return encrypted_key

def generate_public_key(encrypted_private_key, password):

    private_key = RSA.import_key(encrypted_private_key, password)
    return private_key.publickey().exportKey()


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

