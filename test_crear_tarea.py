# test_crear_tarea.py

import os
import requests
import base64
from datetime import datetime, timedelta
from dotenv import load_dotenv
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Cargar variables de entorno
load_dotenv()
AZURE_PAT = os.getenv("AZURE_PAT")
AZURE_ORGANIZATION = os.getenv("AZURE_ORGANIZATION")
AZURE_PROJECT = os.getenv("AZURE_PROJECT")

ENCODED_PAT = base64.b64encode(f":{AZURE_PAT}".encode()).decode()
HEADERS = {
    "Content-Type": "application/json",
    "Authorization": f"Basic {ENCODED_PAT}"
}

# Datos de prueba
TITULO = "🧪 Tarea de prueba IA 1h"
DESCRIPCION = "Esta es una tarea de prueba creada automáticamente para verificar el registro"
USUARIO_ASIGNADO = "Mildred Moreno"
PARENT_ID = 16345

# Fecha objetivo
fecha = datetime(2025, 3, 3)
finish_date = fecha.replace(hour=18, minute=0)
target_date = fecha.date()

# Endpoint
url = f"https://dev.azure.com/{AZURE_ORGANIZATION}/{AZURE_PROJECT}/_apis/wit/workitems/$Task?api-version=6.0"

# Cuerpo PATCH
payload = [
    {"op": "add", "path": "/fields/System.Title", "value": TITULO},
    {"op": "add", "path": "/fields/System.Description", "value": DESCRIPCION},
    {"op": "add", "path": "/fields/System.AssignedTo", "value": USUARIO_ASIGNADO},
    {"op": "add", "path": "/fields/Microsoft.VSTS.Scheduling.OriginalEstimate", "value": 1.0},
    {"op": "add", "path": "/fields/Microsoft.VSTS.Scheduling.CompletedWork", "value": 1.0},
    {"op": "add", "path": "/fields/Microsoft.VSTS.Scheduling.FinishDate", "value": finish_date.isoformat()},
    {"op": "add", "path": "/fields/Microsoft.VSTS.Scheduling.TargetDate", "value": target_date.isoformat()},
    {"op": "add", "path": "/fields/System.State", "value": "Closed"},
    {"op": "add", "path": "/relations/-", "value": {
        "rel": "System.LinkTypes.Hierarchy-Reverse",
        "url": f"https://dev.azure.com/{AZURE_ORGANIZATION}/_apis/wit/workItems/{PARENT_ID}",
        "attributes": {"comment": "Vinculado al habilitador semanal"}
    }},
]


# Ejecutar
response = requests.patch(url, headers={**HEADERS, "Content-Type": "application/json-patch+json"}, json=payload)

if response.status_code in [200, 201]:
    data = response.json()
    logger.info(f"✅ Tarea creada exitosamente con ID: {data['id']}")
    logger.info(f"🔗 Enlace: {data['_links']['html']['href']}")
else:
    logger.error(f"❌ Error al crear la tarea: {response.status_code} - {response.text}")
