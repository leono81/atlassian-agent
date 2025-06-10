# 🚀 Guía de Instalación - Sistema de Autenticación Híbrido

## 📋 Prerrequisitos

### 🖥️ Servidor
- **OS**: Linux/Unix (Ubuntu 20.04+ recomendado)
- **Python**: 3.8 o superior
- **RAM**: Mínimo 2GB, recomendado 4GB
- **Disco**: Mínimo 5GB libres
- **Red**: Acceso a internet (para instalación de dependencias)

### 👤 Permisos
- Usuario con permisos `sudo` o acceso root
- Permisos de escritura en directorio de aplicación
- Puerto disponible (default: 8501)

## 📦 Instalación Paso a Paso

### 1️⃣ Preparar el Entorno

```bash
# Conectar al servidor
ssh usuario@servidor-interno

# Actualizar sistema
sudo apt update && sudo apt upgrade -y

# Instalar Python y dependencias del sistema
sudo apt install python3 python3-pip python3-venv git -y

# Verificar versión de Python
python3 --version  # Debe ser 3.8+
```

### 2️⃣ Clonar y Configurar el Proyecto

```bash
# Navegar al directorio de aplicaciones
cd /opt  # o el directorio que prefieras

# Clonar el repositorio (ajustar URL según tu repo)
sudo git clone <URL_DEL_REPOSITORIO> atlassian-agent
sudo chown -R $USER:$USER atlassian-agent

# Entrar al directorio
cd atlassian-agent
```

### 3️⃣ Configurar Entorno Virtual

```bash
# Crear entorno virtual
python3 -m venv .venv

# Activar entorno virtual
source .venv/bin/activate

# Actualizar pip
pip install --upgrade pip

# Instalar dependencias
pip install -r requirements.txt
```

### 4️⃣ Configurar Base de Datos

```bash
# Crear directorio para datos de Streamlit
mkdir -p .streamlit

# Verificar que la base de datos se crea correctamente
python3 -c "
from config.user_credentials_db import user_credentials_db
print('✅ Base de datos inicializada correctamente')
users = user_credentials_db.list_local_users()
print(f'👥 Usuarios locales: {len(users)}')
"
```

### 5️⃣ Crear Primer Usuario Administrador

```bash
# Script para crear usuario admin inicial
python3 -c "
from config.user_credentials_db import user_credentials_db

# Datos del primer admin (CAMBIAR ESTOS VALORES)
admin_email = 'admin@tuempresa.com'
admin_name = 'Administrador Principal' 
admin_password = 'TuPasswordSegura123'  # CAMBIAR ESTA CONTRASEÑA

# Crear usuario admin
result = user_credentials_db.create_local_user(
    user_email=admin_email,
    display_name=admin_name,
    password=admin_password,
    is_admin=True
)

if result:
    print(f'✅ Usuario administrador creado: {admin_email}')
    print('🔒 RECUERDA CAMBIAR LA CONTRASEÑA desde el panel de admin')
else:
    print('❌ Error creando usuario administrador')
"
```

### 6️⃣ Configurar Streamlit

```bash
# Crear archivo de configuración de Streamlit
cat > .streamlit/config.toml << 'EOF'
[server]
port = 8501
address = "0.0.0.0"
enableCORS = false
enableXsrfProtection = false

[browser]
gatherUsageStats = false

[theme]
primaryColor = "#1f77b4"
backgroundColor = "#ffffff"
secondaryBackgroundColor = "#f0f2f6"
textColor = "#262730"

[logger]
level = "info"
EOF
```

### 7️⃣ Configurar Variables de Entorno

```bash
# Crear archivo de variables de entorno
cat > .env << 'EOF'
# Configuración del sistema
ENVIRONMENT=production
SERVER_NAME=servidor-interno

# Configuración de logging (opcional - reemplazar con tus credenciales de Logfire)
# LOGFIRE_TOKEN=tu_token_de_logfire

# Configuración de autenticación
AUTH_SESSION_DURATION_HOURS=24
AUTH_REMEMBER_DURATION_DAYS=7
AUTH_MAX_FAILED_ATTEMPTS=5

# Base de datos
DATABASE_PATH=.streamlit/user_credentials.db
EOF
```

