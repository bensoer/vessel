import utils.cryptor as cryptor
import utils.serializer as serializer


def convert_object_to_bytes(message_object, private_key: bytes=None, private_key_password: str=None,
                             base64_aes_cipher_bytes: bytes=None)->bytes:

    # serialize the object into bytes
    message_bytes = serializer.serialize_object_to_bytes(message_object)

    # if encryption parameters were supplied, encrypt the serialized bytes
    if private_key is not None and private_key_password is not None and base64_aes_cipher_bytes is not None:
        # it is assumed we are encrypting the data
        aes_plaintext = cryptor.decrypt_base64_bytes_with_private_key_to_bytes(base64_aes_cipher_bytes,
                                                                               private_key,
                                                                               private_key_password)

        base64_encrypted_bytes = cryptor.encrypt_bytes_with_aes_key_to_base64_bytes(message_bytes, aes_plaintext)
        message_bytes = base64_encrypted_bytes

    # add padding for the sockets
    return b'{' + message_bytes + b'}'

#def convert_bytes_to_object(message_bytes:bytes):

