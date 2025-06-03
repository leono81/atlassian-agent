#!/usr/bin/env python3
"""
Script de migración para convertir credenciales del formato JSON 
al nuevo formato de base de datos SQLite con cifrado robusto.
"""

import json
import sys
from pathlib import Path
from datetime import datetime

# Agregar el directorio raíz al path para imports
sys.path.append(str(Path(__file__).parent.parent))

from config.user_credentials_db import user_credentials_db
from config.encryption import credential_encryption
import logfire

# Configurar Logfire para la migración
try:
    from config import settings
    logfire.configure(
        token=settings.LOGFIRE_TOKEN,
        send_to_logfire="if-token-present",
        service_name="credential_migration",
        service_version="1.0.0"
    )
except:
    # Si no se puede configurar Logfire, continuar sin él
    pass

def _decrypt_old_format(encrypted_key: str) -> str:
    """Descifra usando el formato antiguo (placeholder)"""
    if not encrypted_key:
        return ""
    if encrypted_key.startswith("PLAINTEXT_NEEDS_ENCRYPTION:"):
        return encrypted_key.split(":", 1)[1]
    return encrypted_key  # Si no tiene el prefijo, asumir que es texto plano

def migrate_credentials():
    """Migra credenciales del JSON a la base de datos SQLite"""
    json_file = Path(".streamlit/user_atlassian_keys.json")
    backup_file = Path(f".streamlit/user_atlassian_keys_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
    
    if not json_file.exists():
        print(f"✅ No se encontró archivo JSON en {json_file}. No hay nada que migrar.")
        return True
    
    print(f"🔄 Iniciando migración desde {json_file} a la base de datos SQLite...")
    
    try:
        # 1. Leer y parsear el archivo JSON
        with open(json_file, 'r') as f:
            data = json.load(f)
        
        if not isinstance(data, dict):
            print(f"❌ Error: El archivo JSON no contiene un diccionario válido.")
            return False
        
        print(f"📊 Encontrados {len(data)} usuarios en el archivo JSON.")
        
        # 2. Crear backup del archivo original
        with open(backup_file, 'w') as f:
            json.dump(data, f, indent=4)
        print(f"💾 Backup creado: {backup_file}")
        
        # 3. Migrar cada usuario
        migrated_count = 0
        skipped_count = 0
        
        for user_email, creds in data.items():
            if not isinstance(creds, dict):
                print(f"⚠️  Saltando usuario {user_email}: datos malformados ({type(creds)})")
                skipped_count += 1
                continue
            
            # Extraer credenciales
            encrypted_api_key = creds.get("api_key", "")
            atlassian_username = creds.get("username", "")
            
            if not encrypted_api_key or not atlassian_username:
                print(f"⚠️  Saltando usuario {user_email}: credenciales incompletas")
                skipped_count += 1
                continue
            
            # Descifrar usando el formato antiguo
            api_key = _decrypt_old_format(encrypted_api_key)
            
            if not api_key:
                print(f"⚠️  Saltando usuario {user_email}: no se pudo descifrar la API key")
                skipped_count += 1
                continue
            
            # Guardar en la base de datos (se cifra automáticamente)
            success = user_credentials_db.save_credentials(user_email, api_key, atlassian_username)
            
            if success:
                print(f"✅ Migrado: {user_email} -> {atlassian_username}")
                migrated_count += 1
            else:
                print(f"❌ Error migrando: {user_email}")
                skipped_count += 1
        
        # 4. Resumen de migración
        print(f"\n📈 Resumen de migración:")
        print(f"   ✅ Migrados exitosamente: {migrated_count}")
        print(f"   ⚠️  Saltados: {skipped_count}")
        print(f"   📁 Backup guardado en: {backup_file}")
        
        # 5. Verificar migración
        print(f"\n🔍 Verificando migración...")
        db_users = user_credentials_db.list_users()
        print(f"   📊 Usuarios en la BD: {len(db_users)}")
        
        for user_email, atlassian_username, updated_at in db_users:
            api_key, username = user_credentials_db.get_credentials(user_email)
            if api_key and username:
                print(f"   ✅ {user_email} -> {username} (verificado)")
            else:
                print(f"   ❌ {user_email} -> Error en verificación")
        
        if migrated_count > 0:
            print(f"\n🎉 Migración completada exitosamente!")
            print(f"💡 El archivo original se mantiene como backup.")
            print(f"💡 La aplicación ahora usará la base de datos SQLite con cifrado robusto.")
        
        logfire.info(f"Migración completada: {migrated_count} usuarios migrados, {skipped_count} saltados")
        return True
        
    except Exception as e:
        print(f"❌ Error durante la migración: {e}")
        logfire.error(f"Error en migración: {e}", exc_info=True)
        return False

def verify_migration():
    """Verifica que la migración se hizo correctamente"""
    print("\n🔍 Verificando estado de credenciales...")
    
    # Verificar BD
    db_users = user_credentials_db.list_users()
    print(f"📊 Usuarios en base de datos: {len(db_users)}")
    
    for user_email, atlassian_username, updated_at in db_users:
        print(f"   • {user_email} -> {atlassian_username} (actualizado: {updated_at})")
    
    # Verificar archivo JSON
    json_file = Path(".streamlit/user_atlassian_keys.json")
    if json_file.exists():
        print(f"📁 Archivo JSON original existe: {json_file}")
    else:
        print(f"📁 Archivo JSON original no encontrado")

if __name__ == "__main__":
    print("🚀 Script de Migración de Credenciales")
    print("="*50)
    
    # Permitir ejecutar solo verificación
    if len(sys.argv) > 1 and sys.argv[1] == "--verify":
        verify_migration()
    else:
        success = migrate_credentials()
        if success:
            print("\n" + "="*50)
            verify_migration()
        else:
            print("\n❌ La migración falló. Revisa los logs para más detalles.")
            sys.exit(1) 