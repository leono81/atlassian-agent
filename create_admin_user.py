#!/usr/bin/env python3
"""
Script para crear el primer usuario administrador del sistema.
Ejecutar: python3 create_admin_user.py
"""

import sys
import os
import getpass
from pathlib import Path

# Agregar el directorio del proyecto al path
project_dir = Path(__file__).parent
sys.path.insert(0, str(project_dir))

def create_admin_user():
    """Crea el primer usuario administrador del sistema."""
    
    print("🚀 Creación del Primer Usuario Administrador")
    print("=" * 50)
    print()
    
    try:
        # Importar la base de datos
        from config.user_credentials_db import user_credentials_db
        
        # Verificar si ya existen usuarios
        existing_users = user_credentials_db.list_local_users()
        if existing_users:
            print("⚠️  Ya existen usuarios en el sistema:")
            for user in existing_users:
                admin_status = "👑 Admin" if user['is_admin'] else "👤 Usuario"
                status = "✅ Activo" if user['is_active'] else "❌ Inactivo"
                print(f"   - {user['user_email']} ({admin_status}) - {status}")
            print()
            
            continuar = input("¿Quieres crear otro usuario? (s/N): ").lower().strip()
            if continuar not in ['s', 'si', 'sí', 'y', 'yes']:
                print("✅ Operación cancelada.")
                return True
            print()
        
        # Solicitar datos del usuario
        print("📝 Datos del nuevo usuario administrador:")
        print()
        
        # Email
        while True:
            email = input("📧 Email del administrador: ").strip()
            if not email:
                print("❌ El email no puede estar vacío.")
                continue
            if "@" not in email:
                print("❌ Email inválido. Debe contener '@'.")
                continue
            if user_credentials_db.local_user_exists(email):
                print("❌ Ya existe un usuario con ese email.")
                continue
            break
        
        # Nombre completo
        while True:
            nombre = input("👤 Nombre completo: ").strip()
            if not nombre:
                print("❌ El nombre no puede estar vacío.")
                continue
            break
        
        # Contraseña
        while True:
            password = getpass.getpass("🔒 Contraseña (mín. 8 caracteres): ")
            if len(password) < 8:
                print("❌ La contraseña debe tener al menos 8 caracteres.")
                continue
            
            password_confirm = getpass.getpass("🔒 Confirmar contraseña: ")
            if password != password_confirm:
                print("❌ Las contraseñas no coinciden.")
                continue
            break
        
        print()
        print("📋 Resumen del usuario a crear:")
        print(f"   📧 Email: {email}")
        print(f"   👤 Nombre: {nombre}")
        print(f"   👑 Tipo: Administrador")
        print()
        
        confirmar = input("¿Crear este usuario? (S/n): ").lower().strip()
        if confirmar in ['n', 'no']:
            print("✅ Operación cancelada.")
            return True
        
        # Crear el usuario
        print("⏳ Creando usuario...")
        
        resultado = user_credentials_db.create_local_user(
            user_email=email,
            display_name=nombre,
            password=password,
            is_admin=True
        )
        
        if resultado:
            print()
            print("🎉 ¡Usuario administrador creado exitosamente!")
            print()
            print("📋 Información del usuario:")
            print(f"   📧 Email: {email}")
            print(f"   👤 Nombre: {nombre}")
            print(f"   👑 Permisos: Administrador")
            print()
            print("🔍 Próximos pasos:")
            print("   1. Inicia la aplicación con: python -m streamlit run app_chat.py")
            print("   2. Ve a http://localhost:8501 (o la IP de tu servidor)")
            print("   3. Selecciona 'Autenticación Local'")
            print("   4. Inicia sesión con las credenciales que acabas de crear")
            print("   5. Accede al 'Panel de Administración' para crear más usuarios")
            print()
            print("🔒 IMPORTANTE: Guarda estas credenciales en un lugar seguro")
            
            return True
        else:
            print("❌ Error al crear el usuario. Verifica los logs para más detalles.")
            return False
            
    except ImportError as e:
        print("❌ Error importando dependencias:")
        print(f"   {e}")
        print()
        print("🔧 Soluciones:")
        print("   1. Verifica que estás en el directorio correcto del proyecto")
        print("   2. Activa el entorno virtual: source .venv/bin/activate")
        print("   3. Instala dependencias: pip install -r requirements.txt")
        return False
        
    except Exception as e:
        print(f"❌ Error inesperado: {e}")
        print()
        print("🔧 Revisa los logs o contacta al soporte técnico.")
        return False

def verificar_entorno():
    """Verifica que el entorno esté configurado correctamente."""
    
    print("🔍 Verificando entorno...")
    
    # Verificar directorio .streamlit
    streamlit_dir = Path(".streamlit")
    if not streamlit_dir.exists():
        print("📁 Creando directorio .streamlit...")
        streamlit_dir.mkdir(exist_ok=True)
    
    # Verificar que se pueden importar las dependencias básicas
    try:
        import sqlite3
        import bcrypt
        print("✅ Dependencias básicas disponibles")
        return True
    except ImportError as e:
        print(f"❌ Faltan dependencias: {e}")
        print("🔧 Ejecuta: pip install -r requirements.txt")
        return False

if __name__ == "__main__":
    print("🏢 Sistema de Usuarios - Agente Atlassian")
    print("=" * 50)
    print()
    
    # Verificar entorno
    if not verificar_entorno():
        sys.exit(1)
    
    # Crear usuario
    if create_admin_user():
        print("✅ Proceso completado exitosamente.")
    else:
        print("❌ El proceso falló.")
        sys.exit(1) 