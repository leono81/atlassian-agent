# 🛠️ Guía de Troubleshooting - Sistema de Autenticación Híbrido

## 🚨 Diagnóstico Rápido

### ⚡ Comandos de Verificación Inmediata

```bash
# 1. ¿Está ejecutándose el servicio?
./start_atlassian_agent.sh status

# 2. ¿Está disponible el puerto?
netstat -tlnp | grep :8501

# 3. ¿Responde la aplicación?
curl -I http://localhost:8501

# 4. ¿Está accesible la base de datos?
python3 -c "from config.user_credentials_db import user_credentials_db; print(len(user_credentials_db.list_local_users()))"

# 5. Ver logs en tiempo real
tail -f logs/app.log
```

## 🔴 Problemas Críticos

### ❌ Servicio No Inicia

#### **Síntoma**: `start_atlassian_agent.sh start` falla

**Diagnóstico:**
```bash
# Verificar puerto ocupado
sudo lsof -i :8501

# Verificar permisos
ls -la start_atlassian_agent.sh

# Verificar entorno virtual
source .venv/bin/activate
python3 --version
```

**Soluciones:**

**🔧 Puerto ocupado:**
```bash
# Encontrar proceso ocupando puerto
sudo lsof -i :8501
# Resultado: streamlit  12345 user...

# Matar proceso
sudo kill -9 12345

# Limpiar archivo PID obsoleto
rm -f atlassian_agent.pid

# Reintentar inicio
./start_atlassian_agent.sh start
```

**🔧 Permisos incorrectos:**
```bash
# Dar permisos de ejecución
chmod +x start_atlassian_agent.sh

# Verificar owner del directorio
sudo chown -R $USER:$USER /opt/atlassian-agent
```

**🔧 Entorno virtual dañado:**
```bash
# Recrear entorno virtual
rm -rf .venv
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### ❌ Base de Datos Inaccesible

#### **Síntoma**: Error "No such table" o "Database locked"

**Diagnóstico:**
```bash
# Verificar archivo de BD
ls -la .streamlit/user_credentials.db

# Verificar permisos
stat .streamlit/user_credentials.db

# Test de conexión manual
python3 -c "
import sqlite3
conn = sqlite3.connect('.streamlit/user_credentials.db')
cursor = conn.cursor()
cursor.execute('SELECT name FROM sqlite_master WHERE type=\"table\"')
print('Tablas:', cursor.fetchall())
conn.close()
"
```

**Soluciones:**

**🔧 BD no existe:**
```bash
# Crear directorio
mkdir -p .streamlit

# Inicializar BD
python3 -c "
from config.user_credentials_db import user_credentials_db
print('BD inicializada')
"
```

**🔧 BD bloqueada:**
```bash
# Verificar procesos usando BD
sudo lsof .streamlit/user_credentials.db

# Si hay procesos, matarlos
sudo kill -9 <PID>

# Reiniciar servicio
./start_atlassian_agent.sh restart
```

**🔧 BD corrupta:**
```bash
# Backup BD actual
cp .streamlit/user_credentials.db .streamlit/user_credentials.db.corrupted

# Recrear BD (CUIDADO: borra datos)
rm .streamlit/user_credentials.db
python3 -c "from config.user_credentials_db import user_credentials_db; print('BD recreada')"

# Restaurar desde backup si existe
# cp backup/user_credentials.db.backup .streamlit/user_credentials.db
```

### ❌ No Puedo Hacer Login

#### **Síntoma**: "Invalid credentials" o "User not found"

**Diagnóstico:**
```bash
# Verificar usuario existe
python3 -c "
from config.user_credentials_db import user_credentials_db
users = user_credentials_db.list_local_users()
for user in users:
    print(f'Usuario: {user[\"user_email\"]}, Activo: {user[\"is_active\"]}')
"

