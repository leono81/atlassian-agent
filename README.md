# 🤖 Agente Conversacional Jira/Confluence

Un agente conversacional avanzado construido con **PydanticAI** para interactuar con Jira y Confluence utilizando lenguaje natural. Con interfaz **Streamlit**, autenticación multi-usuario, memoria personalizada y observabilidad completa.

**🆕 NUEVO: Autenticación multi-usuario, memoria personalizada y manejo robusto de fechas/zonas horarias.**

## 🚀 Inicio Rápido

### 1. Instalación
```bash
# Clona el repositorio
git clone <tu-repo>
cd agente-atlassian

# Instala las dependencias
pip install -r requirements.txt
```

### 2. Configuración Básica
```bash
# 1. Configura las variables de entorno (ver CONFIG_ENV_TEMPLATE.md)
# Crea archivo .env basándote en el template
nano .env

# 2. Crea un usuario administrador
python create_admin_user.py

# 3. Ejecuta la aplicación
streamlit run ui/app.py
```

### 3. Acceso
- **Local**: http://localhost:8501
- **Red**: http://TU_IP:8501

## ⚙️ Variables de Entorno

Crea un archivo `.env` en la raíz del proyecto con las siguientes variables:

### 🔑 **Variables Obligatorias**
```bash
# AI y Memoria (al menos una API de IA es obligatoria)
OPENAI_API_KEY=tu_openai_api_key              # Para GPT models
# O alternativamente:
ANTHROPIC_API_KEY=tu_anthropic_api_key        # Para Claude models

# Memoria Personalizada (recomendado)
MEM0_API_KEY=tu_mem0_api_key                  # Para memoria persistente

# Observabilidad (opcional pero recomendado)
LOGFIRE_TOKEN=tu_logfire_token                # Para monitoring y logs
```

### 🏢 **Variables de Atlassian (Opcionales)**
```bash
# Configuración por defecto (usuarios pueden configurar sus propias credenciales)
JIRA_URL=https://tu-empresa.atlassian.net
CONFLUENCE_URL=https://tu-empresa.atlassian.net/wiki
ATLASSIAN_EMAIL=tu-email@empresa.com
ATLASSIAN_API_TOKEN=tu_api_token
```

### 🌍 **Variables de Sistema**
```bash
# Zona Horaria (importante para worklog correcto)
TIMEZONE=America/Buenos_Aires                 # Zona horaria IANA válida

# Modelo de IA (opcional)
PYDANTIC_AI_MODEL=openai:gpt-4o-mini         # Modelo por defecto
```

### 📝 **Notas sobre Variables**
- **Sin variables de Atlassian**: Los usuarios deben configurar sus credenciales en la interfaz
- **TIMEZONE**: Crítico para el correcto manejo de fechas en worklogs
- **Mem0**: Sin esta API key, la memoria no será persistente entre sesiones
- **Logfire**: Sin este token, los logs solo serán locales

## ✨ Características Principales

### 🔍 **Jira - Gestión Completa**
- **Búsqueda avanzada** con JQL y texto libre
- **Gestión de issues** con detalles completos y story points
- **Registro de tiempo** con manejo robusto de fechas y zonas horarias
- **Análisis de worklogs** por usuario e issue
- **Gestión de sprints** con progreso y métricas
- **Workflows y transiciones** de estado
- **Gestión de usuarios** y asignaciones

### 📖 **Confluence - Gestión de Contenido**
- **Búsqueda inteligente** con CQL y texto libre
- **Lectura y creación** de páginas con formato XHTML
- **Actualización de contenido** con versionado
- **Gestión de espacios** múltiples

### 🧠 **Memoria Personalizada (Mem0)**
- **Aliases inteligentes** para issues, proyectos y usuarios
- **Búsqueda semántica** de información guardada
- **Contexto por usuario** completamente aislado
- **Categorización flexible** de tipos de memoria

### 🔐 **Sistema de Autenticación**
- **Autenticación local** con usuarios y contraseñas
- **Panel de administración** para gestión de usuarios
- **Credenciales cifradas** por usuario
- **Sesiones seguras** con expiración configurable

## 🛠️ Arquitectura del Sistema

```
📁 agente-atlassian/
├── 🤖 agent_core/          # Core del agente PydanticAI
│   ├── main_agent.py       # Agente principal con 25+ tools
│   ├── jira_instances.py   # Clientes Jira con credenciales por usuario
│   └── confluence_instances.py # Clientes Confluence
├── 🛠️ tools/              # Herramientas especializadas
│   ├── jira_tools.py       # 20+ funciones de Jira
│   ├── confluence_tools.py # Funciones de Confluence
│   ├── mem0_tools.py       # Sistema de memoria
│   └── time_tools.py       # Utilidades de tiempo y fechas
├── 🖥️ ui/                 # Interfaz Streamlit
│   ├── app.py              # Aplicación principal (USAR ESTE)
│   └── agent_wrapper.py    # Wrapper del agente
├── ⚙️ config/             # Configuración del sistema
│   ├── settings.py         # Configuración + utils de fechas
│   ├── user_credentials_db.py # Base de datos de usuarios
│   └── encryption.py       # Cifrado de credenciales
└── 📚 docs/               # Documentación detallada
```

## 🔧 Manejo de Fechas y Zonas Horarias

**IMPORTANTE**: El agente incluye un sistema robusto de manejo de fechas que resuelve problemas comunes de zona horaria.

### Configuración
```bash
# En tu archivo .env
TIMEZONE=America/Buenos_Aires  # Tu zona horaria local
```

