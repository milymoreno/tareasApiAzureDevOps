import os
import base64
import requests
from dotenv import load_dotenv


import os
import requests
import pandas as pd
from datetime import date
from config import AZURE_ORGANIZATION

import logging
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


# Cargar variables del .env
load_dotenv()

AZURE_PAT = os.getenv("AZURE_PAT")
ORGANIZATION = os.getenv("AZURE_ORGANIZATION")

encoded_token = base64.b64encode(f":{AZURE_PAT}".encode()).decode()

HEADERS = {
    "Content-Type": "application/json",
    "Authorization": f"Basic {encoded_token}"
}

BASE_URL = f"https://dev.azure.com/{ORGANIZATION}"

def listar_proyectos():
    url = f"{BASE_URL}/_apis/projects?api-version=6.0"
    try:
        response = requests.get(url, headers=HEADERS, timeout=30)
        response.raise_for_status()
        data = response.json()
        print("✅ Conexión exitosa. Proyectos encontrados:")
        for proyecto in data.get("value", []):
            print(f"- {proyecto['name']}")
    except Exception as e:
        print("❌ Error en la conexión o autenticación:")
        print(e)
        
def obtener_proyecto_predeterminado():
    url = f"{BASE_URL}/_apis/projects?api-version=6.0"
    response = requests.get(url, headers=HEADERS)
    if response.status_code == 200:
        proyectos = response.json().get("value", [])
        for p in proyectos:
            if "P2P Project" in p["name"]:
                logger.info(f"✅ Proyecto detectado dinámicamente: {p['name']}")
                return p["name"]
        logger.warning("⚠️ Proyecto 'P2P Project' no encontrado. Usando el primero disponible.")
        return proyectos[0]["name"] if proyectos else None
    else:
        logger.error(f"❌ Error al obtener proyectos: {response.status_code} - {response.text}")
        raise Exception("Error al obtener lista de proyectos")

PROJECT = obtener_proyecto_predeterminado()


def obtener_actividades_dia(usuario: str, fecha: date):
    logger.info(f"🔍 Buscando tareas para {usuario} el {fecha}")

    query = f"""
    SELECT [System.Id], [System.Title], [System.State]
    FROM WorkItems
    WHERE [System.AssignedTo] CONTAINS '{usuario}'
    AND [System.WorkItemType] = 'Task'
    AND [System.State] <> ''
    AND [Microsoft.VSTS.Scheduling.TargetDate] = '{fecha}'
    AND [Microsoft.VSTS.Scheduling.FinishDate] = '{fecha}'
    """

    
    # AND [System.WorkItemType] = 'Task'
    # AND [System.State] <> ''
    # AND [System.ClosedDate] >= '{fecha}T00:00:00Z'
    # AND [System.ClosedDate] <= '{fecha}T23:59:59Z'

    logger.debug(f"WIQL Query:\n{query}")
    
    url = f"{BASE_URL}/{PROJECT}/_apis/wit/wiql?api-version=6.0"

    logger.info(f"🌐 URL final del WIQL: {url}")
    response = requests.post(url, headers=HEADERS, json={"query": query})


    if response.status_code != 200:
        logger.error(f"❌ Error en WIQL: {response.status_code} - {response.text}")
        raise Exception("Error al consultar tareas")    
   

    result = response.json()
    ids = [item["id"] for item in result.get("workItems", [])]
    
    for i, tarea_id in enumerate(ids, start=1):
        logger.info(f"   🔹 Tarea {i}: ID={tarea_id}")


    logger.info(f"🔎 Se encontraron {len(ids)} tareas registradas ese día")

    return ids

def imprimir_titulos_tareas(ids: list):
    if not ids:
        logger.info("🟡 No hay tareas para mostrar.")
        return

    url = f"{BASE_URL}/_apis/wit/workitemsbatch?api-version=6.0"
    body = {
        "ids": ids,
        "fields": ["System.Id", "System.Title"]
    }

    response = requests.post(url, headers=HEADERS, json=body)

    if response.status_code != 200:
        logger.error(f"❌ Error al obtener detalles: {response.status_code} - {response.text}")
        return

    tareas = response.json().get("value", [])
    logger.info(f"📝 Títulos de las tareas encontradas:")
    for tarea in tareas:
        id_ = tarea.get("id")
        title = tarea.get("fields", {}).get("System.Title", "Sin título")
        logger.info(f"   🔹 [{id_}] {title}")

# def imprimir_titulos_y_horas(ids: list):
#     if not ids:
#         logger.info("🟡 No hay tareas para mostrar.")
#         return

#     url = f"{BASE_URL}/_apis/wit/workitemsbatch?api-version=6.0"
#     body = {
#         "ids": ids,
#         "fields": [
#             "System.Id",
#             "System.Title",
#             "Microsoft.VSTS.Scheduling.CompletedWork"
#         ]
#     }

#     response = requests.post(url, headers=HEADERS, json=body)

#     if response.status_code != 200:
#         logger.error(f"❌ Error al obtener detalles: {response.status_code} - {response.text}")
#         return

#     tareas = response.json().get("value", [])
#     logger.info(f"📝 Detalle de tareas encontradas:")
#     total_horas = 0.0

#     for tarea in tareas:
#         campos = tarea.get("fields", {})
#         titulo = campos.get("System.Title", "Sin título")
#         horas = campos.get("Microsoft.VSTS.Scheduling.CompletedWork", 0.0)
#         total_horas += horas or 0
#         logger.info(f"   🔹 {titulo} - ⏱️ {horas} horas")

#     logger.info(f"🧮 Total acumulado: {round(total_horas, 2)} horas")

def imprimir_titulos_y_horas(ids: list):
    if not ids:
        logger.info("🟡 No hay tareas para mostrar.")
        return

    url = f"{BASE_URL}/_apis/wit/workitemsbatch?api-version=6.0"
    body = {
        "ids": ids,
        "fields": [
            "System.Id",
            "System.Title",
            "Microsoft.VSTS.Scheduling.CompletedWork",
            "Microsoft.VSTS.Scheduling.TargetDate",
            "Microsoft.VSTS.Scheduling.FinishDate"
        ]
    }

    response = requests.post(url, headers=HEADERS, json=body)

    if response.status_code != 200:
        logger.error(f"❌ Error al obtener detalles: {response.status_code} - {response.text}")
        return

    tareas = response.json().get("value", [])
    logger.info("📋 Detalle de tareas encontradas:")
    total_horas = 0.0

    for tarea in tareas:
        campos = tarea.get("fields", {})
        titulo = campos.get("System.Title", "Sin título")
        horas = campos.get("Microsoft.VSTS.Scheduling.CompletedWork", 0.0)
        target_date = campos.get("Microsoft.VSTS.Scheduling.TargetDate", "N/A")
        finish_date = campos.get("Microsoft.VSTS.Scheduling.FinishDate", "N/A")
        total_horas += horas or 0

        logger.info(f"   🔹 {titulo}")
        logger.info(f"      ⏱️ {horas} horas")
        logger.info(f"      🎯 Target Date: {target_date}")
        logger.info(f"      ✅ Finish Date: {finish_date}")

    logger.info(f"🧮 Total acumulado: {round(total_horas, 2)} horas")



if __name__ == "__main__":
    listar_proyectos()
    from datetime import datetime
    usuario = "Mildred Moreno"
    #fecha = datetime.now().date()    
    fecha = date(2025, 3, 3)
    #obtener_actividades_dia(usuario, fecha)
    tareas_ids = obtener_actividades_dia(usuario, fecha)
    #imprimir_titulos_tareas(tareas_ids)
    imprimir_titulos_y_horas(tareas_ids)

