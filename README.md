# 🤖 Agente Conversacional Jira/Confluence

Este proyecto implementa un agente conversacional avanzado construido con **PydanticAI** para interactuar con Jira y Confluence utilizando lenguaje natural. La interfaz de usuario se desarrolla con **Streamlit** y incluye autenticación multi-usuario, memoria personalizada y observabilidad completa.

**🆕 NUEVO: Ahora con autenticación multi-usuario, memoria personalizada por usuario y capacidades avanzadas de gestión de sprints y workflows.**

## ✨ Características Principales

### 🔍 **Jira - Gestión de Issues**
- **Búsqueda avanzada**: Consultas JQL personalizadas y búsqueda por texto
- **Detalles completos**: Información detallada de issues incluyendo story points
- **Gestión de comentarios**: Agregar comentarios con formato rico
- **Registro de tiempo**: Worklog con soporte para formatos flexibles (horas, minutos, segundos)
- **Análisis de tiempo**: Reportes detallados de horas trabajadas por usuario y issue
- **Gestión de usuarios**: Búsqueda, validación y gestión de asignaciones

### 🏃‍♂️ **Jira - Gestión de Sprints**
- **Sprint activo**: Consultar issues del sprint en curso
- **Progreso de sprint**: Análisis de avance con story points y porcentajes
- **Mi trabajo actual**: Vista personalizada del trabajo asignado en el sprint
- **Issues hijo**: Análisis de dependencias y subtareas

### 🔄 **Jira - Workflows y Transiciones**
- **Estados disponibles**: Consultar todos los estados del proyecto
- **Transiciones permitidas**: Ver qué transiciones están disponibles para cada issue
- **Cambio de estado**: Ejecutar transiciones con comentarios y campos adicionales
- **Gestión de workflows**: Información completa del flujo de trabajo del proyecto

### 📖 **Confluence - Gestión de Contenido**
- **Búsqueda inteligente**: Búsqueda por texto libre o consultas CQL avanzadas
- **Lectura de páginas**: Contenido completo con metadatos y enlaces
- **Creación de páginas**: Crear nuevas páginas con contenido en formato XHTML
- **Actualización de contenido**: Modificar páginas existentes con versionado
- **Gestión de espacios**: Trabajo con múltiples espacios de Confluence

### 🧠 **Memoria Personalizada (Mem0)**
- **Aliases inteligentes**: Guardar atajos personalizados para issues, proyectos, usuarios
- **Búsqueda semántica**: Encontrar información guardada usando lenguaje natural
- **Contexto por usuario**: Memoria completamente aislada por usuario autenticado
- **Tipos de memoria**: Categorización flexible (jira_alias, soporte, cliente, etc.)
- **Precargar contexto**: Memoria completa disponible para el agente

### 🔐 **Autenticación y Seguridad (NUEVO SISTEMA HÍBRIDO)**
- **Autenticación híbrida**: Google OAuth2 + Autenticación local
- **Servidores internos**: Soporte completo para servidores sin dominio público
- **Panel de administración**: Gestión completa de usuarios y permisos
- **Credenciales cifradas**: API keys de Atlassian cifradas por usuario
- **Base de datos segura**: SQLite con 3 tablas para máxima seguridad
- **Sesiones avanzadas**: Control de expiración y "recordar sesión"
- **Auditoría completa**: Logs de todas las acciones con Logfire

### 📊 **Observabilidad y Logging**
- **Logfire integrado**: Observabilidad completa con trazas distribuidas
- **Logging contextual**: Información detallada por usuario y operación
- **Instrumentación automática**: Monitoreo de PydanticAI y HTTP
- **Status tracker**: Seguimiento en tiempo real del estado del agente

### ⏰ **Utilidades de Tiempo**
- **Zona horaria configurable**: Soporte para diferentes zonas horarias
- **Fecha/hora actual**: Contexto temporal para todas las operaciones
- **Parsing inteligente**: Interpretación flexible de formatos de tiempo

