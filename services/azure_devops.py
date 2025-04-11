import os
import requests
import pandas as pd
from datetime import date, datetime
from config import AZURE_ORGANIZATION, AZURE_PAT_ENCODED

from services.azure_client import obtener_proyecto_predeterminado



import logging
logger = logging.getLogger(__name__)
#logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")


BASE_URL = f"https://dev.azure.com/{AZURE_ORGANIZATION}"

HEADERS = {
    "Content-Type": "application/json",
    "Authorization": f"Basic {AZURE_PAT_ENCODED}"
}

def ejecutar_consulta_wiql(query: str, proyecto: str) -> list:
    url = f"{BASE_URL}/{proyecto}/_apis/wit/wiql?api-version=6.0"
    #logger = logging.getLogger(__name__)
    logger.info(f"🌐 Ejecutando consulta WIQL en: {url}")
    logger.debug(f"WIQL: {query}")

    response = requests.post(url, headers=HEADERS, json={"query": query})

    if response.status_code != 200:
        logger.error(f"❌ Error al ejecutar WIQL: {response.status_code} - {response.text}")
        return []

    data = response.json()
    return [item["id"] for item in data.get("workItems", [])]


def obtener_detalles_workitems(ids: list) -> list:
    if not ids:
        return []

    ids_str = ','.join(map(str, ids))
    url = f"{BASE_URL}/_apis/wit/workitems?ids={ids_str}&$expand=relations&api-version=6.0"
    # logger = logging.getLogger(__name__)
    logger.info(f"🔍 Obteniendo detalles para WorkItems: {ids_str}")

    response = requests.get(url, headers=HEADERS)

    if response.status_code != 200:
        logger.error(f"❌ Error al obtener detalles de WorkItems: {response.status_code} - {response.text}")
        return []

    return response.json().get("value", [])

def obtener_horas_totales_del_dia(usuario: str, fecha: date) -> dict:
    proyecto = obtener_proyecto_predeterminado()

    tareas_query = f"""
    SELECT [System.Id], [System.Title], [System.WorkItemType], [Microsoft.VSTS.Scheduling.OriginalEstimate]
    FROM WorkItems
    WHERE [System.AssignedTo] CONTAINS '{usuario}'
    AND ([System.WorkItemType] = 'Task' OR [System.WorkItemType] = 'Enabler')
    AND [Microsoft.VSTS.Scheduling.TargetDate] = '{fecha}'
    AND [Microsoft.VSTS.Scheduling.FinishDate] = '{fecha}'
    """

    logger.info("🧾 Consulta WIQL para tareas y habilitadores:")
    logger.info(tareas_query)

    logger.info(f"🌐 Ejecutando consulta WIQL en: {BASE_URL}/{proyecto}/_apis/wit/wiql?api-version=6.0")

    ids = ejecutar_consulta_wiql(tareas_query, proyecto)
    workitems = obtener_detalles_workitems(ids)

    total_horas = 0.0
    detalles = []

    for item in workitems:
        tipo = item["fields"].get("System.WorkItemType")
        estimate = item["fields"].get("Microsoft.VSTS.Scheduling.OriginalEstimate", 0.0)
        titulo = item["fields"].get("System.Title")
        wid = item["id"]

        # Omitir enablers con tareas hijas
        if tipo == "Enabler":
            tiene_hijos = any(
                rel.get("rel") == "System.LinkTypes.Hierarchy-Forward"
                for rel in item.get("relations", [])
            )
            if tiene_hijos:
                logger.info(f"🔗 Enabler #{wid} omitido por tener hijos.")
                continue

        logger.info(f"✅ Contabilizado: {tipo} #{wid} - {titulo} - Horas: {estimate}")
        total_horas += estimate
        detalles.append({"id": wid, "tipo": tipo, "titulo": titulo, "horas": estimate})

    logger.info(f"🧮 Total de horas del día {fecha}: {total_horas:.2f}")
    return {"total_horas": round(total_horas, 2), "items": detalles}


