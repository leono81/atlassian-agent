# 👑 Manual del Administrador - Sistema de Autenticación Híbrido

## 📋 Descripción del Rol

Como **administrador del sistema**, tienes acceso completo al **Panel de Administración** que te permite:

- 👥 **Gestionar usuarios** (crear, editar, eliminar)
- 📊 **Monitorear estadísticas** del sistema
- 🔒 **Controlar permisos** y seguridad
- 📋 **Revisar logs** y auditoría
- ⚙️ **Administrar configuración** del sistema

## 🚀 Acceso al Panel de Administración

### 1️⃣ Inicio de Sesión

1. **Acceder al sistema**: `http://TU_SERVIDOR:8501`
2. **Selector de autenticación**: Elegir "Panel de Administración"
3. **Credenciales**: Usar tu email y contraseña de administrador
4. **Verificación**: El sistema validará tus permisos de admin

### 2️⃣ Navegación del Panel

El panel está organizado en **5 pestañas principales**:

```
👤 Crear Usuario  |  👥 Gestionar Usuarios  |  📊 Estadísticas  |  📋 Logs  |  ⚙️ Sistema
```

## 👤 Gestión de Usuarios

### ➕ Crear Nuevos Usuarios

**Pestaña: "Crear Usuario"**

#### Formulario de Creación:
- **📧 Email**: Dirección única del usuario (ej: `juan.perez@empresa.com`)
- **🔒 Contraseña**: Mínimo 8 caracteres (se hasheará automáticamente)
- **👤 Nombre completo**: Nombre para mostrar (ej: `Juan Pérez`)
- **⚙️ Permisos de admin**: Checkbox para dar permisos administrativos

#### Validaciones Automáticas:
- ✅ Email único (no duplicados)
- ✅ Contraseña mínimo 8 caracteres
- ✅ Email válido (contiene @)
- ✅ Campos obligatorios completados

#### Proceso:
1. **Completar formulario** con datos del usuario
2. **Revisar permisos**: ¿Será administrador?
3. **Crear usuario**: Botón "✅ Crear Usuario"
4. **Confirmación**: Sistema muestra éxito/error
5. **Logging**: Acción registrada automáticamente

### 👥 Gestionar Usuarios Existentes

**Pestaña: "Gestionar Usuarios"**

#### Lista de Usuarios:
Cada usuario se muestra en un **expandible** con:

```
👤 Juan Pérez (juan.perez@empresa.com)
├── 📧 Email: juan.perez@empresa.com
├── 👤 Nombre: Juan Pérez  
├── ✅ Estado: Activo/Inactivo
├── 👑 Admin: Sí/No
├── 📅 Creado: 2024-01-15 10:30:15
├── 🕐 Último acceso: 2024-01-15 12:45:30
└── 🚫 Intentos fallidos: 0
```

#### Acciones Disponibles:

**🔄 Cambiar Estado (Toggle)**
- **Activo → Inactivo**: Usuario no podrá hacer login
- **Inactivo → Activo**: Restaurar acceso del usuario
- **Automático**: Cambio se aplica inmediatamente

**🔒 Resetear Contraseña**
1. **Botón**: "🔒 Resetear Password"
2. **Formulario**: Nueva contraseña + confirmación
3. **Validación**: Mínimo 8 caracteres, contraseñas iguales
4. **Aplicar**: Contraseña se hashea y actualiza
5. **Notificar usuario**: Comunicar nueva contraseña de forma segura

**🗑️ Eliminar Usuario**
1. **Botón**: "🗑️ Eliminar" 
2. **Confirmación**: Pantalla de advertencia
3. **Warning**: "Esta acción no se puede deshacer"
4. **Confirmación final**: "🗑️ ELIMINAR"
5. **Limpieza**: Se eliminan también todas las sesiones

### 🔐 Buenas Prácticas de Gestión

#### ✅ Recomendaciones:

**Creación de Usuarios:**
- ✅ Usar emails corporativos únicos
- ✅ Contraseñas temporales (usuario debe cambiar)
- ✅ Dar permisos admin solo cuando sea necesario
- ✅ Verificar datos antes de crear

**Gestión Regular:**
- ✅ Revisar usuarios inactivos mensualmente
- ✅ Auditar permisos de administrador trimestralmente
- ✅ Monitorear intentos de login fallidos
- ✅ Desactivar (no eliminar) usuarios que no usan el sistema

**Seguridad:**
- ✅ Resetear contraseñas comprometidas inmediatamente
- ✅ Comunicar nuevas contraseñas por canal seguro (no email)
- ✅ Revisar logs de acceso regularmente
- ✅ Mantener mínimo número de administradores

#### ❌ Evitar:

- ❌ Eliminar usuarios a menos que sea absolutamente necesario
- ❌ Dar permisos de admin sin justificación
- ❌ Usar contraseñas permanentes débiles
- ❌ Compartir credenciales de administrador

