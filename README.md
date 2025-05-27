# 🤖 Agente Conversacional Jira/Confluence

Este proyecto implementa un agente conversacional construido con PydanticAI para interactuar con Jira y Confluence utilizando lenguaje natural. La interfaz de usuario se desarrolla con Streamlit y la observabilidad se gestiona con Logfire.

**🆕 NUEVO: Ahora con autenticación multi-usuario y memoria personalizada por usuario.**

## ✨ Características
- 🔍 **Consultar issues de Jira** (búsqueda, detalles)
- ✏️ **Crear y modificar issues en Jira** (crear, comentar)
- 📖 **Buscar y leer páginas de Confluence**
- 📝 **Crear y modificar páginas en Confluence**
- 💬 **Interfaz de chat amigable**
- 🔐 **Autenticación multi-usuario con Google OAuth2**
- 🧠 **Memoria personalizada por usuario con Mem0**
- 🔄 **Preparado para comunicación A2A**

## Stack Tecnológico
- Python 3.10+
- PydanticAI
- Streamlit
- atlassian-python-api
- Logfire
- uv (para gestión de dependencias y entorno)

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
python generate_cookie_secret.py

# Copia el template de configuración
cp .streamlit/secrets.toml.template .streamlit/secrets.toml

# Edita con tus credenciales de Google OAuth2
nano .streamlit/secrets.toml
```

📖 **Para configurar Google OAuth2:** Lee `SETUP_OAUTH.md`

### 3. Variables de entorno
Crea un archivo `.env` en la raíz del proyecto, basándote en `.env.example`, y completa tus credenciales:
```bash
# APIs
MEM0_API_KEY=tu_mem0_api_key
OPENAI_API_KEY=tu_openai_api_key

# Atlassian
JIRA_URL=https://tu-empresa.atlassian.net
CONFLUENCE_URL=https://tu-empresa.atlassian.net/wiki
ATLASSIAN_EMAIL=tu-email@empresa.com
ATLASSIAN_API_TOKEN=tu_api_token
```

### 4. Verificar configuración
```bash
python verify_auth_setup.py
```

## Configuración de Zona Horaria

El agente utiliza la variable de entorno `TIMEZONE` para determinar la zona horaria local al devolver la fecha y hora actual.

- **Formato:** Debe ser una zona horaria IANA válida, por ejemplo: `America/Buenos_Aires`, `Europe/Madrid`, `UTC`.
- **Ejemplo en `.env`:**
  ```
  TIMEZONE=America/Buenos_Aires
  ```
- **Fallback:** Si la variable no está definida o es inválida, el agente usará UTC por defecto.

Esto permite que todas las herramientas que dependan de la hora local sean consistentes y fácilmente configurables.

## Ejecución
Para iniciar la aplicación Streamlit:
```bash
streamlit run ui/app.py