### 8️⃣ Crear Script de Inicio

```bash
# Crear script de inicio del servicio
cat > start_atlassian_agent.sh << 'EOF'
#!/bin/bash

# Configuración
PROJECT_DIR="/opt/atlassian-agent"  # Ajustar si usaste otro directorio
LOG_DIR="$PROJECT_DIR/logs"
PID_FILE="$PROJECT_DIR/atlassian_agent.pid"

# Crear directorio de logs
mkdir -p "$LOG_DIR"

# Función para iniciar el servicio
start_service() {
    echo "🚀 Iniciando Atlassian Agent..."
    
    cd "$PROJECT_DIR"
    source .venv/bin/activate
    
    # Verificar que el puerto esté libre
    if lsof -i :8501 > /dev/null 2>&1; then
        echo "❌ Puerto 8501 ya está en uso"
        exit 1
    fi
    
    # Iniciar Streamlit en background
    nohup streamlit run streamlit_app.py \
        --server.port 8501 \
        --server.address 0.0.0.0 \
        > "$LOG_DIR/app.log" 2>&1 &
    
    # Guardar PID
    echo $! > "$PID_FILE"
    
    echo "✅ Atlassian Agent iniciado"
    echo "🌐 Acceso: http://$(hostname -I | awk '{print $1}'):8501"
    echo "📋 Logs: $LOG_DIR/app.log"
    echo "🔧 PID: $(cat $PID_FILE)"
}

# Función para detener el servicio
stop_service() {
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        echo "🛑 Deteniendo Atlassian Agent (PID: $PID)..."
        kill $PID 2>/dev/null
        rm -f "$PID_FILE"
        echo "✅ Servicio detenido"
    else
        echo "⚠️ No se encontró archivo PID"
    fi
}

# Función para verificar estado
status_service() {
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if ps -p $PID > /dev/null 2>&1; then
            echo "✅ Atlassian Agent ejecutándose (PID: $PID)"
            echo "🌐 URL: http://$(hostname -I | awk '{print $1}'):8501"
        else
            echo "❌ Proceso no encontrado (PID obsoleto: $PID)"
            rm -f "$PID_FILE"
        fi
    else
        echo "❌ Atlassian Agent no está ejecutándose"
    fi
}

# Manejo de argumentos
case "$1" in
    start)
        start_service
        ;;
    stop)
        stop_service
        ;;
    restart)
        stop_service
        sleep 2
        start_service
        ;;
    status)
        status_service
        ;;
    *)
        echo "Uso: $0 {start|stop|restart|status}"
        exit 1
        ;;
esac
EOF

# Hacer ejecutable el script
chmod +x start_atlassian_agent.sh
```

### 9️⃣ Crear Servicio Systemd (Opcional)

```bash
# Crear archivo de servicio systemd para auto-inicio
sudo cat > /etc/systemd/system/atlassian-agent.service << 'EOF'
[Unit]
Description=Atlassian Agent Authentication System
After=network.target

[Service]
Type=forking
User=atlassian  # Cambiar por tu usuario
Group=atlassian # Cambiar por tu grupo
WorkingDirectory=/opt/atlassian-agent
Environment=PATH=/opt/atlassian-agent/.venv/bin
ExecStart=/opt/atlassian-agent/start_atlassian_agent.sh start
ExecStop=/opt/atlassian-agent/start_atlassian_agent.sh stop
ExecReload=/opt/atlassian-agent/start_atlassian_agent.sh restart
PIDFile=/opt/atlassian-agent/atlassian_agent.pid
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Recargar systemd y habilitar servicio
sudo systemctl daemon-reload
sudo systemctl enable atlassian-agent.service
```

