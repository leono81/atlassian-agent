# ui/custom_styles.py
import streamlit as st

def apply_custom_title_styles():
    """Aplica estilos personalizados para títulos usando CSS."""
    st.markdown("""
    <style>
        /* Importar Google Fonts */
        @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;600;700&family=Inter:wght@400;500;600&display=swap');
        
        /* Estilos para títulos principales */
        .titulo-app {
            font-family: 'Poppins', sans-serif;
            font-size: 2.5rem;
            font-weight: 700;
            color: #1e3a8a;
            text-align: center;
            margin: 0 0 1rem 0;
            background: linear-gradient(135deg, #1e3a8a 0%, #3b82f6 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }
        
        .titulo-seccion {
            font-family: 'Inter', sans-serif;
            font-size: 1.8rem;
            font-weight: 600;
            color: #374151;
            margin: 1.5rem 0 1rem 0;
            border-bottom: 2px solid #e5e7eb;
            padding-bottom: 0.5rem;
        }
        
        .titulo-usuario {
            font-family: 'Poppins', sans-serif;
            font-size: 2rem;
            font-weight: 500;
            color: #059669;
            margin: 0;
        }
        
        /* Títulos con efectos especiales */
        .titulo-gradiente {
            font-family: 'Poppins', sans-serif;
            font-size: 2.2rem;
            font-weight: 700;
            background: linear-gradient(45deg, #ff6b6b, #4ecdc4, #45b7d1, #96ceb4);
            background-size: 300% 300%;
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            animation: gradientShift 3s ease infinite;
            text-align: center;
        }
        
        @keyframes gradientShift {
            0% { background-position: 0% 50%; }
            50% { background-position: 100% 50%; }
            100% { background-position: 0% 50%; }
        }
        
        /* Título con sombra */
        .titulo-sombra {
            font-family: 'Poppins', sans-serif;
            font-size: 2.5rem;
            font-weight: 600;
            color: #1f2937;
            text-shadow: 3px 3px 6px rgba(0, 0, 0, 0.2);
            text-align: center;
            margin: 1rem 0;
        }
        
        /* Título minimalista */
        .titulo-minimal {
            font-family: 'Inter', sans-serif;
            font-size: 2rem;
            font-weight: 300;
            color: #6b7280;
            letter-spacing: 2px;
            text-transform: uppercase;
            text-align: center;
            margin: 2rem 0;
        }
    </style>
    """, unsafe_allow_html=True)

def render_custom_title(text, style="default", emoji=""):
    """
    Renderiza un título con estilo personalizado.
    
    Args:
        text (str): Texto del título
        style (str): Estilo a aplicar ('app', 'seccion', 'usuario', 'gradiente', 'sombra', 'minimal')
        emoji (str): Emoji opcional
    """
    if style == "app":
        st.markdown(f'<h1 class="titulo-app">{emoji} {text}</h1>', unsafe_allow_html=True)
    elif style == "seccion":
        st.markdown(f'<h2 class="titulo-seccion">{emoji} {text}</h2>', unsafe_allow_html=True)
    elif style == "usuario":
        st.markdown(f'<h2 class="titulo-usuario">{emoji} {text}</h2>', unsafe_allow_html=True)
    elif style == "gradiente":
        st.markdown(f'<h1 class="titulo-gradiente">{emoji} {text}</h1>', unsafe_allow_html=True)
    elif style == "sombra":
        st.markdown(f'<h1 class="titulo-sombra">{emoji} {text}</h1>', unsafe_allow_html=True)
    elif style == "minimal":
        st.markdown(f'<h1 class="titulo-minimal">{emoji} {text}</h1>', unsafe_allow_html=True)
    else:
        # Título por defecto
        st.title(f"{emoji} {text}")

# Ejemplos de uso:
def show_title_examples():
    """Muestra ejemplos de diferentes estilos de títulos."""
    apply_custom_title_styles()
    
    render_custom_title("Agente Atlassian", "app", "🤖")
    render_custom_title("Bienvenido Leandro", "usuario", "👋")
    render_custom_title("Configuración", "seccion", "⚙️")
    render_custom_title("Título Animado", "gradiente", "✨")
    render_custom_title("Título con Sombra", "sombra", "🎯")
    render_custom_title("Diseño Minimalista", "minimal", "") 