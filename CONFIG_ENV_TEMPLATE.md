# 📋 Template de Variables de Entorno

Este archivo contiene todas las variables de entorno necesarias para el correcto funcionamiento del agente. 

**Crea un archivo `.env` en la raíz del proyecto** con estas variables:

## 🔑 Variables Obligatorias

```bash
# =============================================================================
# APIs DE INTELIGENCIA ARTIFICIAL (AL MENOS UNA ES OBLIGATORIA)
# =============================================================================

# OpenAI (GPT models) - Principal recomendado
OPENAI_API_KEY=tu_openai_api_key

# Anthropic (Claude models) - Alternativa a OpenAI
# ANTHROPIC_API_KEY=tu_anthropic_api_key

# Groq (Ultra rápido) - Alternativa gratuita
# GROQ_API_KEY=tu_groq_api_key

# Modelo por defecto (opcional)
PYDANTIC_AI_MODEL=openai:gpt-4o-mini
```

## 🧠 Memoria Personalizada

```bash
# =============================================================================
# MEMORIA PERSONALIZADA (RECOMENDADO)
# =============================================================================

# Mem0 - Sistema de memoria personalizada
# Sin esto, la memoria no será persistente entre sesiones
MEM0_API_KEY=tu_mem0_api_key
```

## 🌍 Configuración Regional

```bash
# =============================================================================
# ZONA HORARIA (CRÍTICO PARA WORKLOGS)
# =============================================================================

# Zona horaria (IMPORTANTE para fechas correctas en worklog)
# Formato: Zona horaria IANA válida
# Ejemplos: America/Buenos_Aires, Europe/Madrid, America/New_York, UTC
TIMEZONE=America/Buenos_Aires
```

## 🏢 Atlassian (Opcional)

```bash
# =============================================================================
# ATLASSIAN - CONFIGURACIÓN POR DEFECTO (OPCIONAL)
# =============================================================================
# Los usuarios pueden configurar sus propias credenciales en la interfaz
# Estas son configuraciones por defecto para facilitar el setup inicial

# URL de tu instancia de Jira
JIRA_URL=https://tu-empresa.atlassian.net

# URL de tu instancia de Confluence  
CONFLUENCE_URL=https://tu-empresa.atlassian.net/wiki

# Credenciales por defecto (usuarios pueden usar las suyas)
ATLASSIAN_EMAIL=tu-email@empresa.com
ATLASSIAN_API_TOKEN=tu_api_token
```

## 📊 Observabilidad

```bash
# =============================================================================
# OBSERVABILIDAD Y LOGGING (OPCIONAL PERO RECOMENDADO)
# =============================================================================

# Logfire - Observabilidad avanzada
# Obtén tu token en: https://logfire.pydantic.dev
LOGFIRE_TOKEN=tu_logfire_token
```

## 🔧 Configuración Avanzada

```bash
# =============================================================================
# CONFIGURACIÓN AVANZADA (OPCIONAL)
# =============================================================================

# Puerto de Streamlit (por defecto: 8501)
# STREAMLIT_SERVER_PORT=8501

# Nivel de logging (por defecto: INFO)
# LOG_LEVEL=INFO
```

## 📝 Notas Importantes

### ✅ Variables Obligatorias
- **Al menos una API de IA**: `OPENAI_API_KEY` O `ANTHROPIC_API_KEY` O `GROQ_API_KEY`

### 🌟 Variables Recomendadas
- **`MEM0_API_KEY`**: Para memoria persistente entre sesiones
- **`LOGFIRE_TOKEN`**: Para observabilidad y debugging avanzado
- **`TIMEZONE`**: Crítico para fechas correctas en worklogs de Jira

### 🔧 Variables Opcionales
- **Variables de Atlassian**: Los usuarios pueden configurar las suyas en la interfaz
- **Puerto y logging**: Tienen valores por defecto razonables

### 🔒 Seguridad
- ⚠️ **Nunca commitees el archivo `.env`** con valores reales
- ✅ Las credenciales de usuarios se cifran automáticamente en la BD
- ✅ Este template debe estar en `.gitignore`

## 📋 Ejemplo Completo

```bash
# Copia esto en tu archivo .env y configura tus valores reales

# AI (OBLIGATORIO - al menos una)
OPENAI_API_KEY=sk-proj-abc123...

# Memoria (recomendado)
MEM0_API_KEY=mem0_abc123...

# Zona horaria (importante)
TIMEZONE=America/Buenos_Aires

# Observabilidad (opcional)
LOGFIRE_TOKEN=logfire_abc123...

# Atlassian por defecto (opcional)
JIRA_URL=https://miempresa.atlassian.net
CONFLUENCE_URL=https://miempresa.atlassian.net/wiki
ATLASSIAN_EMAIL=admin@miempresa.com
ATLASSIAN_API_TOKEN=ATATT3xFf...
```

## 🧪 Verificar Configuración

Después de crear tu archivo `.env`, verifica que esté correctamente configurado:

```bash
# Test básico de configuración
python config/settings.py

# Test específico de fechas (crítico)
python -c "
from config.settings import get_timezone, parse_datetime_robust
print('Timezone configurado:', get_timezone())
print('Test de fecha:', parse_datetime_robust('ahora'))
"

# Test de APIs de IA
python -c "
import os
apis = ['OPENAI_API_KEY', 'ANTHROPIC_API_KEY', 'GROQ_API_KEY']
configured = [api for api in apis if os.getenv(api)]
print(f'APIs configuradas: {configured}')
print(f'¿Al menos una API?: {len(configured) > 0}')
"
``` 