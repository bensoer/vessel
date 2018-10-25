import nacl.utils
from nacl.public import PrivateKey, Box, PublicKey
from nacl.encoding import URLSafeBase64Encoder
import nacl.secret

def generate_private_key()->bytes:
    private_key = PrivateKey.generate()
    return private_key.encode(URLSafeBase64Encoder)


def generate_public_key(private_key:bytes)->bytes:
    private_key = PrivateKey(private_key, encoder=URLSafeBase64Encoder)
    return private_key.public_key.encode(URLSafeBase64Encoder)


def generate_aes_key()->bytes:
    return nacl.utils.random(nacl.secret.SecretBox.KEY_SIZE)


def encrypt_bytes_with_aes_key_to_base64_bytes(plaintext_bytes:bytes, aes_key:bytes)->bytes:
    box = nacl.secret.SecretBox(aes_key)
    return box.encrypt(plaintext_bytes, encoder=URLSafeBase64Encoder)


def decrypt_base64_bytes_with_aes_key_to_bytes(base64_cipher_bytes:bytes, aes_key:bytes)->bytes:
    box = nacl.secret.SecretBox(aes_key)
    return box.decrypt(base64_cipher_bytes, encoder=URLSafeBase64Encoder)


def encrypt_bytes_with_public_key_to_base64_bytes(plaintext_bytes:bytes, exported_public_key:bytes, exported_private_key:bytes)->bytes:
    private_key = PrivateKey(exported_private_key, encoder=URLSafeBase64Encoder)
    public_key = PublicKey(exported_public_key, encoder=URLSafeBase64Encoder)

    box = Box(private_key, public_key)

    return box.encrypt(plaintext_bytes, encoder=URLSafeBase64Encoder)


def decrypt_base64_bytes_with_private_key_to_bytes(base64_cipher_bytes: bytes, exported_private_key: bytes, exported_public_key: bytes)->bytes:
    private_key = PrivateKey(exported_private_key, encoder=URLSafeBase64Encoder)
    public_key = PublicKey(exported_public_key, encoder=URLSafeBase64Encoder)

    box = Box(private_key, public_key)

    return box.decrypt(base64_cipher_bytes, encoder=URLSafeBase64Encoder)

