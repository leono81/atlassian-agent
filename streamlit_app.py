# streamlit_app.py
# Punto de entrada principal para Streamlit Community Cloud

import sys
import os

# Agregar el directorio actual al path para imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Importar y ejecutar la aplicación principal
from ui.app import * 