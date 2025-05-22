import sys
import os

# Asegura que la raíz del proyecto esté en el path
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from src import create_app

app = create_app()

if __name__ == "__main__":
    app.run()
