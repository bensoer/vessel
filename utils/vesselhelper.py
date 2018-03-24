from Crypto.PublicKey import RSA

def generate_private_key(password):
    key = RSA.generate(2048)
    encrypted_key = key.exportKey(passphrase=password, pkcs=8, protection="scryptAndAES128-CBC")
    return encrypted_key

def generate_public_key(encrypted_private_key, password):

    private_key = RSA.import_key(encrypted_private_key, password)
    return private_key.publickey().exportKey()


def determine_engine_for_script(script_name):

    filetype2engine = {
        'ps1': 'powershell',
        'py': 'python',
        'sql': 'sql',
        'batch': 'batch',
        'exe': 'executable'
    }

    file_type = script_name[script_name.rfind('.')+1:]
    return filetype2engine.get(file_type, None)

