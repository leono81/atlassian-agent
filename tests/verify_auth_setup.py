#!/usr/bin/env python3
"""
Script de verificación para la configuración de autenticación.
Ejecuta este script para verificar que todo esté configurado correctamente.
"""

import os
import sys
from pathlib import Path

def check_file_exists(file_path, description):
    """Verifica si un archivo existe."""
    if Path(file_path).exists():
        print(f"✅ {description}: {file_path}")
        return True
    else:
        print(f"❌ {description}: {file_path} - NO ENCONTRADO")
        return False

def check_secrets_file():
    """Verifica el archivo de secrets."""
    secrets_path = ".streamlit/secrets.toml"
    if not check_file_exists(secrets_path, "Archivo de secrets"):
        return False
    
    try:
        with open(secrets_path, 'r') as f:
            content = f.read()
        
        required_keys = [
            "redirect_uri",
            "cookie_secret", 
            "client_id",
            "client_secret",
            "server_metadata_url"
        ]
        
        missing_keys = []
        for key in required_keys:
            if key not in content:
                missing_keys.append(key)
        
        if missing_keys:
            print(f"❌ Faltan claves en secrets.toml: {', '.join(missing_keys)}")
            return False
        
        # Verificar que no tengan valores de template
        template_values = [
            "REEMPLAZA_CON_UN_SECRET_ALEATORIO",
            "TU_GOOGLE_CLIENT_ID",
            "TU_GOOGLE_CLIENT_SECRET"
        ]
        
        for template_val in template_values:
            if template_val in content:
                print(f"❌ Encontrado valor de template en secrets.toml: {template_val}")
                print("   Debes reemplazar este valor con tu configuración real")
                return False
        
        print("✅ Archivo secrets.toml configurado correctamente")
        return True
        
    except Exception as e:
        print(f"❌ Error leyendo secrets.toml: {e}")
        return False

def check_gitignore():
    """Verifica que .gitignore proteja los secrets."""
    gitignore_path = ".gitignore"
    if not check_file_exists(gitignore_path, "Archivo .gitignore"):
        return False
    
    try:
        with open(gitignore_path, 'r') as f:
            content = f.read()
        
        if ".streamlit/secrets.toml" in content:
            print("✅ .gitignore protege secrets.toml")
            return True
        else:
            print("❌ .gitignore NO protege secrets.toml")
            print("   Agrega esta línea: .streamlit/secrets.toml")
            return False
            
    except Exception as e:
        print(f"❌ Error leyendo .gitignore: {e}")
        return False

def check_environment():
    """Verifica variables de entorno necesarias."""
    env_vars = ["MEM0_API_KEY", "OPENAI_API_KEY"]
    found_vars = []
    
    for var in env_vars:
        if os.getenv(var):
            found_vars.append(var)
            print(f"✅ Variable de entorno: {var}")
        else:
            print(f"⚠️  Variable de entorno: {var} - NO ENCONTRADA")
    
    if found_vars:
        print(f"✅ Al menos una variable de entorno configurada: {', '.join(found_vars)}")
        return True
    else:
        print("❌ No se encontraron variables de entorno necesarias")
        return False

def check_streamlit_version():
    """Verifica la versión de Streamlit."""
    try:
        import streamlit as st
        version = st.__version__
        
        # Verificar que tenga soporte para autenticación nativa
        if hasattr(st, 'login') and hasattr(st, 'logout'):
            print(f"✅ Streamlit {version} con soporte de autenticación nativa")
            return True
        else:
            print(f"❌ Streamlit {version} NO tiene soporte de autenticación nativa")
            print("   Actualiza Streamlit: pip install --upgrade streamlit")
            return False
            
    except ImportError:
        print("❌ Streamlit no está instalado")
        return False

def main():
    """Función principal de verificación."""
    print("🔍 Verificando configuración de autenticación...\n")
    
    checks = [
        ("Directorio .streamlit", lambda: check_file_exists(".streamlit", "Directorio de configuración")),
        ("Template de secrets", lambda: check_file_exists(".streamlit/secrets.toml.template", "Template de secrets")),
        ("Archivo de secrets", check_secrets_file),
        ("Protección .gitignore", check_gitignore),
        ("Variables de entorno", check_environment),
        ("Versión de Streamlit", check_streamlit_version),
        ("Archivos de documentación", lambda: all([
            check_file_exists("SETUP_OAUTH.md", "Guía OAuth2"),
            check_file_exists("AUTHENTICATION_GUIDE.md", "Guía de autenticación"),
            check_file_exists("generate_cookie_secret.py", "Generador de cookie secret")
        ]))
    ]
    
    passed = 0
    total = len(checks)
    
    for name, check_func in checks:
        print(f"\n--- {name} ---")
        if check_func():
            passed += 1
        else:
            print(f"💡 Consulta AUTHENTICATION_GUIDE.md para solucionar este problema")
    
    print(f"\n{'='*50}")
    print(f"📊 RESUMEN: {passed}/{total} verificaciones pasaron")
    
    if passed == total:
        print("🎉 ¡Todo configurado correctamente!")
        print("🚀 Puedes ejecutar: streamlit run ui/app.py")
    else:
        print("⚠️  Hay problemas de configuración que debes resolver")
        print("📖 Consulta AUTHENTICATION_GUIDE.md para más detalles")
        sys.exit(1)

if __name__ == "__main__":
    main() 