# streamlit_app.py
# Punto de entrada principal para Streamlit Community Cloud
# Este archivo ejecuta la aplicación real ubicada en ui/app.py

import sys
import os
from pathlib import Path

# Configurar el path para imports
try:
    # En ejecución normal
    project_root = Path(__file__).parent.absolute()
except NameError:
    # En pruebas o contextos especiales
    project_root = Path.cwd()

sys.path.insert(0, str(project_root))

# Ejecutar la aplicación real directamente
app_file = project_root / "ui" / "app.py"
if app_file.exists():
    with open(app_file, 'r', encoding='utf-8') as f:
        exec(f.read())
else:
    raise FileNotFoundError(f"No se encontró ui/app.py en {project_root}") 