## 🛠️ Stack Tecnológico

- **Python 3.10+** - Lenguaje base
- **PydanticAI** - Framework de agentes conversacionales
- **Streamlit** - Interfaz de usuario web
- **atlassian-python-api** - Integración con Jira/Confluence
- **Logfire** - Observabilidad y monitoreo
- **Mem0** - Sistema de memoria personalizada
- **Google OAuth2** - Autenticación segura
- **uv** - Gestión de dependencias y entorno

## 📚 Documentación Completa

### 🔐 Sistema de Autenticación Híbrido
- **[📋 Documentación Técnica](docs/AUTHENTICATION_SYSTEM.md)** - Arquitectura y características del sistema
- **[🚀 Guía de Instalación](docs/INSTALLATION.md)** - Instalación paso a paso en servidor interno
- **[👑 Manual del Administrador](docs/ADMIN_GUIDE.md)** - Gestión de usuarios y sistema
- **[🛠️ Troubleshooting](docs/TROUBLESHOOTING.md)** - Resolución de problemas comunes

### 🎯 Características del Sistema Híbrido
- ✅ **Google OAuth2**: Para servidores con dominio público y HTTPS
- ✅ **Autenticación Local**: Para servidores internos corporativos
- ✅ **Panel de Administración**: Gestión completa de usuarios y permisos
- ✅ **Seguridad Avanzada**: Hash bcrypt, sesiones seguras, auditoría completa
- ✅ **Escalabilidad**: De 4 usuarios actuales a 50+ usuarios potenciales
- ✅ **100% Retrocompatible**: Sin pérdida de datos existentes

## 🚀 Configuración

### 1. Instalación básica
```bash
# Clona el repositorio
git clone <tu-repo>
cd agente-atlassian

# Crea un entorno virtual e instala las dependencias
uv venv
uv pip install -e .[dev]
# o si solo quieres las dependencias de producción:
# uv pip install -e .
```

### 2. Configuración de autenticación (NUEVO)
```bash
# Genera un cookie secret seguro
python config/generate_cookie_secret.py

# Copia el template de configuración
cp .streamlit/secrets.toml.template .streamlit/secrets.toml

# Edita con tus credenciales de Google OAuth2
nano .streamlit/secrets.toml
```

📖 **Para configurar Google OAuth2:** Lee `Guides and Implementation/SETUP_OAUTH.md`

### 3. Variables de entorno
Crea un archivo `.env` en la raíz del proyecto, basándote en `.env.example`, y completa tus credenciales:
```bash
# APIs de IA y Memoria
MEM0_API_KEY=tu_mem0_api_key
OPENAI_API_KEY=tu_openai_api_key

# Atlassian (configuración base)
JIRA_URL=https://tu-empresa.atlassian.net
CONFLUENCE_URL=https://tu-empresa.atlassian.net/wiki
ATLASSIAN_EMAIL=tu-email@empresa.com
ATLASSIAN_API_TOKEN=tu_api_token

# Observabilidad (opcional)
LOGFIRE_TOKEN=tu_logfire_token

# Zona horaria (opcional)
TIMEZONE=America/Buenos_Aires
```

### 4. Verificar configuración
```bash
python verify_auth_setup.py
```

## ⚡ Funcionalidades Detalladas

### 🎯 **Comandos de Jira**

**Búsqueda y Consultas:**
- `"Busca issues del proyecto PROJ con estado abierto"`
- `"Muéstrame los issues asignados a Juan"`
- `"¿Cuáles son los bugs críticos pendientes?"`

**Gestión de Tiempo:**
- `"Registra 2 horas de trabajo en PROJ-123"`
- `"¿Cuántas horas trabajó María en la historia PROJ-456?"`
- `"Muestra el reporte de horas del issue PROJ-789"`

