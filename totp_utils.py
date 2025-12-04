import os
import hmac
import hashlib
import base64
import time

def load_seed():
    path = "/data/seed.txt"
    if not os.path.exists(path):
        return None
    with open(path, "r") as f:
        return f.read().strip()

def generate_totp_code(hex_seed: str, interval=30):
    key = bytes.fromhex(hex_seed)
    timestep = int(time.time()) // interval
    msg = timestep.to_bytes(8, "big")
    h = hmac.new(key, msg, hashlib.sha1).digest()
    o = h[-1] & 0x0F
    code = (int.from_bytes(h[o:o+4], "big") & 0x7fffffff) % 1000000
    return f"{code:06d}"

def verify_totp_code(hex_seed: str, code: str, valid_window=1):
    now = int(time.time() // 30)
    for offset in range(-valid_window, valid_window + 1):
        expected = generate_totp_code(hex_seed, interval=30)
        if expected == code:
            return True
    return False