### Funcionalidad
- ✅ **Parsing automático** de múltiples formatos de fecha
- ✅ **Conversión de zonas horarias** automática
- ✅ **Compatibilidad** entre entornos locales y servidores
- ✅ **Fallbacks inteligentes** en caso de errores

### Formatos Soportados
- `2025-06-12T12:00:00-03:00` (ISO con zona horaria)
- `2025-06-12T00:00:00.000+0000` (UTC con milisegundos)
- `2024-07-30T14:30:00Z` (UTC con Z)
- `ahora` o `None` (fecha/hora actual)

## 🎯 Comandos Principales

### 📊 **Jira - Worklog y Tiempo**
```
"Registra 2 horas de trabajo en PROJ-123"
"¿Cuántas horas trabajó María en PROJ-456?"
"Muestra el reporte de horas del issue PROJ-789"
"Registra 30 minutos en PROJ-123 iniciado ayer a las 14:00"
```

### 🔍 **Jira - Búsqueda y Gestión**
```
"Busca issues del proyecto PROJ con estado abierto"
"¿Cuáles son los bugs críticos pendientes?"
"Cambia PROJ-456 a 'En Progreso' con comentario"
"¿Cómo va el progreso del sprint actual?"
```

### 📝 **Confluence**
```
"Busca documentación sobre APIs en el espacio DOCS"
"Crea una página 'Guía de Usuario' en DOCS"
"Actualiza la página ID 123456 con nuevo contenido"
```

### 🧠 **Memoria Personalizada**
```
"Recuerda que 'mi proyecto' es PROJ-123"
"¿Cuál es mi proyecto?"
"Guarda que Juan Pérez es juan.perez@empresa.com"
```

## 🚀 Ejecución

### ✅ **Opción Recomendada**
```bash
streamlit run ui/app.py
```

### ⚠️ **Para Streamlit Cloud**
```bash
streamlit run streamlit_app.py  # Solo en Streamlit Cloud
```

### 🔧 **Con Configuración Personalizada**
```bash
# Puerto personalizado
STREAMLIT_SERVER_PORT=8502 streamlit run ui/app.py

# Con logging detallado
LOGFIRE_TOKEN=tu_token streamlit run ui/app.py
```

## 🧪 Testing y Verificación

### Verificar Configuración
```bash
# Verifica que la configuración sea correcta
python config/settings.py

# Crear usuario administrador
python create_admin_user.py

# Tests básicos (si están disponibles)
pytest tests/ -v
```

### Verificar Funcionalidades
1. **Autenticación**: Crear usuario y hacer login
2. **Jira**: Buscar un issue conocido
3. **Memoria**: Guardar y recuperar un alias
4. **Fechas**: Registrar tiempo en un issue

## 🔒 Seguridad

- **🔐 Cifrado**: Todas las API keys se cifran antes del almacenamiento
- **👤 Aislamiento**: Cada usuario tiene credenciales y memoria separadas  
- **🚫 Sin logging**: Las credenciales nunca se registran en logs
- **⏰ Sesiones**: Control de expiración y renovación automática
- **🛡️ Validación**: Sanitización de inputs y validación de permisos

## 📊 Observabilidad

### Con Logfire (Recomendado)
1. Obtén tu token en [logfire.pydantic.dev](https://logfire.pydantic.dev)
2. Configura `LOGFIRE_TOKEN` en tu `.env`
3. Visualiza trazas en tiempo real en el dashboard

### Logs Locales
- Logs estructurados con contexto de usuario
- Trazas de operaciones de Jira/Confluence
- Monitoreo de estado del agente

## ⚠️ Troubleshooting

### 🖥️ **Pantalla Negra o Vacía**
```bash
# SOLUCIÓN: Usa el archivo correcto
streamlit run ui/app.py  # ✅ CORRECTO
# NO: streamlit run streamlit_app.py  # ❌ Solo para Streamlit Cloud
```

### 🔑 **Error de API Keys**
```bash
# Verifica que las variables estén configuradas
python -c "import os; print('OPENAI_KEY:', bool(os.getenv('OPENAI_API_KEY')))"
```

### 🌍 **Problemas de Fecha/Zona Horaria**
```bash
# Verifica la configuración de timezone
python -c "from config.settings import get_timezone; print(get_timezone())"
```

### 📚 **Más Troubleshooting**
Ver `docs/TROUBLESHOOTING.md` para problemas específicos.

## 📚 Documentación Adicional

- **[🔐 Sistema de Autenticación](docs/AUTHENTICATION_SYSTEM.md)** - Arquitectura detallada
- **[🚀 Guía de Instalación](docs/INSTALLATION.md)** - Instalación en servidor
- **[👑 Manual del Administrador](docs/ADMIN_GUIDE.md)** - Gestión de usuarios
- **[🔧 Troubleshooting](docs/TROUBLESHOOTING.md)** - Resolución de problemas
- **[🧠 Sistema de Memoria](docs/MULTIUSER_MEMORY_SOLUTION.md)** - Memoria personalizada

## 🤝 Contribuir

1. Fork el proyecto
2. Crea una rama feature (`git checkout -b feature/nueva-funcionalidad`)
3. Commit tus cambios (`git commit -am 'Agrega nueva funcionalidad'`)
4. Push a la rama (`git push origin feature/nueva-funcionalidad`)
5. Abre un Pull Request

## 📄 Licencia

Este proyecto está bajo la Licencia MIT.

---

**Desarrollado con ❤️ usando PydanticAI, Streamlit y las mejores prácticas de desarrollo de agentes conversacionales.**
