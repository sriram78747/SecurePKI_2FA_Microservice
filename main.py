import os
import time
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from decrypt_seed import load_private_key, decrypt_seed
from totp_utils import generate_totp_code, verify_totp_code

app = FastAPI()


# ---------- Request Models ----------

class DecryptSeedRequest(BaseModel):
    encrypted_seed: str


class Verify2FARequest(BaseModel):
    code: str | None = None


SEED_PATH = "/data/seed.txt"


def seed_exists() -> bool:
    return os.path.exists(SEED_PATH)


def read_seed() -> str:
    if not seed_exists():
        raise FileNotFoundError("Seed not decrypted yet")
    with open(SEED_PATH, "r") as f:
        return f.read().strip()


# ---------- Endpoint 1: POST /decrypt-seed ----------

@app.post("/decrypt-seed")
def decrypt_seed_endpoint(body: DecryptSeedRequest):
    try:
        # Load private key
        private_key = load_private_key("student_private.pem")

        # Decrypt seed
        seed_hex = decrypt_seed(body.encrypted_seed, private_key)

        # Ensure /data directory exists
        os.makedirs(os.path.dirname(SEED_PATH), exist_ok=True)

        # Save to /data/seed.txt
        with open(SEED_PATH, "w") as f:
            f.write(seed_hex + "\n")

        return {"status": "ok"}

    except Exception as e:
        # For security, don't leak internal error details
        print("Decryption error:", e)
        raise HTTPException(status_code=500, detail={"error": "Decryption failed"})


# ---------- Endpoint 2: GET /generate-2fa ----------

@app.get("/generate-2fa")
def generate_2fa():
    try:
        if not seed_exists():
            raise HTTPException(
                status_code=500,
                detail={"error": "Seed not decrypted yet"},
            )

        hex_seed = read_seed()

        # Generate TOTP code
        code = generate_totp_code(hex_seed)

        # Calculate remaining seconds in current 30s period (0–29)
        now = int(time.time())
        elapsed = now % 30
        valid_for = 30 - elapsed
        if valid_for == 30:
            valid_for = 0

        return {
            "code": code,
            "valid_for": valid_for,
        }

    except HTTPException:
        raise
    except Exception as e:
        print("Generate 2FA error:", e)
        raise HTTPException(status_code=500, detail={"error": "Seed not decrypted yet"})


# ---------- Endpoint 3: POST /verify-2fa ----------

@app.post("/verify-2fa")
def verify_2fa(body: Verify2FARequest):
    # Validate code provided
    if not body.code:
        raise HTTPException(
            status_code=400,
            detail={"error": "Missing code"},
        )

    try:
        if not seed_exists():
            raise HTTPException(
                status_code=500,
                detail={"error": "Seed not decrypted yet"},
            )

        hex_seed = read_seed()

        # Verify with ±1 period tolerance (±30s)
        is_valid = verify_totp_code(hex_seed, body.code, valid_window=1)

        return {"valid": bool(is_valid)}

    except HTTPException:
        raise
    except Exception as e:
        print("Verify 2FA error:", e)
        raise HTTPException(status_code=500, detail={"error": "Seed not decrypted yet"})
