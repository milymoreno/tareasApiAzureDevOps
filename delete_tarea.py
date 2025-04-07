import os
import requests
import base64
from dotenv import load_dotenv
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Cargar variables del .env
load_dotenv()

AZURE_PAT = os.getenv("AZURE_PAT")
AZURE_ORGANIZATION = os.getenv("AZURE_ORGANIZATION")
AZURE_PROJECT = os.getenv("AZURE_PROJECT")

encoded_token = base64.b64encode(f":{AZURE_PAT}".encode()).decode()

HEADERS = {
    "Content-Type": "application/json",
    "Authorization": f"Basic {encoded_token}"
}

BASE_URL = f"https://dev.azure.com/{AZURE_ORGANIZATION}"

def eliminar_tarea(work_item_id: int):
    url = f"{BASE_URL}/{AZURE_PROJECT}/_apis/wit/workitems/{work_item_id}?api-version=6.0"
    response = requests.delete(url, headers=HEADERS)

    if response.status_code == 204:
        logger.info(f"✅ Tarea {work_item_id} eliminada correctamente.")
    else:
        logger.error(f"❌ Error al eliminar tarea: {response.status_code} - {response.text}")

if __name__ == "__main__":
    eliminar_tarea(18029)