## 🔧 Configuración del Firewall

```bash
# Si tienes UFW habilitado
sudo ufw allow 8501/tcp
sudo ufw reload

# Si tienes iptables
sudo iptables -A INPUT -p tcp --dport 8501 -j ACCEPT
sudo iptables-save > /etc/iptables/rules.v4  # En algunas distribuciones
```

## 🚀 Primer Arranque

### 1️⃣ Iniciar el Servicio

```bash
# Método 1: Con script manual
./start_atlassian_agent.sh start

# Método 2: Con systemd (si lo configuraste)
sudo systemctl start atlassian-agent

# Verificar estado
./start_atlassian_agent.sh status
```

### 2️⃣ Verificar Acceso

```bash
# Obtener IP del servidor
hostname -I

# El servicio estará disponible en:
# http://TU_IP_SERVIDOR:8501
```

### 3️⃣ Primera Configuración

1. **Acceder al sistema**: Abre navegador en `http://TU_IP_SERVIDOR:8501`
2. **Elegir autenticación local** en el selector
3. **Login con admin**: Usa las credenciales del usuario admin creado
4. **Acceder al panel de admin**: Elegir "Panel de Administración"
5. **Crear usuarios adicionales**: En la pestaña "Crear Usuario"
6. **Configurar credenciales Atlassian**: Para cada usuario

## 🔒 Configuración de Seguridad

### 1️⃣ Cambiar Contraseña del Admin

```bash
# Desde el panel de admin web:
# 1. Login como admin
# 2. Panel de Administración
# 3. Gestionar Usuarios
# 4. Buscar tu usuario admin
# 5. Resetear Password
```

### 2️⃣ Configurar HTTPS (Recomendado)

```bash
# Instalar nginx como proxy reverso
sudo apt install nginx -y

# Configurar nginx para HTTPS (requiere certificado SSL)
sudo cat > /etc/nginx/sites-available/atlassian-agent << 'EOF'
server {
    listen 80;
    server_name tu-servidor-interno.local;  # Cambiar por tu nombre
    
    location / {
        proxy_pass http://127.0.0.1:8501;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
EOF

# Habilitar sitio
sudo ln -s /etc/nginx/sites-available/atlassian-agent /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

## 📊 Verificación de Instalación

### ✅ Checklist Final

```bash
# 1. Verificar servicio activo
./start_atlassian_agent.sh status

# 2. Verificar base de datos
python3 -c "
from config.user_credentials_db import user_credentials_db
print('✅ BD activa:', len(user_credentials_db.list_local_users()), 'usuarios')
"

# 3. Verificar puerto
netstat -tlnp | grep :8501

# 4. Verificar logs
tail -f logs/app.log

# 5. Test de conectividad
curl -I http://localhost:8501
```

### 🐛 Troubleshooting Rápido

```bash
# Problema: Puerto ocupado
sudo lsof -i :8501
sudo kill -9 <PID>

# Problema: Permisos de base de datos
sudo chown -R $USER:$USER .streamlit/

# Problema: Dependencias faltantes
source .venv/bin/activate
pip install -r requirements.txt --force-reinstall

# Ver logs detallados
tail -f logs/app.log
```

## 🎯 Próximos Pasos

1. **Crear usuarios**: Usar panel de admin para agregar usuarios
2. **Configurar credenciales Atlassian**: Para cada usuario
3. **Backup**: Configurar respaldo de `.streamlit/user_credentials.db`
4. **Monitoreo**: Configurar Logfire (opcional)
5. **Documentar**: URLs y credenciales para tu equipo

---

## 📞 Soporte

- **Logs de aplicación**: `logs/app.log`
- **Configuración**: `.streamlit/config.toml`
- **Base de datos**: `.streamlit/user_credentials.db`
- **Variables de entorno**: `.env`

**⚠️ IMPORTANTE**: Hacer backup de la base de datos antes de actualizaciones mayores. 