# 🔐 Configuración de Google OAuth2 para Streamlit

## Paso 1: Crear proyecto en Google Cloud Console

1. Ve a [Google Cloud Console](https://console.cloud.google.com/)
2. Crea un nuevo proyecto o selecciona uno existente
3. Habilita la **Google+ API** y **Google Identity API**

## Paso 2: Configurar OAuth2 Consent Screen

1. Ve a **APIs & Services** > **OAuth consent screen**
2. Selecciona **External** (para usuarios fuera de tu organización)
3. Completa la información básica:
   - **App name**: "Atlassian Agent"
   - **User support email**: tu email
   - **Developer contact information**: tu email
4. En **Scopes**, agrega:
   - `openid`
   - `profile` 
   - `email`
5. Guarda y continúa

## Paso 3: Crear credenciales OAuth2

1. Ve a **APIs & Services** > **Credentials**
2. Clic en **+ CREATE CREDENTIALS** > **OAuth 2.0 Client IDs**
3. Selecciona **Web application**
4. Configura:
   - **Name**: "Streamlit Auth Client"
   - **Authorized JavaScript origins**: 
     - `http://localhost:8501` (para desarrollo)
     - `https://tu-dominio.com` (para producción)
   - **Authorized redirect URIs**:
     - `http://localhost:8501/oauth2callback` (para desarrollo)
     - `https://tu-dominio.com/oauth2callback` (para producción)

## Paso 4: Obtener credenciales

Después de crear el cliente OAuth2, obtendrás:
- **Client ID**: `123456789-abcdef.apps.googleusercontent.com`
- **Client Secret**: `GOCSPX-abcdef123456`

## Paso 5: Configurar secrets.toml

Crea/actualiza el archivo `.streamlit/secrets.toml`:

```toml
[auth]
redirect_uri = "http://localhost:8501/oauth2callback"
cookie_secret = "GENERA_UN_SECRET_ALEATORIO_AQUI_32_CARACTERES"
client_id = "TU_GOOGLE_CLIENT_ID"
client_secret = "TU_GOOGLE_CLIENT_SECRET"
server_metadata_url = "https://accounts.google.com/.well-known/openid-configuration"
```

## Paso 6: Generar cookie_secret

Ejecuta este comando en Python para generar un secret seguro:

```python
import secrets
print(secrets.token_urlsafe(32))
```

## ⚠️ IMPORTANTE

- **NUNCA** subas `secrets.toml` a git
- Agrega `.streamlit/secrets.toml` a tu `.gitignore`
- Para producción, usa variables de entorno en lugar de `secrets.toml`

## 🔄 Para producción (Streamlit Cloud)

En Streamlit Cloud, agrega estos secrets en la configuración:

```
[auth]
redirect_uri = "https://tu-app.streamlit.app/oauth2callback"
cookie_secret = "tu_secret_de_produccion"
client_id = "tu_client_id"
client_secret = "tu_client_secret"
server_metadata_url = "https://accounts.google.com/.well-known/openid-configuration"
``` 