## 📊 Monitoreo y Estadísticas

### 📈 Dashboard de Métricas

**Pestaña: "Estadísticas"**

#### Métricas Principales:
```
👥 Total Usuarios    ✅ Usuarios Activos    👑 Administradores    🔐 Con Login
     12                      10                      3              8
```

#### Estadísticas de Estado:
- **Usuarios Activos vs Inactivos**: Barra de progreso visual
- **Distribución de Administradores**: Porcentaje del total
- **Usuarios con Login**: Quiénes han accedido al menos una vez

#### Integración Atlassian:
```
🔗 Credenciales Atlassian
🔑 Usuarios con credenciales Atlassian: 8

Usuarios con acceso a Atlassian:
- juan.perez@empresa.com → jperez.atlassian (actualizado: 2024-01-15)
- maria.garcia@empresa.com → mgarcia.atlassian (actualizado: 2024-01-14)
```

### 📊 Interpretación de Métricas

#### 🟢 Indicadores Saludables:
- **Alta proporción activos/total**: >80% usuarios activos
- **Pocos intentos fallidos**: <5% usuarios con intentos fallidos
- **Login reciente**: >60% usuarios con login en último mes
- **Credenciales Atlassian**: Todos los usuarios activos tienen credenciales

#### 🟡 Indicadores de Atención:
- **Usuarios inactivos**: 20-50% usuarios sin login reciente
- **Admin ratio**: >30% usuarios con permisos admin
- **Intentos fallidos**: 5-15% usuarios con intentos fallidos

#### 🔴 Indicadores de Problema:
- **Usuarios bloqueados**: >15% usuarios con máximos intentos fallidos
- **Falta de credenciales**: Usuarios activos sin credenciales Atlassian
- **Sobre-administración**: >50% usuarios con permisos admin

## 📋 Auditoría y Logs

### 🔍 Monitoreo de Logs

**Pestaña: "Logs"**

#### Dashboard de Logfire:
- **URL**: https://logfire-us.pydantic.dev/
- **Acceso**: Con credenciales de Logfire (si configurado)
- **Tiempo real**: Logs se actualizan automáticamente

#### Eventos Monitoreados:

**🔐 Autenticación:**
```json
{
  "timestamp": "2024-01-15 10:30:15",
  "action": "login_success", 
  "user": "juan.perez@empresa.com",
  "method": "local_auth",
  "ip_address": "192.168.1.100"
}
```

**👥 Gestión de Usuarios:**
```json
{
  "timestamp": "2024-01-15 10:25:42",
  "action": "user_created",
  "admin_user": "admin@empresa.com", 
  "target_user": "nuevo@empresa.com",
  "is_admin": false
}
```

**🔒 Seguridad:**
```json
{
  "timestamp": "2024-01-15 10:15:33",
  "action": "login_failed",
  "user": "test@empresa.com",
  "reason": "invalid_credentials",
  "attempts": 3
}
```

### 🚨 Alertas Importantes

#### Monitorear Activamente:

**🔴 Seguridad Crítica:**
- `login_failed` con `attempts >= 3`
- `admin_panel_access_denied` repetitivo
- `user_deleted` no autorizado
- Múltiples `login_failed` desde misma IP

**🟡 Operacionales:**
- `password_reset` frecuente del mismo usuario
- `user_created` fuera de horario laboral  
- `session_invalidated` masivo
- Acceso desde IPs no reconocidas

**🟢 Informativo:**
- `login_success` diario normal
- `admin_panel_access` autorizado
- `user_status_changed` planificado

### 📋 Tareas de Auditoría Regular

#### 🗓️ Diaria:
- ✅ Revisar intentos de login fallidos
- ✅ Verificar accesos al panel de admin
- ✅ Monitorear nuevas sesiones

#### 🗓️ Semanal:
- ✅ Auditar usuarios creados/eliminados
- ✅ Revisar cambios de permisos
- ✅ Verificar resets de contraseña

#### 🗓️ Mensual:
- ✅ Análisis completo de patrones de acceso
- ✅ Revisión de usuarios inactivos
- ✅ Limpieza de sesiones expiradas
- ✅ Backup de base de datos

## ⚙️ Configuración del Sistema

### 💾 Administración de Base de Datos

**Pestaña: "Sistema"**

#### Estado de la BD:
```
💾 Base de Datos
✅ Base de datos activa: 2048 bytes
🔄 Conexión exitosa. 12 usuarios encontrados.

📊 Estadísticas de la Base de Datos:
- 👥 Usuarios locales: 12
- 🔗 Credenciales Atlassian: 8  
- 📊 Tablas: 3 (user_credentials, local_users, local_user_sessions)
```

