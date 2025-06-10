# 🔐 Sistema de Autenticación Híbrido - Atlassian Agent

## 📋 Descripción General

Este sistema implementa una **autenticación híbrida** que permite usar el **Atlassian Agent** tanto en servidores con acceso público (con Google OAuth2) como en servidores internos corporativos (con autenticación local).

### 🎯 Problema Resuelto

- **Servidores internos** sin dominio público ni HTTPS no pueden usar Google OAuth2
- **Equipos corporativos** necesitan control total sobre usuarios y permisos
- **Escalabilidad** de 4 usuarios actuales a 50+ usuarios potenciales
- **Seguridad y auditoría** requeridas para aprobación gerencial

## 🏗️ Arquitectura del Sistema

### 📊 Diagrama de Componentes

```
┌─────────────────────────────────────────────────────────────┐
│                   ATLASSIAN AGENT UI                       │
│                     (Streamlit)                            │
├─────────────────────────────────────────────────────────────┤
│                SELECTOR DE AUTENTICACIÓN                   │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐ │
│  │   Google    │  │    Local    │  │   Panel de Admin    │ │
│  │   OAuth2    │  │    Auth     │  │                     │ │
│  └─────────────┘  └─────────────┘  └─────────────────────┘ │
├─────────────────────────────────────────────────────────────┤
│               CAPA DE AUTENTICACIÓN                        │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │           user_credentials_db.py                        │ │
│  │  • user_credentials (Atlassian API keys)               │ │
│  │  • local_users (usuarios locales)                      │ │
│  │  • local_user_sessions (sesiones activas)              │ │
│  └─────────────────────────────────────────────────────────┘ │
├─────────────────────────────────────────────────────────────┤
│                  CAPA DE LOGGING                           │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │              Logfire Integration                        │ │
│  │  • Auditoría completa de acciones                      │ │
│  │  • Trazabilidad de sesiones                            │ │
│  │  • Dashboard web en tiempo real                        │ │
│  └─────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

### 🔄 Flujo de Autenticación

1. **Selector de Método**: Usuario elige entre 3 opciones
2. **Validación**: Sistema verifica credenciales según método
3. **Sesión**: Se establece sesión segura con token único
4. **Aplicación**: Usuario accede a funcionalidades del agent
5. **Auditoría**: Todas las acciones se registran en Logfire

## ⚙️ Métodos de Autenticación

### 1. 🌐 Google OAuth2
- **Uso**: Servidores con dominio público y HTTPS
- **Ventajas**: Integración con Google Workspace, SSO
- **Requisitos**: Configuración OAuth2, dominio verificado

### 2. 🏢 Autenticación Local
- **Uso**: Servidores internos corporativos
- **Ventajas**: Control total, sin dependencias externas
- **Características**:
  - Hash bcrypt con salt único
  - Sesiones con expiración configurable
  - Bloqueo automático tras 5 intentos fallidos
  - Soporte para "recordar sesión" (7 días)

### 3. ⚙️ Panel de Administración
- **Uso**: Gestión de usuarios y sistema
- **Acceso**: Solo administradores autorizados
- **Funcionalidades**: CRUD usuarios, estadísticas, logs

## 🛡️ Características de Seguridad

### 🔒 Autenticación Local
- **Hashing**: bcrypt con salt individual por usuario
- **Sesiones**: Tokens únicos con validación temporal
- **Bloqueo**: Automático tras intentos fallidos
- **Expiración**: 24h standard, 7 días con "recordar"

### 📊 Auditoría y Logging
- **Eventos registrados**:
  - Intentos de login (exitosos/fallidos)
  - Creación/eliminación de usuarios
  - Cambios de permisos y contraseñas
  - Acceso al panel de administración
  - Invalidación de sesiones

### 🔐 Control de Acceso
- **Administradores**: Acceso completo al panel de admin
- **Usuarios**: Acceso solo a funcionalidades del agent
- **Sesiones**: Validación automática en cada request

## 📂 Estructura de Base de Datos

### Tabla: `user_credentials`
```sql
user_email TEXT PRIMARY KEY,
encrypted_api_key TEXT NOT NULL,
atlassian_username TEXT NOT NULL,
updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
```

### Tabla: `local_users`
```sql
user_email TEXT PRIMARY KEY,
display_name TEXT NOT NULL,
password_hash TEXT NOT NULL,
is_admin BOOLEAN DEFAULT FALSE,
is_active BOOLEAN DEFAULT TRUE,
created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
last_login TIMESTAMP,
failed_login_attempts INTEGER DEFAULT 0
```

### Tabla: `local_user_sessions`
```sql
session_id TEXT PRIMARY KEY,
user_email TEXT NOT NULL,
created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
expires_at TIMESTAMP NOT NULL,
is_active BOOLEAN DEFAULT TRUE,
FOREIGN KEY (user_email) REFERENCES local_users(user_email)
```

## 🚀 Escalabilidad

### 📈 Capacidades Actuales
- **Usuarios simultáneos**: 50+ (limitado por hardware del servidor)
- **Sesiones activas**: Sin límite técnico
- **Performance**: SQLite optimizado para <100 usuarios

### 🔄 Migración Futura
- **Active Directory**: Integración preparada para fase futura
- **LDAP**: Arquitectura compatible
- **Base de datos**: Migración fácil a PostgreSQL/MySQL

## 🔧 Mantenimiento

### 📊 Monitoreo
- **Dashboard**: Logfire para logs en tiempo real
- **Métricas**: Panel de admin con estadísticas
- **Alertas**: Configurables en Logfire

### 🧹 Tareas de Limpieza
- **Sesiones expiradas**: Limpieza automática recomendada
- **Logs antiguos**: Rotación en Logfire
- **Backup**: SQLite fácil de respaldar

## 🔄 Compatibilidad

### ✅ Retrocompatibilidad
- **100% compatible** con sistema existente
- **Credenciales Atlassian** preservadas intactas
- **Configuración existente** sin cambios

### 🔀 Migración
- **Sin downtime**: Sistema híbrido permite migración gradual
- **Rollback**: Posible en cualquier momento
- **Datos**: Sin pérdida de información existente

## 📋 Estados del Sistema

### 🟢 Producción (Implementado)
- ✅ Selector de autenticación
- ✅ Google OAuth2 con detección de configuración
- ✅ Autenticación local completa
- ✅ Panel de administración funcional
- ✅ Base de datos con 3 tablas
- ✅ Logging completo con Logfire
- ✅ Sesiones seguras con expiración
- ✅ Control de acceso granular

### 🔵 Futuras Mejoras (Opcionales)
- 🔄 Integración con Active Directory
- 📊 Dashboard de métricas avanzadas
- 🔔 Sistema de notificaciones
- 🌐 API REST para integración externa
- 📱 App móvil para administradores

---

## 📞 Contacto y Soporte

**Documentación técnica**: Ver `docs/INSTALLATION.md` y `docs/ADMIN_GUIDE.md`
**Troubleshooting**: Ver `docs/TROUBLESHOOTING.md`
**Logs**: Dashboard en https://logfire-us.pydantic.dev/ 