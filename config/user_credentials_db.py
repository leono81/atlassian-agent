# config/user_credentials_db.py
import sqlite3
import json
import hashlib
import secrets
import bcrypt
from pathlib import Path
from typing import Optional, Tuple, List, Dict, Any
from datetime import datetime, timezone
from config.encryption import credential_encryption
import logfire

class UserCredentialsDB:
    def __init__(self):
        self.db_path = Path(".streamlit/user_credentials.db")
        self._init_db()
    
    def _init_db(self):
        """Inicializa la base de datos con todas las tablas necesarias"""
        self.db_path.parent.mkdir(exist_ok=True)
        
        with sqlite3.connect(self.db_path) as conn:
            # Tabla existente para credenciales de Atlassian (sin cambios)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS user_credentials (
                    user_email TEXT PRIMARY KEY,
                    encrypted_api_key TEXT NOT NULL,
                    atlassian_username TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Nueva tabla para usuarios locales
            conn.execute("""
                CREATE TABLE IF NOT EXISTS local_users (
                    user_email TEXT PRIMARY KEY,
                    display_name TEXT NOT NULL,
                    password_hash TEXT NOT NULL,
                    salt TEXT NOT NULL,
                    is_active BOOLEAN DEFAULT TRUE,
                    is_admin BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_login TIMESTAMP NULL,
                    failed_login_attempts INTEGER DEFAULT 0,
                    password_changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Tabla para sesiones de usuarios locales
            conn.execute("""
                CREATE TABLE IF NOT EXISTS local_user_sessions (
                    session_id TEXT PRIMARY KEY,
                    user_email TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    expires_at TIMESTAMP NOT NULL,
                    is_active BOOLEAN DEFAULT TRUE,
                    ip_address TEXT NULL,
                    user_agent TEXT NULL,
                    FOREIGN KEY (user_email) REFERENCES local_users (user_email)
                )
            """)
            
            conn.commit()
            logfire.info("Base de datos inicializada con tablas: user_credentials, local_users, local_user_sessions")

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

    def _hash_password(self, password: str) -> Tuple[str, str]:
        """
        Genera hash seguro de contraseña con salt usando bcrypt.
        Retorna tupla (password_hash, salt).
        """
        try:
            # Generar salt aleatorio
            salt = bcrypt.gensalt()
            
            # Generar hash de la contraseña
            password_hash = bcrypt.hashpw(password.encode('utf-8'), salt)
            
            # Convertir a strings para almacenar en DB
            salt_str = salt.decode('utf-8')
            hash_str = password_hash.decode('utf-8')
            
            return hash_str, salt_str
            
        except Exception as e:
            logfire.error(f"Error generando hash de contraseña: {e}", exc_info=True)
            raise
    
    def _verify_password(self, password: str, stored_hash: str, stored_salt: str) -> bool:
        """
        Verifica si una contraseña coincide con el hash almacenado.
        """
        try:
            # Convertir salt y hash de vuelta a bytes
            salt_bytes = stored_salt.encode('utf-8')
            stored_hash_bytes = stored_hash.encode('utf-8')
            
            # Generar hash de la contraseña proporcionada con el mismo salt
            password_hash = bcrypt.hashpw(password.encode('utf-8'), salt_bytes)
            
            # Comparar hashes
            return password_hash == stored_hash_bytes
            
        except Exception as e:
            logfire.error(f"Error verificando contraseña: {e}", exc_info=True)
            return False
    
    def create_local_user(self, user_email: str, display_name: str, password: str, is_admin: bool = False) -> bool:
        """
        Crea un nuevo usuario local.
        """
        try:
            # Validar que el email no existe
            if self.local_user_exists(user_email):
                logfire.warning(f"Intento de crear usuario duplicado: {user_email}")
                return False
            
            # Generar hash de contraseña
            password_hash, salt = self._hash_password(password)
            
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT INTO local_users 
                    (user_email, display_name, password_hash, salt, is_admin, created_at, updated_at, password_changed_at)
                    VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                """, (user_email, display_name, password_hash, salt, is_admin))
                conn.commit()
            
            logfire.info(f"Usuario local creado: {user_email} (admin: {is_admin})")
            return True
            
        except Exception as e:
            logfire.error(f"Error creando usuario local {user_email}: {e}", exc_info=True)
            return False
    
    def verify_local_user(self, user_email: str, password: str) -> Optional[Dict[str, Any]]:
        """
        Verifica credenciales de usuario local.
        Retorna información del usuario si es válido, None si no.
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    SELECT user_email, display_name, password_hash, salt, is_active, is_admin,
                           failed_login_attempts, last_login
                    FROM local_users 
                    WHERE user_email = ?
                """, (user_email,))
                
                row = cursor.fetchone()
                if not row:
                    logfire.info(f"Usuario local no encontrado: {user_email}")
                    return None
                
                user_email_db, display_name, password_hash, salt, is_active, is_admin, failed_attempts, last_login = row
                
                # Verificar si el usuario está activo
                if not is_active:
                    logfire.warning(f"Intento de login con usuario inactivo: {user_email}")
                    return None
                
                # Verificar contraseña
                if self._verify_password(password, password_hash, salt):
                    # Login exitoso - resetear intentos fallidos y actualizar último login
                    conn.execute("""
                        UPDATE local_users 
                        SET failed_login_attempts = 0, last_login = CURRENT_TIMESTAMP 
                        WHERE user_email = ?
                    """, (user_email,))
                    conn.commit()
                    
                    user_info = {
                        'user_email': user_email_db,
                        'display_name': display_name,
                        'is_admin': bool(is_admin),
                        'last_login': last_login
                    }
                    
                    logfire.info(f"Login exitoso usuario local: {user_email}")
                    return user_info
                else:
                    # Login fallido - incrementar contador
                    new_failed_attempts = failed_attempts + 1
                    conn.execute("""
                        UPDATE local_users 
                        SET failed_login_attempts = ? 
                        WHERE user_email = ?
                    """, (new_failed_attempts, user_email))
                    conn.commit()
                    
                    logfire.warning(f"Login fallido usuario local: {user_email} (intentos: {new_failed_attempts})")
                    
                    # Desactivar usuario si hay demasiados intentos fallidos (opcional)
                    if new_failed_attempts >= 5:
                        conn.execute("""
                            UPDATE local_users 
                            SET is_active = FALSE 
                            WHERE user_email = ?
                        """, (user_email,))
                        conn.commit()
                        logfire.warning(f"Usuario local desactivado por intentos fallidos: {user_email}")
                    
                    return None
                    
        except Exception as e:
            logfire.error(f"Error verificando usuario local {user_email}: {e}", exc_info=True)
            return None
    
    def local_user_exists(self, user_email: str) -> bool:
        """Verifica si un usuario local existe."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    SELECT COUNT(*) FROM local_users WHERE user_email = ?
                """, (user_email,))
                count = cursor.fetchone()[0]
                return count > 0
        except Exception as e:
            logfire.error(f"Error verificando existencia de usuario local {user_email}: {e}", exc_info=True)
            return False
    
    def list_local_users(self) -> List[Dict[str, Any]]:
        """Lista todos los usuarios locales."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    SELECT user_email, display_name, is_active, is_admin, 
                           created_at, last_login, failed_login_attempts
                    FROM local_users 
                    ORDER BY created_at DESC
                """)
                
                users = []
                for row in cursor.fetchall():
                    users.append({
                        'user_email': row[0],
                        'display_name': row[1],
                        'is_active': bool(row[2]),
                        'is_admin': bool(row[3]),
                        'created_at': row[4],
                        'last_login': row[5],
                        'failed_login_attempts': row[6]
                    })
                
                return users
                
        except Exception as e:
            logfire.error(f"Error listando usuarios locales: {e}", exc_info=True)
            return []
    
    def update_local_user_password(self, user_email: str, new_password: str) -> bool:
        """Actualiza la contraseña de un usuario local."""
        try:
            if not self.local_user_exists(user_email):
                return False
            
            password_hash, salt = self._hash_password(new_password)
            
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    UPDATE local_users 
                    SET password_hash = ?, salt = ?, password_changed_at = CURRENT_TIMESTAMP,
                        failed_login_attempts = 0, updated_at = CURRENT_TIMESTAMP
                    WHERE user_email = ?
                """, (password_hash, salt, user_email))
                conn.commit()
            
            logfire.info(f"Contraseña actualizada para usuario local: {user_email}")
            return True
            
        except Exception as e:
            logfire.error(f"Error actualizando contraseña para {user_email}: {e}", exc_info=True)
            return False
    
    def toggle_local_user_status(self, user_email: str, is_active: bool) -> bool:
        """Activa o desactiva un usuario local."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    UPDATE local_users 
                    SET is_active = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE user_email = ?
                """, (is_active, user_email))
                conn.commit()
            
            status = "activado" if is_active else "desactivado"
            logfire.info(f"Usuario local {status}: {user_email}")
            return True
            
        except Exception as e:
            logfire.error(f"Error cambiando estado de usuario local {user_email}: {e}", exc_info=True)
            return False
    
    def delete_local_user(self, user_email: str) -> bool:
        """Elimina un usuario local y sus sesiones."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Eliminar sesiones del usuario
                conn.execute("DELETE FROM local_user_sessions WHERE user_email = ?", (user_email,))
                
                # Eliminar usuario
                conn.execute("DELETE FROM local_users WHERE user_email = ?", (user_email,))
                conn.commit()
            
            logfire.info(f"Usuario local eliminado: {user_email}")
            return True
            
        except Exception as e:
            logfire.error(f"Error eliminando usuario local {user_email}: {e}", exc_info=True)
            return False
    
    def create_user_session(self, user_email: str, expires_in_hours: int = 24, 
                           ip_address: str = None, user_agent: str = None) -> Optional[str]:
        """Crea una sesión para un usuario local."""
        try:
            # Generar ID de sesión único
            session_id = secrets.token_urlsafe(32)
            
            # Calcular fecha de expiración
            from datetime import datetime, timedelta
            expires_at = datetime.now() + timedelta(hours=expires_in_hours)
            
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT INTO local_user_sessions 
                    (session_id, user_email, expires_at, ip_address, user_agent)
                    VALUES (?, ?, ?, ?, ?)
                """, (session_id, user_email, expires_at, ip_address, user_agent))
                conn.commit()
            
            logfire.info(f"Sesión creada para usuario local: {user_email} (session_id: {session_id[:8]}...)")
            return session_id
            
        except Exception as e:
            logfire.error(f"Error creando sesión para {user_email}: {e}", exc_info=True)
            return None
    
    def validate_user_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Valida una sesión de usuario local."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    SELECT s.user_email, s.expires_at, u.display_name, u.is_admin
                    FROM local_user_sessions s
                    JOIN local_users u ON s.user_email = u.user_email
                    WHERE s.session_id = ? AND s.is_active = TRUE AND u.is_active = TRUE
                """, (session_id,))
                
                row = cursor.fetchone()
                if not row:
                    return None
                
                user_email, expires_at_str, display_name, is_admin = row
                
                # Verificar si la sesión ha expirado
                expires_at = datetime.fromisoformat(expires_at_str.replace('Z', '+00:00'))
                if datetime.now() > expires_at:
                    # Marcar sesión como inactiva
                    conn.execute("""
                        UPDATE local_user_sessions 
                        SET is_active = FALSE 
                        WHERE session_id = ?
                    """, (session_id,))
                    conn.commit()
                    return None
                
                return {
                    'user_email': user_email,
                    'display_name': display_name,
                    'is_admin': bool(is_admin),
                    'session_id': session_id
                }
                
        except Exception as e:
            logfire.error(f"Error validando sesión {session_id}: {e}", exc_info=True)
            return None
    
    def invalidate_user_session(self, session_id: str) -> bool:
        """Invalida una sesión de usuario local."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    UPDATE local_user_sessions 
                    SET is_active = FALSE 
                    WHERE session_id = ?
                """, (session_id,))
                conn.commit()
            
            logfire.info(f"Sesión invalidada: {session_id[:8]}...")
            return True
            
        except Exception as e:
            logfire.error(f"Error invalidando sesión {session_id}: {e}", exc_info=True)
            return False

# Instancia global
user_credentials_db = UserCredentialsDB() 