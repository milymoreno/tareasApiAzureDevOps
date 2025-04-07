from datetime import date, datetime
import json
import os
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

def cargar_prs_revisados_por_fecha(fecha_str):
    try:
        fecha_dt = datetime.strptime(fecha_str, "%Y-%m-%d").date()
    except ValueError:
        logging.error(f"❌ Formato de fecha inválido: {fecha_str}. Se espera dd-mm-yyyy.")
        raise

    fecha_archivo = fecha_dt.strftime('%d_%m_%Y')  # formato 02_04_2025
    ruta = f"/home/mildred-moreno/tracking/pr_tracking_{fecha_archivo}.json"

    logging.info(f"📅 Fecha solicitada: {fecha_archivo}")
    logging.info(f"📂 Intentando cargar archivo de tracking: {ruta}")

    if not os.path.exists(ruta):
        logging.error(f"❌ No se encontró el archivo de tracking: {ruta}")
        raise FileNotFoundError(f"No se encontró el archivo de tracking: {ruta}")

    try:
        with open(ruta, "r") as f:
            data = json.load(f)
            logging.info(f"✅ Archivo cargado exitosamente. Total PRs revisados: {len(data)}")
            return data
    except Exception as e:
        logging.error(f"❌ Error al leer el archivo: {e}")
        raise


# def cargar_prs_revisados_de_hoy():
#     fecha_hoy = date.today().strftime('%d_%m_%Y')  # formato 02_04_2025
#     ruta = f"/home/mildred-moreno/tracking/pr_tracking_{fecha_hoy}.json"

#     logging.info(f"📅 Fecha actual: {fecha_hoy}")
#     logging.info(f"📂 Intentando cargar archivo de tracking: {ruta}")

#     if not os.path.exists(ruta):
#         logging.error(f"❌ No se encontró el archivo de tracking: {ruta}")
#         raise FileNotFoundError(f"No se encontró el archivo de tracking: {ruta}")

#     try:
#         with open(ruta, "r") as f:
#             data = json.load(f)
#             logging.info(f"✅ Archivo cargado exitosamente. Total PRs revisados: {len(data)}")
#             return data
#     except Exception as e:
#         logging.error(f"❌ Error al leer el archivo: {e}")
#         raise

#     logging.info(f"📥 Archivo cargado exitosamente. Total PRs revisados: {len(data)}")
    
def generar_resumen_repositorios(fecha: str):
    try:
        prs = cargar_prs_revisados_por_fecha(fecha)
        repositorios = set()

        for pr_id, info in prs.items():
            estado = info.get("estado")
            if estado != "omitido":
                repo = info.get("repositorio")
                if repo:
                    repositorios.add(repo)

        if not repositorios:
            logging.info("⚠️ No hay repositorios registrados hoy (todos omitidos o vacío).")
            return ""

        resumen = f"Se revisaron y aprobaron PRs correspondientes a los siguientes repositorios: {', '.join(sorted(repositorios))}."
        logging.info(f"📝 Resumen generado: {resumen}")
        return resumen

    except Exception as e:
        logging.error(f"🚨 Error generando resumen de repositorios: {str(e)}")
        return ""
    
def generar_payload_revision_prs(usuario: str, fecha: str, habilitador_id: int, duracion_horas: float, descripcion: str):
    payload = {
        "titulo": "Revisión y Aprobación de PRs",
        "descripcion": descripcion,
        "usuario": usuario,
        "fecha": fecha,
        "horaFin": datetime.now().isoformat(),
        "duracion": round(duracion_horas, 2),
        "habilitador_id": habilitador_id,
    }
    logging.info(f"📦 Payload generado: {json.dumps(payload, indent=2, ensure_ascii=False)}")
    return payload