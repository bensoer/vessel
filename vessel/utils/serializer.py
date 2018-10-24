import msgpack
import json

def serialize_object_to_bytes(message_object)->bytes:
    return msgpack.packb(message_object, use_bin_type=True)

def deserialize_bytes_to_object(object_bytes:bytes):
    return msgpack.unpackb(object_bytes, raw=False)