**Sprints y Planificación:**
- `"¿Cómo va el progreso del sprint actual?"`
- `"Muestra mi trabajo pendiente en el sprint"`
- `"¿Cuántos story points quedan por completar?"`

**Workflows y Estados:**
- `"¿A qué estados puedo mover el issue PROJ-123?"`
- `"Cambia PROJ-456 a 'En Progreso' con comentario"`
- `"Muestra todos los estados disponibles del proyecto"`

### 📝 **Comandos de Confluence**

**Búsqueda de Contenido:**
- `"Busca páginas sobre 'API documentation' en el espacio DOCS"`
- `"Encuentra la página de configuración del servidor"`
- `"¿Qué documentos hay sobre el proceso de deployment?"`

**Gestión de Páginas:**
- `"Crea una página llamada 'Guía de Usuario' en el espacio DOCS"`
- `"Actualiza la página ID 123456 con nuevo contenido"`
- `"Lee el contenido completo de la página de arquitectura"`

### 🧠 **Comandos de Memoria**

**Guardar Información:**
- `"Recuerda que 'mi proyecto' es PROJ"`
- `"Guarda que Juan Pérez es 'juan.perez@empresa.com'"`
- `"Alias 'servidor prod' para SRV-001"`

**Recuperar Información:**
- `"¿Cuál es mi proyecto?"`
- `"Busca información sobre configuración de servidor"`
- `"¿Qué aliases tengo guardados para usuarios?"`

## 🏗️ Arquitectura del Sistema

```
📁 Proyecto/
├── 🤖 agent_core/          # Core del agente PydanticAI
│   ├── main_agent.py       # Agente principal
│   ├── jira_instances.py   # Clientes Jira
│   ├── confluence_instances.py # Clientes Confluence
│   └── output_models.py    # Modelos de respuesta
├── 🛠️ tools/              # Herramientas del agente
│   ├── jira_tools.py       # 20+ funciones de Jira
│   ├── confluence_tools.py # Funciones de Confluence
│   ├── mem0_tools.py       # Sistema de memoria
│   ├── time_tools.py       # Utilidades de tiempo
│   └── formatting_tools.py # Formateo de respuestas
├── 🖥️ ui/                 # Interfaz Streamlit
│   ├── app.py              # Aplicación principal
│   ├── agent_wrapper.py    # Wrapper del agente
│   ├── agent_status_tracker.py # Tracking de estado
│   └── custom_styles.py    # Estilos personalizados
├── ⚙️ config/             # Configuración del sistema
│   ├── settings.py         # Configuración general
│   ├── encryption.py       # Cifrado de credenciales
│   ├── user_credentials_db.py # BD de usuarios
│   └── logging_context.py  # Sistema de logging
└── 📚 tests/              # Tests automatizados
```

## 🔧 Configuración de Zona Horaria

El agente utiliza la variable de entorno `TIMEZONE` para determinar la zona horaria local:

- **Formato:** Zona horaria IANA válida (ej: `America/Buenos_Aires`, `Europe/Madrid`, `UTC`)
- **Ejemplo en `.env`:**
  ```
  TIMEZONE=America/Buenos_Aires
  ```
- **Fallback:** Si no está definida o es inválida, usa UTC por defecto

## 🚀 Ejecución

### Desarrollo Local
```bash
streamlit run ui/app.py
```

### Producción
```bash
# Con variables de entorno
STREAMLIT_SERVER_PORT=8501 streamlit run ui/app.py

# O usando el archivo principal
python streamlit_app.py
```

## 🧪 Testing

```bash
# Ejecutar todos los tests
pytest

# Tests específicos
pytest tests/test_jira_tools.py
pytest tests/test_confluence_tools.py

# Tests con logging detallado
pytest -v -s
```

## 📈 Observabilidad