#### Acciones de Mantenimiento:
- **🔄 Verificar Conexión BD**: Test de conectividad
- **📊 Estadísticas BD**: Información detallada de tablas
- **🧹 Limpiar Sesiones Expiradas**: Mantenimiento automático
- **📋 Exportar Logs**: Descarga de logs para análisis

### 🛡️ Políticas de Seguridad

#### Configuración Actual:
```
🛡️ Políticas de Seguridad
- 🔒 Hashing: bcrypt con salt único
- 🎫 Sesiones: 24 horas (standard), 7 días (recordar)  
- 🚫 Bloqueo: 5 intentos fallidos
- 🔐 Contraseñas: Mínimo 8 caracteres
- 📊 Logging: Todos los eventos registrados
```

#### Configuración Avanzada:
Para cambiar estas políticas, editar archivo `.env`:

```bash
# Duración de sesiones
AUTH_SESSION_DURATION_HOURS=24
AUTH_REMEMBER_DURATION_DAYS=7

# Seguridad
AUTH_MAX_FAILED_ATTEMPTS=5
AUTH_MIN_PASSWORD_LENGTH=8
```

### 🚨 Acciones de Emergencia

#### 🔐 Usuario Comprometido:
1. **Desactivar inmediatamente**: Toggle en "Gestionar Usuarios"
2. **Invalidar sesiones**: Resetear contraseña automáticamente invalida sesiones
3. **Revisar logs**: Buscar actividad sospechosa
4. **Comunicar al usuario**: Informar del incidente

#### 🏥 Recuperación del Sistema:
```bash
# Acceso directo a BD (emergencia)
cd /opt/atlassian-agent
source .venv/bin/activate
python3 -c "
from config.user_credentials_db import user_credentials_db
# Crear admin de emergencia
user_credentials_db.create_local_user('emergency@empresa.com', 'Admin Emergencia', 'EmergencyPass123', True)
"
```

#### 🔄 Rollback de Emergencia:
```bash
# Restaurar backup de BD
cp backup/user_credentials.db.backup .streamlit/user_credentials.db

# Reiniciar servicio
./start_atlassian_agent.sh restart
```

## 📚 Flujos de Trabajo Comunes

### 🆕 Onboarding de Nuevo Usuario

1. **👤 Crear usuario** en panel de admin
2. **🔒 Generar contraseña temporal** fuerte
3. **📧 Comunicar credenciales** por canal seguro
4. **🎫 Usuario hace primer login** y cambia contraseña
5. **🔗 Configurar credenciales Atlassian** (usuario o admin)
6. **✅ Verificar acceso** a funcionalidades del agent

### 👋 Offboarding de Usuario

1. **❌ Desactivar usuario** (no eliminar inmediatamente)
2. **🔒 Invalidar sesiones** (resetear contraseña)
3. **📋 Documentar razón** en logs internos
4. **⏳ Esperar período de gracia** (30 días recomendado)
5. **🗑️ Eliminar usuario** si confirmado

### 🔄 Rotación de Contraseñas

1. **📅 Planificar rotación** (trimestral recomendado)
2. **📧 Notificar usuarios** con anticipación
3. **🔒 Forzar cambio** de contraseñas en bloque
4. **📊 Monitorear cumplimiento** via logs
5. **🎯 Seguimiento** de usuarios que no cumplen

### 🚨 Incidente de Seguridad

1. **🔍 Identificar alcance** via logs de Logfire
2. **🔐 Bloquear acceso** de usuarios afectados
3. **📋 Documentar incidente** detalladamente
4. **🔄 Implementar remediación** (reset passwords, etc.)
5. **📊 Análisis post-incidente** y mejoras

---

## 📞 Contacto y Escalación

### 🆘 Soporte Técnico

**Problemas del Sistema:**
- **Logs**: `/opt/atlassian-agent/logs/app.log`
- **BD**: `.streamlit/user_credentials.db`
- **Config**: `.streamlit/config.toml`

**Comandos de Diagnóstico:**
```bash
# Estado del servicio
./start_atlassian_agent.sh status

# Logs en tiempo real
tail -f logs/app.log

# Test de BD
python3 -c "from config.user_credentials_db import user_credentials_db; print(len(user_credentials_db.list_local_users()))"
```

### 📋 Checklist de Responsabilidades

#### ✅ Tareas Diarias:
- [ ] Revisar logs de acceso
- [ ] Verificar intentos fallidos
- [ ] Monitorear estado del servicio

#### ✅ Tareas Semanales:
- [ ] Auditar nuevos usuarios
- [ ] Revisar permisos de admin  
- [ ] Backup de base de datos

#### ✅ Tareas Mensuales:
- [ ] Análisis de uso del sistema
- [ ] Limpieza de usuarios inactivos
- [ ] Revisión de políticas de seguridad
- [ ] Actualización de documentación

**¡Recuerda!** 🔑 Con grandes poderes vienen grandes responsabilidades. Mantén la seguridad y privacidad como prioridad #1. 