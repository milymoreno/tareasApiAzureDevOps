import os
from dotenv import load_dotenv
import base64

load_dotenv()

AZURE_PAT = os.getenv("AZURE_PAT")
AZURE_ORGANIZATION = os.getenv("AZURE_ORGANIZATION")
AZURE_PROJECT = os.getenv("AZURE_PROJECT")
EXCEL_PATH = os.getenv("EXCEL_PATH", "data")  # Carpeta por defecto
AZURE_PAT_ENCODED = base64.b64encode(f":{AZURE_PAT}".encode()).decode()
USUARIOS_VALIDOS_HABILITADOR = os.getenv("USUARIOS_VALIDOS_HABILITADOR", "").split(",")