### Logfire (Recomendado)
1. Obtén tu token en [logfire.pydantic.dev](https://logfire.pydantic.dev)
2. Configura `LOGFIRE_TOKEN` en tu `.env`
3. Visualiza trazas en tiempo real en el dashboard

### Logs Locales
Los logs se almacenan automáticamente con contexto de usuario y operación.

## 🔒 Seguridad

- **Cifrado**: Todas las API keys se cifran antes del almacenamiento
- **Aislamiento**: Cada usuario tiene credenciales y memoria separadas
- **Autenticación**: OAuth2 con Google para acceso seguro
- **No logging**: Las credenciales nunca se registran en logs

## 🤝 Contribuir

1. Fork el proyecto
2. Crea una rama feature (`git checkout -b feature/nueva-funcionalidad`)
3. Commit tus cambios (`git commit -am 'Agrega nueva funcionalidad'`)
4. Push a la rama (`git push origin feature/nueva-funcionalidad`)
5. Abre un Pull Request

## 📄 Licencia

Este proyecto está bajo la Licencia MIT. Ver el archivo `LICENSE` para más detalles.

## 🆘 Soporte

- 📖 **Documentación**: Revisa los archivos en `Guides and Implementation/`
- 🐛 **Issues**: Reporta problemas en GitHub Issues
- 💬 **Discusiones**: Únete a las GitHub Discussions

---

**Desarrollado con ❤️ usando PydanticAI, Streamlit y las mejores prácticas de desarrollo de agentes conversacionales.**

## 🚀 Inicio Rápido

### Ejecutar la aplicación

### Opciones para ejecutar la aplicación:

```bash
# ✅ OPCIÓN 1 - Ejecutar directamente (Recomendado)
streamlit run ui/app.py

# ✅ OPCIÓN 2 - Usar el wrapper (Para Streamlit Cloud)
streamlit run streamlit_app.py
```

**Ambas opciones funcionan correctamente** - `streamlit_app.py` ahora ejecuta `ui/app.py` automáticamente.

### Configuración inicial

1. **Instalar dependencias:**
```bash
pip install -r requirements.txt
```

2. **Crear usuario administrador:**
```bash
python create_admin_user.py
```

3. **Configurar variables de entorno:**
   - Copia `.env.example` a `.env`
   - Configura tus API keys de OpenAI/Anthropic
   - Configura Mem0 para memoria persistente (opcional)

4. **Ejecutar la aplicación:**
```bash
streamlit run ui/app.py
```

## 📁 Estructura de archivos importantes

- `ui/app.py` - **Aplicación principal** (2163 líneas)
- `streamlit_app.py` - Proxy para Streamlit Cloud (solo 11 líneas)
- `agent_core/main_agent.py` - Configuración del agente PydanticAI
- `tools/` - Herramientas para Jira, Confluence y Mem0
- `config/` - Configuración, autenticación y base de datos

## 🔧 Troubleshooting

### Pantalla negra o interfaz vacía
Si ves una pantalla negra al usar el chat, verifica que estés ejecutando:
```bash
streamlit run ui/app.py  # NO streamlit_app.py
```

### Problemas de importación
Si hay errores de `No module named 'mem0'`:
```bash
pip install mem0ai
```

## 🌐 Acceso

- **Local**: http://localhost:8501
- **Red**: http://TU_IP:8501

## 📝 Características

- ✅ Autenticación local con usuarios y sesiones
- ✅ Panel de administración
- ✅ Integración completa con Jira y Confluence
- ✅ Memoria persistente con Mem0
- ✅ Logging avanzado con Logfire
- ✅ Interfaz responsive y moderna
- ✅ Manejo robusto de credenciales cifradas

## 🔐 Seguridad

- Credenciales cifradas en base de datos SQLite
- Sesiones de usuario con expiración
- Logging de auditoría completo
- Validación de permisos por usuario

---

**¿Problemas?** Revisa que estés usando `streamlit run ui/app.py` y no `streamlit_app.py`.
