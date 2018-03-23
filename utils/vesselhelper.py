from Crypto.PublicKey import RSA

def generate_private_key(password):
    key = RSA.generate(2048)
    encrypted_key = key.exportKey(passphrase=password, pkcs=8, protection="scryptAndAES128-CBC")
    return encrypted_key

def generate_public_key(encrypted_private_key, password):

    private_key = RSA.import_key(encrypted_private_key, password)
    return private_key.publickey().exportKey()