#!/usr/bin/env python3
"""
Script para generar un cookie secret seguro para Streamlit Authentication.
Ejecuta este script y copia el resultado al archivo .streamlit/secrets.toml
"""

import secrets

def generate_cookie_secret():
    """Genera un cookie secret seguro de 32 caracteres."""
    return secrets.token_urlsafe(32)

if __name__ == "__main__":
    secret = generate_cookie_secret()
    print("🔐 Cookie Secret generado:")
    print(f"cookie_secret = \"{secret}\"")
    print("\n📋 Copia esta línea completa a tu archivo .streamlit/secrets.toml")
    print("⚠️  IMPORTANTE: Mantén este secret seguro y no lo compartas públicamente.") 