# Ver logs de autenticación
grep "login_failed" logs/app.log | tail -5
```

**Soluciones:**

**🔧 Usuario no existe:**
```bash
# Crear usuario desde línea de comandos
python3 -c "
from config.user_credentials_db import user_credentials_db
result = user_credentials_db.create_local_user(
    'tu-email@empresa.com',
    'Tu Nombre',
    'TuPassword123',
    True  # es admin
)
print('Usuario creado:', result)
"
```

**🔧 Usuario desactivado:**
```bash
# Activar usuario
python3 -c "
from config.user_credentials_db import user_credentials_db
result = user_credentials_db.toggle_local_user_status('tu-email@empresa.com', True)
print('Usuario activado:', result)
"
```

**🔧 Usuario bloqueado (intentos fallidos):**
```bash
# Resetear intentos fallidos
python3 -c "
from config.user_credentials_db import user_credentials_db
# Esto se hace automáticamente al resetear password
result = user_credentials_db.update_local_user_password('tu-email@empresa.com', 'NuevaPassword123')
print('Password reseteado:', result)
"
```

**🔧 Crear admin de emergencia:**
```bash
# Para cuando no tienes acceso a ningún admin
python3 -c "
from config.user_credentials_db import user_credentials_db
import uuid
emergency_password = 'Emergency' + str(uuid.uuid4())[:8]
result = user_credentials_db.create_local_user(
    'emergency@empresa.com',
    'Admin Emergencia',
    emergency_password,
    True
)
print(f'Admin emergencia creado: emergency@empresa.com')
print(f'Password: {emergency_password}')
print('CAMBIAR PASSWORD INMEDIATAMENTE')
"
```

## 🟡 Problemas Comunes

### ⚠️ Lentitud del Sistema

#### **Síntoma**: Aplicación responde muy lento

**Diagnóstico:**
```bash
# CPU y memoria
top -p $(cat atlassian_agent.pid)

# Espacio en disco
df -h

# Logs de error
grep -i "error\|exception" logs/app.log | tail -10

# Tamaño de BD
ls -lh .streamlit/user_credentials.db
```

**Soluciones:**

**🔧 Memoria insuficiente:**
```bash
# Verificar RAM disponible
free -h

# Si es VPS pequeña, considerar swap
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
```

**🔧 BD grande:**
```bash
# Limpiar sesiones expiradas
python3 -c "
from config.user_credentials_db import user_credentials_db
# Implementar función de limpieza si no existe
import sqlite3
conn = sqlite3.connect('.streamlit/user_credentials.db')
cursor = conn.cursor()
cursor.execute('DELETE FROM local_user_sessions WHERE expires_at < datetime(\"now\")')
deleted = cursor.rowcount
conn.commit()
conn.close()
print(f'Sesiones expiradas eliminadas: {deleted}')
"
```

### ⚠️ Panel de Admin Inaccesible

#### **Síntoma**: "Access Denied" en panel de administración

**Diagnóstico:**
```bash
# Verificar permisos del usuario
python3 -c "
from config.user_credentials_db import user_credentials_db
users = user_credentials_db.list_local_users()
for user in users:
    if user['is_admin']:
        print(f'Admin: {user[\"user_email\"]}, Activo: {user[\"is_active\"]}')
"
```

**Soluciones:**

**🔧 No hay usuarios admin:**
```bash
# Promover usuario existente a admin
python3 -c "
from config.user_credentials_db import user_credentials_db
import sqlite3
conn = sqlite3.connect('.streamlit/user_credentials.db')
cursor = conn.cursor()
cursor.execute('UPDATE local_users SET is_admin = 1 WHERE user_email = \"tu-email@empresa.com\"')
conn.commit()
conn.close()
print('Usuario promovido a admin')
"
```

**🔧 Usuario admin desactivado:**
```bash
# Activar usuario admin
python3 -c "
from config.user_credentials_db import user_credentials_db
result = user_credentials_db.toggle_local_user_status('admin@empresa.com', True)
print('Admin activado:', result)
"
```

### ⚠️ Errores de Importación

#### **Síntoma**: "ModuleNotFoundError" o "ImportError"

**Diagnóstico:**
```bash
# Verificar entorno virtual activo
which python3
echo $VIRTUAL_ENV

# Verificar dependencias instaladas
pip list | grep -E "(streamlit|bcrypt|sqlite)"
```

**Soluciones:**

**🔧 Entorno virtual no activo:**
```bash
# Activar entorno virtual
source .venv/bin/activate

# Verificar
which python3  # Debe mostrar ruta en .venv/
```

**🔧 Dependencias faltantes:**
```bash
# Reinstalar dependencias
source .venv/bin/activate
pip install -r requirements.txt --force-reinstall

# Si falla bcrypt
sudo apt-get install build-essential libffi-dev
pip install bcrypt --force-reinstall
```

## 🔧 Herramientas de Diagnóstico

### 📊 Script de Health Check

```bash
# Crear script de diagnóstico
cat > health_check.sh << 'EOF'
#!/bin/bash

echo "=== HEALTH CHECK ATLASSIAN AGENT ==="
echo "$(date)"
echo

# 1. Servicio
echo "1. ESTADO DEL SERVICIO:"
./start_atlassian_agent.sh status
echo

# 2. Puerto
echo "2. PUERTO 8501:"
if netstat -tlnp | grep :8501 > /dev/null; then
    echo "✅ Puerto 8501 está en uso"
