import requests
from datetime import datetime
from config import AZURE_ORGANIZATION, AZURE_PAT_ENCODED, USUARIOS_VALIDOS_HABILITADOR

import logging

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


BASE_URL = f"https://dev.azure.com/{AZURE_ORGANIZATION}"
HEADERS = {
    "Content-Type": "application/json",
    "Authorization": f"Basic {AZURE_PAT_ENCODED}"
}


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


def obtener_habilitador_semanal(fecha_str: str) -> int:
    logging.info("🔎 Buscando habilitador semanal automáticamente...")
    fecha_dt = datetime.strptime(fecha_str, "%Y-%m-%d").date()
    proyecto = obtener_proyecto_predeterminado()  

    usuarios_validos = [u.strip() for u in USUARIOS_VALIDOS_HABILITADOR]
    # Después de cargar la variable
    logging.info(f"👥 Usuarios válidos detectados: {usuarios_validos}")

    query = f"""
    SELECT [System.Id], [System.Title], [System.State], 
           [Microsoft.VSTS.Scheduling.TargetDate], 
           [Microsoft.VSTS.Scheduling.StartDate], 
           [System.AssignedTo]
    FROM WorkItems
    WHERE [System.WorkItemType] = 'Enabler'
    AND [System.Title] CONTAINS 'PEDIDOS EXPERTISE'
    AND [Microsoft.VSTS.Scheduling.StartDate] <= '{fecha_dt}'
    AND [Microsoft.VSTS.Scheduling.TargetDate] >= '{fecha_dt}'
    """


    url = f"{BASE_URL}/{proyecto}/_apis/wit/wiql?api-version=6.0"
    logging.info(f"🌐 URL WIQL: {url}")
    logging.info(f"🧪 WIQL Query a enviar:\n{query}")
    logging.debug(f"🧪 WIQL Query a enviar:\n{query}")  # 👈 Agrega esta línea    
    
    response = requests.post(url, headers=HEADERS, json={"query": query})     

    if response.status_code != 200:
        logging.error(f"❌ Error al consultar WIQL: {response.status_code} - {response.text}")
        raise Exception("Error al consultar habilitadores")

    workitems = response.json().get("workItems", [])
    if not workitems:
        raise Exception("No se encontraron habilitadores para la fecha indicada")

    ids = [str(item["id"]) for item in workitems]
    detalles_url = f"{BASE_URL}/_apis/wit/workitems?ids={','.join(ids)}&api-version=6.0"
    detalles_resp = requests.get(detalles_url, headers=HEADERS)

    if detalles_resp.status_code != 200:
        raise Exception("Error al obtener detalles de los habilitadores")

    for item in detalles_resp.json().get("value", []):
        title = item["fields"].get("System.Title", "").lower()
        assigned_to = item["fields"].get("System.AssignedTo", {}).get("displayName", "").strip()

        if (
            "pedidos expertise" in title
            and any(word in title for word in ["dev", "desarrollo", "develop"])
            and any(user.strip() in assigned_to for user in usuarios_validos)
        ):
            logging.info(f"✅ Habilitador semanal encontrado: {title} (ID: {item['id']})")
            return item["id"]            
            # return {
            #     "id": item["id"],
            #     "titulo": title,
            #     "asignado": assigned_to
            # }
    raise Exception("No se encontró habilitador válido para la fecha indicada.")