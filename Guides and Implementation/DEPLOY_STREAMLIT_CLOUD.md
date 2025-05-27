# 🚀 Guía de Despliegue en Streamlit Community Cloud

## 📋 **Requisitos Previos**

1. ✅ Cuenta de GitHub con tu proyecto subido
2. ✅ Cuenta de Google Cloud Console (para OAuth2)
3. ✅ API Keys de OpenAI, Atlassian, etc.

## 🔧 **Paso 1: Preparar Google OAuth2**

### 1.1 Configurar Google Cloud Console
1. Ve a [Google Cloud Console](https://console.cloud.google.com/)
2. Crea un nuevo proyecto o selecciona uno existente
3. Habilita la **Google+ API**
4. Ve a **Credenciales** → **Crear credenciales** → **ID de cliente OAuth 2.0**
5. Tipo de aplicación: **Aplicación web**
6. **URIs de redirección autorizados**: `https://TU-APP.streamlit.app/oauth2callback`
   - ⚠️ **IMPORTANTE**: Cambiarás esta URL después del despliegue

### 1.2 Obtener credenciales
- Guarda el **Client ID** y **Client Secret**

## 🌐 **Paso 2: Desplegar en Streamlit Cloud**

### 2.1 Acceder a Streamlit Cloud
1. Ve a [share.streamlit.io](https://share.streamlit.io)
2. Inicia sesión con GitHub
3. Haz clic en **"New app"**

### 2.2 Configurar la aplicación
- **Repository**: `tu-usuario/atlassian-agent`
- **Branch**: `main`
- **Main file path**: `streamlit_app.py`
- **App URL**: Personaliza el nombre (ej: `atlassian-agent-tuempresa`)

### 2.3 Tu URL final será:
```
https://atlassian-agent-tuempresa-tu-usuario.streamlit.app
```

## 🔐 **Paso 3: Configurar Secretos**

### 3.1 En la interfaz de Streamlit Cloud
1. Ve a tu app desplegada
2. Haz clic en **"Settings"** → **"Secrets"**
3. Copia y pega la configuración de `.streamlit/secrets.toml.example`
4. **Completa todos los valores**:

```toml
[auth]
redirect_uri = "https://TU-URL-REAL.streamlit.app/oauth2callback"
cookie_secret = "GENERAR_32_CARACTERES_ALEATORIOS"
client_id = "TU_GOOGLE_CLIENT_ID"
client_secret = "TU_GOOGLE_CLIENT_SECRET"
server_metadata_url = "https://accounts.google.com/.well-known/openid-configuration"

OPENAI_API_KEY = "sk-..."
ATLASSIAN_URL = "https://tu-dominio.atlassian.net"
ATLASSIAN_USERNAME = "tu-email@empresa.com"
ATLASSIAN_API_TOKEN = "tu_token"
TIMEZONE = "Europe/Madrid"

# Opcionales
LOGFIRE_TOKEN = "tu_logfire_token"
MEM0_API_KEY = "tu_mem0_key"
```

### 3.2 Actualizar Google OAuth2
1. Vuelve a Google Cloud Console
2. Edita tu **ID de cliente OAuth 2.0**
3. **Actualiza la URI de redirección** con tu URL real de Streamlit
4. Guarda los cambios

## ✅ **Paso 4: Verificar el Despliegue**

### 4.1 Comprobar que funciona
1. Visita tu URL de Streamlit Cloud
2. Debería aparecer el botón de "Iniciar Sesión con Google"
3. Prueba el login
4. Verifica que puedes interactuar con Jira/Confluence

### 4.2 Si hay errores
- Revisa los **logs** en Streamlit Cloud
- Verifica que todos los secretos estén configurados
- Comprueba que las URLs de OAuth2 coincidan

## 🔧 **Comandos Útiles**

### Generar cookie secret aleatorio:
```python
import secrets
print(secrets.token_urlsafe(32))
```

### Verificar configuración local:
```bash
streamlit run streamlit_app.py
```

## 🎯 **URLs Importantes**

- **Tu app**: `https://TU-APP.streamlit.app`
- **Streamlit Cloud**: [share.streamlit.io](https://share.streamlit.io)
- **Google Cloud Console**: [console.cloud.google.com](https://console.cloud.google.com)

## 🆘 **Solución de Problemas**

### Error de OAuth2
- Verifica que las URLs de redirección coincidan exactamente
- Asegúrate de que Google+ API esté habilitada

### Error de importación
- Verifica que `requirements.txt` esté actualizado
- Comprueba que `streamlit_app.py` esté en la raíz

### Error de API Keys
- Verifica que todas las variables estén en "Secrets"
- Comprueba que no haya espacios extra en los valores

---

🎉 **¡Listo!** Tu agente Atlassian estará disponible públicamente en tu URL de Streamlit Cloud. 