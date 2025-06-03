# config/user_credentials_db.py
import sqlite3
import json
from pathlib import Path
from typing import Optional, Tuple
from config.encryption import credential_encryption
import logfire

class UserCredentialsDB:
    def __init__(self):
        self.db_path = Path(".streamlit/user_credentials.db")
        self._init_db()
    
    def _init_db(self):
        """Inicializa la base de datos"""
        self.db_path.parent.mkdir(exist_ok=True)
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS user_credentials (
                    user_email TEXT PRIMARY KEY,
                    encrypted_api_key TEXT NOT NULL,
                    atlassian_username TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()
    
    def save_credentials(self, user_email: str, api_key: str, atlassian_username: str) -> bool:
        """Guarda credenciales cifradas para un usuario"""
        try:
            encrypted_api_key = credential_encryption.encrypt(api_key)
            
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO user_credentials 
                    (user_email, encrypted_api_key, atlassian_username, updated_at)
                    VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                """, (user_email, encrypted_api_key, atlassian_username))
                conn.commit()
            
            logfire.info(f"Credenciales guardadas para usuario: {user_email}")
            return True
            
        except Exception as e:
            logfire.error(f"Error guardando credenciales para {user_email}: {e}", exc_info=True)
            return False
    
    def get_credentials(self, user_email: str) -> Tuple[str, str]:
        """Obtiene y descifra credenciales de un usuario"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    SELECT encrypted_api_key, atlassian_username 
                    FROM user_credentials 
                    WHERE user_email = ?
                """, (user_email,))
                
                row = cursor.fetchone()
                if row:
                    encrypted_api_key, atlassian_username = row
                    api_key = credential_encryption.decrypt(encrypted_api_key)
                    return api_key, atlassian_username
                
            return "", ""
            
        except Exception as e:
            logfire.error(f"Error obteniendo credenciales para {user_email}: {e}", exc_info=True)
            return "", ""
    
    def delete_credentials(self, user_email: str) -> bool:
        """Elimina credenciales de un usuario"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("DELETE FROM user_credentials WHERE user_email = ?", (user_email,))
                conn.commit()
            
            logfire.info(f"Credenciales eliminadas para usuario: {user_email}")
            return True
            
        except Exception as e:
            logfire.error(f"Error eliminando credenciales para {user_email}: {e}", exc_info=True)
            return False
    
    def list_users(self) -> list:
        """Lista todos los usuarios con credenciales"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("SELECT user_email, atlassian_username, updated_at FROM user_credentials")
                return cursor.fetchall()
        except Exception as e:
            logfire.error(f"Error listando usuarios: {e}", exc_info=True)
            return []

# Instancia global
user_credentials_db = UserCredentialsDB() 