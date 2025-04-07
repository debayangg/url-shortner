import string

BASE62 = string.ascii_letters + string.digits  # a-z, A-Z, 0-9

def int_to_base62(n: int, length: int = 6) -> str:
    """Encode an integer n into a Base62 string of fixed length."""
    base = 62
    if n == 0:
        return BASE62[0] * length
    s = []
    while n:
        n, r = divmod(n, base)
        s.append(BASE62[r])
    # Pad with leading zeros if necessary
    while len(s) < length:
        s.append(BASE62[0])
    return ''.join(reversed(s))