def obtener_actividades_dia(usuario: str, fecha: date):
    logger.info(f"🔍 Buscando tareas para {usuario} el {fecha}")
    
    # Obtener el proyecto dinámicamente
    project = obtener_proyecto_predeterminado()
    #AND [System.WorkItemType] = 'Task'
    query = f"""
    SELECT [System.Id], [System.Title], [System.State]
    FROM WorkItems
    WHERE [System.AssignedTo] CONTAINS '{usuario}'    
    AND ([System.WorkItemType] = 'Task' OR [System.WorkItemType] = 'Enabler')
    AND [System.State] <> ''
    AND [Microsoft.VSTS.Scheduling.TargetDate] = '{fecha}'
    AND [Microsoft.VSTS.Scheduling.FinishDate] = '{fecha}'
    """

    logger.debug(f"WIQL Query:\n{query}")

    url = f"{BASE_URL}/{project}/_apis/wit/wiql?api-version=6.0"
    logger.info(f"🌐 URL final del WIQL: {url}")

    response = requests.post(url, headers=HEADERS, json={"query": query})

    if response.status_code != 200:
        logger.error(f"❌ Error en WIQL: {response.status_code} - {response.text}")
        raise Exception("Error al consultar tareas")

    result = response.json()
    ids = [item["id"] for item in result.get("workItems", [])]

    logger.info(f"🔎 Se encontraron {len(ids)} tareas registradas ese día")

    return ids



def obtener_detalles_actividades(ids: list) -> list:
    if not ids:
        return []

    logger.info("🔄 Consultando detalles de las tareas encontradas...")

    project = obtener_proyecto_predeterminado()
    url = f"{BASE_URL}/{project}/_apis/wit/workitemsbatch?api-version=6.0"

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
        raise Exception("Error al obtener detalles de tareas")

    return response.json().get("value", [])

def imprimir_titulos_y_horas(actividades: list):
    if not actividades:
        logger.info("🟡 No hay tareas para mostrar.")
        return

    logger.info("📋 Detalle de tareas encontradas:")
    total_horas = 0.0

    for actividad in actividades:
        campos = actividad.get("fields", {})
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

def calcular_total_horas(actividades: list) -> float:
    total_horas = 0.0

    for actividad in actividades:
        campos = actividad.get("fields", {})
        horas = campos.get("Microsoft.VSTS.Scheduling.CompletedWork", 0.0)
        total_horas += horas or 0

    logger.info(f"🧮 Total horas registradas: {round(total_horas, 2)} horas")
    return total_horas

def crear_tarea_en_azure(payload: list, proyecto: str, tipo: str = "Task") -> dict:
    """
    Crea una tarea en Azure DevOps usando un payload JSON Patch.
    
    Args:
        payload (list): Lista de operaciones JSON Patch para la creación de la tarea.
        proyecto (str): Nombre del proyecto en Azure DevOps.
        tipo (str): Tipo de WorkItem (por defecto "Task").

    Returns:
        dict: Diccionario con datos de la tarea creada o error.
    """
    url = f"{BASE_URL}/{proyecto}/_apis/wit/workitems/${tipo}?api-version=6.0"
    headers = {
        "Content-Type": "application/json-patch+json",
        "Authorization": f"Basic {AZURE_PAT_ENCODED}"
    }

    response = requests.patch(url, headers=headers, json=payload)

    if response.status_code in [200, 201]:
        data = response.json()
        return {
            "success": True,
            "id": data["id"],
            "url": data["_links"]["html"]["href"],
            "data": data
        }
    else:
        logger.error(f"❌ Error al crear tarea: {response.status_code} - {response.text}")
        return {
            "success": False,
            "status_code": response.status_code,
            "error": response.text
        }
