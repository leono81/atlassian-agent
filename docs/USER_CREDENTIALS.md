# Gestión de Credenciales de Usuario

## Archivo de Credenciales de Atlassian

### Ubicación
`.streamlit/user_atlassian_keys.json`

### ⚠️ IMPORTANTE: SEGURIDAD
- **NUNCA subir este archivo a Git/GitHub**
- Contiene API keys y credenciales de usuarios
- Está incluido en `.gitignore`
- El cifrado actual es un placeholder - implementar cifrado robusto

### Estructura del Archivo
```json
{
  "email_del_usuario@dominio.com": {
    "api_key": "PLAINTEXT_NEEDS_ENCRYPTION:api_key_cifrada",
    "username": "usuario.atlassian@empresa.com"
  }
}
```

### Cómo se Crea
1. El usuario ingresa sus credenciales en la interfaz de Streamlit
2. Se cifran (placeholder) y guardan en este archivo
3. Se cargan automáticamente en futuras sesiones

### Mejoras de Seguridad Pendientes
- [ ] Implementar cifrado real (no placeholder)
- [ ] Usar variables de entorno para clave de cifrado
- [ ] Considerar almacenamiento en base de datos segura
- [ ] Implementar rotación de credenciales

### Archivo de Ejemplo
Ver: `.streamlit/user_atlassian_keys.json.example` 