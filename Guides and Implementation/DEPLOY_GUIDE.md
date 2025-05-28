# 🚀 Guía de Despliegue en Streamlit Community Cloud

## ❗ **SOLUCIÓN AL ERROR ACTUAL**

El error que estás viendo se debe a que **Streamlit Cloud no puede encontrar la `OPENAI_API_KEY`**. Aquí está la solución:

### 🔧 **Paso 1: Configurar Secrets en Streamlit Cloud**

1. **Ve a tu app**: https://share.streamlit.io/
2. **Encuentra tu app** "atlassian-agent" 
3. **Haz clic en los 3 puntos** → **Settings**
4. **Ve a la pestaña "Secrets"**
5. **Agrega estos secrets** (copia y pega, reemplazando los valores):

```toml
# === OPENAI API (REQUERIDO) ===
OPENAI_API_KEY = "sk-tu-api-key-real-aqui"

# === CONFIGURACIÓN JIRA ===
JIRA_URL = "https://tu-empresa.atlassian.net"
JIRA_USERNAME = "tu-email@empresa.com"
JIRA_API_TOKEN = "tu_jira_api_token_real"

# === CONFIGURACIÓN CONFLUENCE ===
CONFLUENCE_URL = "https://tu-empresa.atlassian.net/wiki"
CONFLUENCE_USERNAME = "tu-email@empresa.com"
CONFLUENCE_API_TOKEN = "tu_confluence_api_token_real"

# === CONFIGURACIÓN OPCIONAL ===
LOGFIRE_TOKEN = "tu_logfire_token_si_lo_tienes"
MEM0_API_KEY = "tu_mem0_api_key_si_lo_tienes"
PYDANTIC_AI_MODEL = "openai:gpt-4o-mini"
TIMEZONE = "UTC"
```

6. **Haz clic en "Save"**
7. **Reinicia la app** haciendo clic en "Reboot app"

### 🎯 **Paso 2: Verificar el Despliegue**

Después de configurar los secrets:

1. **Espera 1-2 minutos** para que la app se reinicie
2. **Visita tu URL**: `https://atlassian-agent-[tu-repo]-[tu-usuario].streamlit.app`
3. **Verifica que no hay errores** en los logs

---

## 📋 **Configuración Completa (Para Referencia)**

### **URLs Importantes:**
- **Tu App**: https://atlassian-agent.streamlit.app/ (o similar)
- **Panel de Control**: https://share.streamlit.io/
- **Logs en Tiempo Real**: Disponibles en el panel de control

### **Archivos Clave del Proyecto:**
- ✅ `streamlit_app.py` - Punto de entrada
- ✅ `pyproject.toml` - Dependencias (con `package-mode = false`)
- ✅ `requirements.txt` - Generado automáticamente
- ✅ `config/settings.py` - Configuración híbrida (.env + st.secrets)

### **Estructura de Secrets Requeridos:**

| Secret | Descripción | Requerido |
|--------|-------------|-----------|
| `OPENAI_API_KEY` | API Key de OpenAI | ✅ **SÍ** |
| `JIRA_URL` | URL de tu instancia Jira | ✅ **SÍ** |
| `JIRA_USERNAME` | Tu email de Jira | ✅ **SÍ** |
| `JIRA_API_TOKEN` | Token API de Jira | ✅ **SÍ** |
| `CONFLUENCE_URL` | URL de Confluence | ✅ **SÍ** |
| `CONFLUENCE_USERNAME` | Tu email de Confluence | ✅ **SÍ** |
| `CONFLUENCE_API_TOKEN` | Token API de Confluence | ✅ **SÍ** |
| `LOGFIRE_TOKEN` | Token de Logfire | ❌ Opcional |
| `MEM0_API_KEY` | API Key de Mem0 | ❌ Opcional |

---

## 🔍 **Troubleshooting**

### **Error: "No module named 'config'"**
- ✅ **Solucionado** con `streamlit_app.py` que agrega el path correcto

### **Error: "OpenAI API key must be set"**
- ✅ **Solucionado** configurando `OPENAI_API_KEY` en Streamlit Secrets
- ✅ **Solucionado** con la función `get_env_var()` en `settings.py`

### **Error: "ModuleNotFoundError"**
- Verifica que todas las dependencias están en `pyproject.toml`
- Reinicia la app en Streamlit Cloud

### **La app no carga**
- Revisa los logs en tiempo real en el panel de Streamlit Cloud
- Verifica que todos los secrets requeridos están configurados

---

## 🎉 **¡Listo para Producción!**

Una vez configurados los secrets, tu agente estará disponible en:
```
https://atlassian-agent-[repo]-[usuario].streamlit.app
```

**Funcionalidades disponibles:**
- ✅ Chat con el agente
- ✅ Integración con Jira y Confluence
- ✅ Memoria persistente (si configuraste Mem0)
- ✅ Observabilidad (si configuraste Logfire)
- ✅ Autenticación OAuth2 (cuando la configures)

---

## 📞 **Soporte**

Si tienes problemas:
1. **Revisa los logs** en Streamlit Cloud
2. **Verifica los secrets** están bien configurados
3. **Reinicia la app** si es necesario
4. **Contacta al equipo** si persisten los errores 