def generar_payload_tarea(titulo: str, descripcion: str, usuario: str, duracion_horas: float,
                           fecha: date, hora_fin: pd.Timestamp, habilitador_id: int) -> list:
    """
    Genera el payload JSON Patch para crear una tarea en Azure DevOps.

    Args:
        titulo (str): Título de la tarea.
        descripcion (str): Descripción de la tarea.
        usuario (str): Usuario asignado.
        duracion_horas (float): Duración estimada y completada.
        fecha (date): Fecha de target/finish.
        hora_fin (pd.Timestamp): Hora de finalización.
        habilitador_id (int): ID del habilitador semanal al que vincular la tarea.

    Returns:
        list: Lista de operaciones JSON Patch.
    """
    # Asegurar que hora_fin no tenga un día diferente a fecha
    if hora_fin.date() != fecha:
        hora_fin = pd.Timestamp.combine(fecha, hora_fin.time())

    return [
        {"op": "add", "path": "/fields/System.Title", "value": titulo},
        {"op": "add", "path": "/fields/System.Description", "value": descripcion},
        {"op": "add", "path": "/fields/System.AssignedTo", "value": usuario},
        {"op": "add", "path": "/fields/Microsoft.VSTS.Scheduling.OriginalEstimate", "value": duracion_horas},
        {"op": "add", "path": "/fields/Microsoft.VSTS.Scheduling.CompletedWork", "value": duracion_horas},
        {"op": "add", "path": "/fields/Microsoft.VSTS.Scheduling.FinishDate", "value": hora_fin.isoformat()},
        {"op": "add", "path": "/fields/Microsoft.VSTS.Scheduling.TargetDate", "value": fecha.isoformat()},
        {"op": "add", "path": "/fields/System.State", "value": "New"},
        {"op": "add", "path": "/relations/-", "value": {
            "rel": "System.LinkTypes.Hierarchy-Reverse",
            "url": f"https://dev.azure.com/{AZURE_ORGANIZATION}/_apis/wit/workItems/{habilitador_id}",
            "attributes": {"comment": "Vinculado al habilitador semanal"}
        }}
    ]

def obtener_horas_por_habilitador_y_fecha(usuario: str, fecha: date, habilitador_id: int, proyecto: str) -> dict:
    """
    Devuelve las horas registradas en tareas de un habilitador específico en una fecha dada.

    Args:
        usuario (str): Usuario asignado.
        fecha (date): Fecha objetivo.
        habilitador_id (int): ID del habilitador padre.
        proyecto (str): Proyecto de Azure DevOps.

    Returns:
        dict: Información con lista de tareas, total de horas y estado.
    """
    #  AND [System.WorkItemType] = 'Task'
    query = f"""
    SELECT [System.Id], [System.Title], [System.State]
    FROM WorkItems
    WHERE [System.AssignedTo] CONTAINS '{usuario}'
    AND ([System.WorkItemType] = 'Task' OR [System.WorkItemType] = 'Enabler')   
    AND [System.State] <> ''
    AND [Microsoft.VSTS.Scheduling.TargetDate] = '{fecha}'
    AND [Microsoft.VSTS.Scheduling.FinishDate] = '{fecha}'
    """

    url = f"{BASE_URL}/{proyecto}/_apis/wit/wiql?api-version=6.0"
    response = requests.post(url, headers=HEADERS, json={"query": query})

    if response.status_code != 200:
        logger.error(f"❌ Error al consultar WIQL: {response.status_code} - {response.text}")
        raise Exception("Error al consultar tareas")

    result = response.json()
    ids = [item["id"] for item in result.get("workItems", [])]
    if not ids:
        return {"tareas": [], "total_horas": 0.0, "estado": "incompleto"}

    url_detalles = f"{BASE_URL}/_apis/wit/workitems?ids={','.join(map(str, ids))}&$expand=relations&api-version=6.0"
    detalles_resp = requests.get(url_detalles, headers=HEADERS)
    tareas = detalles_resp.json().get("value", [])

    tareas_filtradas = []
    total_horas = 0.0

    for tarea in tareas:
        relations = tarea.get("relations", [])
        for rel in relations:
            if (
                rel.get("rel") == "System.LinkTypes.Hierarchy-Reverse"
                and str(habilitador_id) in rel.get("url", "")
            ):
                estimate = tarea["fields"].get("Microsoft.VSTS.Scheduling.OriginalEstimate", 0.0)
                total_horas += estimate
                tareas_filtradas.append({
                    "id": tarea["id"],
                    "titulo": tarea["fields"].get("System.Title"),
                    "estado": tarea["fields"].get("System.State"),
                    "horas": estimate
                })
                break

    if total_horas == 9.0:
        estado = "completo"
    elif total_horas > 0:
        estado = "parcial"
    else:
        estado = "incompleto"

    return {
        "tareas": tareas_filtradas,
        "total_horas": round(total_horas, 2),
        "estado": estado
    }


