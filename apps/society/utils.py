import random
import string


def generate_unique_code():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
