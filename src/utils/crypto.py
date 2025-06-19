from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend
import base64
import os

class CryptoUtils:
    @staticmethod
    def generate_key() -> bytes:
        return Fernet.generate_key()
    
    @staticmethod
    def derive_key(password: str, salt: bytes) -> bytes:
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA512(),
            length=32,
            salt=salt,
            iterations=100000,
            backend=default_backend()
        )
        
        return base64.urlsafe_b64encode(kdf.derive(password.encode()))
    
    @staticmethod
    def encrypt_file(input_path: str, output_path: str, key: bytes):
        cipher = Fernet(key)
        
        with open(input_path, 'rb') as f:
            file_data = f.read()
            
        encrypted_data = cipher.encrypt(file_data)
        
        with open(output_path, 'wb') as f:
            f.write(encrypted_data)
            
    @staticmethod
    def decrypt_file(input_path: str, output_path: str, key: bytes):
        cipher = Fernet(key)
        
        with open(input_path, 'rb') as f:
            encrypted_data = f.read()
        
        try:
            decrypted_data = cipher.decrypt(encrypted_data)
        except Exception as e:
            raise ValueError("Decryption failed - possibly wrong key") from e
        
        with open(output_path, 'wb') as f:
            f.write(decrypted_data)