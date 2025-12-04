import os
import time
import base64
import string

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import padding

from totp_utils import generate_totp_code, verify_totp_code

app = FastAPI()

SEED_PATH = "/data/seed.txt"
PRIVATE_KEY_PATH = "student_private.pem"


# -----------------------------
# Pydantic Models
# -----------------------------
class DecryptSeedRequest(BaseModel):
    encrypted_seed: str


class Verify2FARequest(BaseModel):
    code: str | None = None


# -----------------------------
# Helper Functions
# -----------------------------
def seed_exists() -> bool:
    return os.path.exists(SEED_PATH)


def read_seed() -> str:
    with open(SEED_PATH, "r") as f:
        return f.read().strip()


def load_private_key(path: str = PRIVATE_KEY_PATH):
    """Load RSA private key from PEM file."""
    with open(path, "rb") as key_file:
        return serialization.load_pem_private_key(
            key_file.read(),
            password=None,
        )


def decrypt_encrypted_seed(encrypted_seed_b64: str) -> str:
    """
    Decrypt base64-encoded encrypted seed using RSA/OAEP-SHA256
    and return a 64-character hex string.
    """
    private_key = load_private_key(PRIVATE_KEY_PATH)

    # 1. Base64 decode
    ciphertext = base64.b64decode(encrypted_seed_b64)

    # 2. RSA/OAEP decrypt with SHA-256
    plaintext = private_key.decrypt(
        ciphertext,
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None,
        ),
    )

    # 3. Decode as UTF-8 string
    hex_seed = plaintext.decode("utf-8").strip()

    # 4. Validate 64-char hex
    if len(hex_seed) != 64 or any(c not in string.hexdigits for c in hex_seed):
        raise ValueError("Decrypted seed is not a valid 64-character hex string")

    return hex_seed


def decrypt_and_store_seed(encrypted_seed_b64: str) -> None:
    """
    Decrypt encrypted seed and store hex seed into /data/seed.txt.
    """
    hex_seed = decrypt_encrypted_seed(encrypted_seed_b64)

    os.makedirs(os.path.dirname(SEED_PATH), exist_ok=True)
    with open(SEED_PATH, "w") as f:
        f.write(hex_seed + "\n")


# -----------------------------
# Endpoints
# -----------------------------

@app.post("/decrypt-seed")
def decrypt_seed_endpoint(body: DecryptSeedRequest):
    """
    1) Decrypt encrypted_seed using student_private.pem
    2) Store hex seed in /data/seed.txt
    """
    try:
        decrypt_and_store_seed(body.encrypted_seed)
        return {"status": "ok"}
    except Exception:
        return JSONResponse(
            status_code=500,
            content={"error": "Decryption failed"},
        )


@app.get("/generate-2fa")
def generate_2fa():
    """
    Generate current TOTP code from stored seed.
    Returns:
        {
          "code": "123456",
          "valid_for": <seconds_remaining_in_30s_window>
        }
    """
    if not seed_exists():
        return JSONResponse(
            status_code=500,
            content={"error": "Seed not decrypted yet"},
        )

    try:
        hex_seed = read_seed()
        code = generate_totp_code(hex_seed)

        # Remaining seconds in current 30s TOTP window
        remaining = 30 - int(time.time()) % 30

        return {"code": code, "valid_for": remaining}
    except Exception:
        return JSONResponse(
            status_code=500,
            content={"error": "Failed to generate code"},
        )


@app.post("/verify-2fa")
def verify_2fa(body: Verify2FARequest):
    """
    Verify TOTP code with ±1 period tolerance.
    """
    # 1. Validate code is provided
    if not body.code:
        return JSONResponse(
            status_code=400,
            content={"error": "Missing code"},
        )

    # 2. Check if /data/seed.txt exists
    if not seed_exists():
        return JSONResponse(
            status_code=500,
            content={"error": "Seed not decrypted yet"},
        )

    try:
        # 3. Read hex seed from file
        hex_seed = read_seed()

        # 4. Verify TOTP code with ±1 period tolerance (valid_window=1)
        is_valid = verify_totp_code(hex_seed, body.code, valid_window=1)

        # 5. Return {"valid": true/false}
        return {"valid": bool(is_valid)}

    except Exception:
        return JSONResponse(
            status_code=500,
            content={"error": "Seed not decrypted yet"},
        )