def cerrar_tareas_por_fecha(usuario: str, fecha: date, proyecto: str) -> list:
    """
    Cierra todas las tareas del usuario en la fecha indicada que no estén cerradas.

    Args:
        usuario (str): Nombre del usuario asignado.
        fecha (date): Fecha objetivo (FinishDate y TargetDate).
        proyecto (str): Proyecto en Azure DevOps.

    Returns:
        list: Lista de tareas que fueron cerradas con éxito.
    """
    tareas_cerradas = []
    tareas = obtener_tareas_abiertas_por_fecha(usuario, fecha, proyecto)

    if not tareas:
        logger.info("📭 No hay tareas abiertas para cerrar en esa fecha.")
        return []

    for tarea in tareas:
        tarea_id = tarea["id"]
        estado_actual = tarea["fields"].get("System.State", "")
        
        if estado_actual.lower() == "closed":
            continue  # Ya cerrada, por seguridad

        payload = [
            {"op": "add", "path": "/fields/System.State", "value": "Closed"}
        ]
        url = f"{BASE_URL}/{proyecto}/_apis/wit/workitems/{tarea_id}?api-version=6.0"
        
        
        headers_patch = {
            "Content-Type": "application/json-patch+json",
            "Authorization": f"Basic {AZURE_PAT_ENCODED}"
        }
        response = requests.patch(url, headers=headers_patch, json=payload)


        if response.status_code in [200, 201]:
            tareas_cerradas.append(tarea_id)
            logger.info(f"✅ Tarea {tarea_id} cerrada correctamente")
        else:
            logger.error(f"❌ Error al cerrar tarea {tarea_id}: {response.status_code} - {response.text}")

    return tareas_cerradas



def obtener_tareas_abiertas_por_fecha(usuario: str, fecha: date, proyecto: str) -> list:
    """
    Obtiene tareas tipo 'Task' asignadas a un usuario en un día específico que no estén cerradas.

    Args:
        usuario (str): Nombre del usuario asignado (ej: 'Mildred Moreno').
        fecha (date): Fecha a filtrar por TargetDate y FinishDate.
        proyecto (str): Nombre del proyecto en Azure DevOps.

    Returns:
        list: Lista de tareas abiertas (diccionarios con datos completos).
    """
    # [System.WorkItemType] = 'Task'
    logger.info(f"🔍 Buscando tareas abiertas de {usuario} en {fecha}")

    query = f"""
    SELECT [System.Id], [System.Title], [System.State], [Microsoft.VSTS.Scheduling.OriginalEstimate],
           [Microsoft.VSTS.Scheduling.FinishDate], [Microsoft.VSTS.Scheduling.TargetDate]
    FROM WorkItems
    WHERE         
        ([System.WorkItemType] = 'Task' OR [System.WorkItemType] = 'Enabler')
        AND [System.AssignedTo] CONTAINS '{usuario}'
        AND [System.State] = 'New'
        AND [Microsoft.VSTS.Scheduling.TargetDate] = '{fecha}'
        AND [Microsoft.VSTS.Scheduling.FinishDate] = '{fecha}'
    """

    url = f"{BASE_URL}/{proyecto}/_apis/wit/wiql?api-version=6.0"
    response = requests.post(url, headers=HEADERS, json={"query": query})

    if response.status_code != 200:
        logger.error(f"❌ Error al consultar WIQL: {response.status_code} - {response.text}")
        raise Exception("Error en consulta WIQL")

    result = response.json()
    work_item_ids = [item["id"] for item in result.get("workItems", [])]

    if not work_item_ids:
        logger.info("📭 No hay tareas abiertas encontradas.")
        return []

    logger.info(f"🔄 Consultando detalles de {len(work_item_ids)} tareas abiertas")

    ids_str = ",".join(str(id_) for id_ in work_item_ids)
    url_detalles = f"{BASE_URL}/_apis/wit/workitems?ids={ids_str}&api-version=6.0"
    response_detalles = requests.get(url_detalles, headers=HEADERS)

    if response_detalles.status_code != 200:
        logger.error(f"❌ Error al obtener detalles: {response_detalles.status_code} - {response_detalles.text}")
        raise Exception("Error al obtener detalles de tareas")

    return response_detalles.json().get("value", [])

