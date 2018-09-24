import string
import random


def generate_random_string(length:int = 32):
    return ''.join([random.choice(string.ascii_letters + string.digits) for n in range(length)])
