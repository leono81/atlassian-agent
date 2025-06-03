# config/encryption.py
import os
import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from pathlib import Path
import logfire

class CredentialEncryption:
    def __init__(self):
        self._key = None
        self._ensure_key()
    
    def _ensure_key(self):
        """Genera o carga la clave de cifrado"""
        key_file = Path(".streamlit/encryption.key")
        
        if key_file.exists():
            # Cargar clave existente
            with open(key_file, 'rb') as f:
                self._key = f.read()
        else:
            # Generar nueva clave
            self._key = Fernet.generate_key()
            
            # Guardar clave (también debería estar en .gitignore)
            key_file.parent.mkdir(exist_ok=True)
            with open(key_file, 'wb') as f:
                f.write(self._key)
            
            logfire.info(f"Nueva clave de cifrado generada: {key_file}")
    
    def encrypt(self, data: str) -> str:
        """Cifra un string"""
        if not data:
            return ""
        
        fernet = Fernet(self._key)
        encrypted_data = fernet.encrypt(data.encode())
        return base64.urlsafe_b64encode(encrypted_data).decode()
    
    def decrypt(self, encrypted_data: str) -> str:
        """Descifra un string"""
        if not encrypted_data:
            return ""
        
        try:
            fernet = Fernet(self._key)
            decoded_data = base64.urlsafe_b64decode(encrypted_data.encode())
            decrypted_data = fernet.decrypt(decoded_data)
            return decrypted_data.decode()
        except Exception as e:
            logfire.error(f"Error al descifrar datos: {e}")
            return ""

# Instancia global
credential_encryption = CredentialEncryption() 