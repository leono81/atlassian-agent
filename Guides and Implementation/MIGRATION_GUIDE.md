# Guía de Migración de Credenciales

Este documento describe el proceso de migración desde el sistema antiguo de credenciales (JSON con cifrado placeholder) al nuevo sistema de base de datos SQLite con cifrado robusto.

## ¿Qué ha cambiado?

### Sistema Anterior (JSON)
- **Archivo**: `.streamlit/user_atlassian_keys.json`
- **Cifrado**: Placeholder con prefijo `PLAINTEXT_NEEDS_ENCRYPTION:`
- **Formato**: JSON con credenciales por usuario
- **Seguridad**: ⚠️ Básica, solo para desarrollo

### Sistema Nuevo (SQLite + Cifrado)
- **Base de datos**: `.streamlit/user_credentials.db`
- **Cifrado**: Fernet (cryptography) con clave dedicada
- **Clave**: `.streamlit/encryption.key`
- **Seguridad**: ✅ Cifrado robusto para producción

## Proceso de Migración Automática

### 1. Ejecutar Migración

```bash
python scripts/migrate_credentials.py
```

La migración realizará automáticamente:

1. **Detección** de archivo JSON existente
2. **Backup** del archivo original con timestamp
3. **Conversión** de datos al nuevo formato
4. **Cifrado** de API keys con Fernet
5. **Verificación** de la migración

### 2. Verificar Migración

```bash
python scripts/migrate_credentials.py --verify
```

### 3. Resultados Esperados

```
🚀 Script de Migración de Credenciales
==================================================
🔄 Iniciando migración desde .streamlit/user_atlassian_keys.json a la base de datos SQLite...
📊 Encontrados 1 usuarios en el archivo JSON.
💾 Backup creado: .streamlit/user_atlassian_keys_backup_20250603_002157.json
✅ Migrado: usuario@ejemplo.com -> username.atlassian
🎉 Migración completada exitosamente!
```

## Archivos Generados

Después de la migración encontrarás:

```
.streamlit/
├── user_credentials.db                           # Nueva base de datos SQLite
├── encryption.key                                # Clave de cifrado (mantener segura)
├── user_atlassian_keys_backup_YYYYMMDD_HHMMSS.json  # Backup automático
└── user_atlassian_keys.json                     # Archivo original (puede eliminarse)
```

## Seguridad

### ⚠️ Importante para Producción

1. **Clave de cifrado**: El archivo `.streamlit/encryption.key` es crítico
   - Si se pierde, no se podrán descifrar las credenciales
   - Debe estar en `.gitignore` (ya incluido)
   - Considerar backup seguro para producción

2. **Base de datos**: `.streamlit/user_credentials.db`
   - Contiene credenciales cifradas
   - También debe estar en `.gitignore` (ya incluido)

3. **Archivos de backup**: Los archivos `*_backup_*.json`
   - Contienen credenciales en formato anterior
   - Eliminar después de verificar la migración
   - No subir a repositorios

### Recomendaciones de Producción

```bash
# Para producción, considera usar variables de entorno para la clave
export CREDENTIAL_ENCRYPTION_KEY="tu-clave-segura-aqui"

# O usar servicios de gestión de secretos como:
# - AWS Secrets Manager
# - Azure Key Vault
# - Google Secret Manager
# - HashiCorp Vault
```

## Compatibilidad

### Código Actualizado

La aplicación ha sido actualizada para usar automáticamente el nuevo sistema:

- `config/encryption.py`: Cifrado Fernet
- `config/user_credentials_db.py`: Operaciones de BD
- `ui/app.py`: Interfaz actualizada

### Funciones Eliminadas

Se han eliminado las funciones obsoletas del sistema JSON:

- ❌ `_encrypt_key()` (placeholder)
- ❌ `_decrypt_key()` (placeholder)
- ❌ `load_all_user_credentials()`
- ❌ `save_all_user_credentials()`

### Funciones Nuevas

Se han agregado funciones robustas:

- ✅ `user_credentials_db.save_credentials()`
- ✅ `user_credentials_db.get_credentials()`
- ✅ `credential_encryption.encrypt()`
- ✅ `credential_encryption.decrypt()`

## Rollback (En caso de problemas)

Si necesitas volver al sistema anterior temporalmente:

1. **Restaurar desde backup**:
   ```bash
   cp .streamlit/user_atlassian_keys_backup_*.json .streamlit/user_atlassian_keys.json
   ```

2. **Comentar el código nuevo** en `ui/app.py` y descomentar las funciones JSON

3. **Reinstalar dependencias** sin cryptography si es necesario

> ⚠️ **Nota**: El rollback no es recomendado para producción debido a la reducida seguridad del sistema anterior.

## Troubleshooting

### Error: "No module named 'cryptography'"

```bash
pip install --upgrade cryptography
# o
python -m pip install cryptography
```

### Error: "Archivo JSON malformado"

El script de migración manejará datos corruptos automáticamente y reportará usuarios que no se pudieron migrar.

### Error: "No se puede crear la base de datos"

Verificar permisos en el directorio `.streamlit/`:

```bash
ls -la .streamlit/
chmod 755 .streamlit/
```

## Soporte

Para problemas durante la migración:

1. Revisar logs de Logfire
2. Ejecutar `python scripts/migrate_credentials.py --verify`
3. Verificar que todos los archivos están en `.gitignore`
4. Contactar al equipo de desarrollo con los logs de error

---

✅ **La migración es segura**: Se crean backups automáticos y se verifica la integridad de los datos. 