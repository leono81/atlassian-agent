import streamlit as st
import subprocess # Para ejecutar streamlit desde aquí
import os
from config.settings import validate_config

def run_streamlit():
    """Ejecuta la aplicación Streamlit."""
    # Asegurarse de que la configuración es válida antes de lanzar
    try:
        validate_config()
    except ValueError as e:
        st.error(f"Error de configuración: {e}")
        st.stop()

    # Obtener la ruta al script de la app de Streamlit
    # __file__ es la ruta a este script (main.py)
    # os.path.dirname obtiene el directorio de main.py
    # os.path.join construye la ruta a ui/app.py
    streamlit_app_path = os.path.join(os.path.dirname(__file__), "ui", "app.py")

    # Comando para ejecutar Streamlit
    # Usamos sys.executable para asegurar que se usa el mismo intérprete de Python
    # que está ejecutando este script.
    import sys
    command = [sys.executable, "-m", "streamlit", "run", streamlit_app_path]

    print(f"Ejecutando Streamlit con el comando: {' '.join(command)}")
    subprocess.run(command)

if __name__ == "__main__":
    run_streamlit()
    