else
    echo "❌ Puerto 8501 libre"
fi
echo

# 3. Base de datos
echo "3. BASE DE DATOS:"
if [ -f ".streamlit/user_credentials.db" ]; then
    DB_SIZE=$(stat -c%s ".streamlit/user_credentials.db")
    echo "✅ BD existe (${DB_SIZE} bytes)"
    
    # Test conexión
    python3 -c "
from config.user_credentials_db import user_credentials_db
try:
    users = user_credentials_db.list_local_users()
    print(f'✅ BD accesible ({len(users)} usuarios)')
except Exception as e:
    print(f'❌ Error BD: {e}')
"
else
    echo "❌ BD no existe"
fi
echo

# 4. Logs recientes
echo "4. LOGS RECIENTES (últimas 5 líneas):"
if [ -f "logs/app.log" ]; then
    tail -5 logs/app.log
else
    echo "❌ No se encontraron logs"
fi
echo

# 5. Recursos del sistema
echo "5. RECURSOS:"
echo "CPU y Memoria del proceso:"
if [ -f "atlassian_agent.pid" ]; then
    PID=$(cat atlassian_agent.pid)
    ps -p $PID -o pid,ppid,%cpu,%mem,cmd 2>/dev/null || echo "❌ Proceso no encontrado"
else
    echo "❌ Archivo PID no encontrado"
fi
echo

echo "Espacio en disco:"
df -h . | tail -1
echo

echo "=== FIN HEALTH CHECK ==="
EOF

chmod +x health_check.sh
```

## 📋 Checklist de Troubleshooting

### ✅ Antes de Reportar Problema

- [ ] Ejecutar `health_check.sh`
- [ ] Revisar logs: `tail -20 logs/app.log`
- [ ] Verificar espacio en disco: `df -h`
- [ ] Probar restart: `./start_atlassian_agent.sh restart`
- [ ] Verificar conectividad: `curl -I http://localhost:8501`

### ✅ Información para Soporte

**Incluir siempre:**
1. **Síntoma específico**: Qué estaba haciendo cuando falló
2. **Logs**: Últimas 20 líneas de `logs/app.log`
3. **Output del health check**: `./health_check.sh`
4. **Versión del sistema**: `cat /etc/os-release`
5. **Configuración Python**: `python3 --version` y `pip list`

### ✅ Escalación por Prioridad

**🔴 Crítico (resolver inmediatamente):**
- Sistema no inicia
- Base de datos inaccesible
- No hay administradores disponibles

**🟡 Alto (resolver en 24h):**
- Lentitud significativa
- Algunos usuarios no pueden acceder
- Errores frecuentes en logs

**🟢 Medio (resolver en semana):**
- Problemas cosméticos de UI
- Optimizaciones de rendimiento
- Nuevas funcionalidades

## 🆘 Contactos de Emergencia

### 🔧 Auto-recuperación

```bash
# Script de recuperación automática
cat > emergency_recovery.sh << 'EOF'
#!/bin/bash
echo "🆘 RECUPERACIÓN DE EMERGENCIA"

# 1. Parar servicio
./start_atlassian_agent.sh stop

# 2. Crear admin emergencia si no hay admins
python3 -c "
from config.user_credentials_db import user_credentials_db
import uuid

# Verificar si hay admins
users = user_credentials_db.list_local_users()
admins = [u for u in users if u['is_admin'] and u['is_active']]

if not admins:
    password = 'Emergency' + str(uuid.uuid4())[:8] + '!'
    result = user_credentials_db.create_local_user(
        'emergency@empresa.com',
        'Admin Emergencia',
        password,
        True
    )
    print(f'✅ Admin emergencia creado:')
    print(f'Email: emergency@empresa.com')
    print(f'Password: {password}')
    print('⚠️ CAMBIAR PASSWORD INMEDIATAMENTE')
else:
    print(f'✅ {len(admins)} admin(s) disponible(s)')
"

# 3. Limpiar sesiones problemáticas
python3 -c "
import sqlite3
conn = sqlite3.connect('.streamlit/user_credentials.db')
cursor = conn.cursor()
cursor.execute('UPDATE local_user_sessions SET is_active = 0')
conn.commit()
conn.close()
print('✅ Sesiones limpiadas')
"

# 4. Reiniciar servicio
./start_atlassian_agent.sh start

echo "🆘 RECUPERACIÓN COMPLETADA"
EOF

chmod +x emergency_recovery.sh
```

**Solo usar en emergencias reales cuando el sistema esté completamente inaccesible.** 