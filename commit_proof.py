import subprocess
import base64

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding


STUDENT_PRIVATE_KEY_PATH = "student_private.pem"
INSTRUCTOR_PUBLIC_KEY_PATH = "instructor_public.pem"


def get_latest_commit_hash() -> str:
    """Get latest commit hash (40-char hex) from git."""
    commit_hash = subprocess.check_output(
        ["git", "log", "-1", "--format=%H"],
        encoding="utf-8"
    ).strip()
    return commit_hash


def load_student_private_key():
    with open(STUDENT_PRIVATE_KEY_PATH, "rb") as f:
        key_data = f.read()
    private_key = serialization.load_pem_private_key(
        key_data,
        password=None,
    )
    return private_key


def load_instructor_public_key():
    with open(INSTRUCTOR_PUBLIC_KEY_PATH, "rb") as f:
        key_data = f.read()
    public_key = serialization.load_pem_public_key(
        key_data
    )
    return public_key


def sign_message(message: str, private_key) -> bytes:
    """
    Sign a message using RSA-PSS with SHA-256.

    - Sign the ASCII/UTF-8 string of commit hash
    """
    message_bytes = message.encode("utf-8")

    signature = private_key.sign(
        message_bytes,
        padding.PSS(
            mgf=padding.MGF1(hashes.SHA256()),
            salt_length=padding.PSS.MAX_LENGTH,
        ),
        hashes.SHA256(),
    )
    return signature


def encrypt_with_public_key(data: bytes, public_key) -> bytes:
    """
    Encrypt data using RSA/OAEP with public key (SHA-256).
    """
    ciphertext = public_key.encrypt(
        data,
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None,
        ),
    )
    return ciphertext


def main():
    # 1. Get commit hash
    commit_hash = get_latest_commit_hash()

    # 2. Load student private key
    student_priv = load_student_private_key()

    # 3. Sign commit hash (ASCII string)
    signature = sign_message(commit_hash, student_priv)

    # 4. Load instructor public key
    instructor_pub = load_instructor_public_key()

    # 5. Encrypt signature with instructor public key
    encrypted_signature = encrypt_with_public_key(signature, instructor_pub)

    # 6. Base64 encode encrypted signature
    encrypted_signature_b64 = base64.b64encode(encrypted_signature).decode("utf-8")

    # Output
    print("Commit Hash:")
    print(commit_hash)
    print("\nEncrypted Signature (Base64):")
    print(encrypted_signature_b64)


if __name__ == "__main__":
    main()
