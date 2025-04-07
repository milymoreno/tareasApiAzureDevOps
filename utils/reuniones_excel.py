import pandas as pd
import logging
from datetime import datetime

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

def limpiar_titulo(titulo: str) -> str:
    return titulo.replace("[GMAIL]", "").strip()




def leer_reuniones_excel(ruta_excel: str) -> list:
    logger.info(f"📄 Leyendo archivo: {ruta_excel}")
    df = df = pd.read_excel(ruta_excel, engine="openpyxl")
    logger.info(f"📊 Reuniones encontradas: {len(df)} filas")

    reuniones = []
    for i, row in df.iterrows():
        hora_inicio = pd.to_datetime(row["horaInicio"])
        hora_fin = pd.to_datetime(row["horaFin"])
        duracion_horas = (hora_fin - hora_inicio).total_seconds() / 3600

        titulo_limpio = limpiar_titulo(str(row["titulo"]))

        reunion = {
            "titulo_original": row["titulo"],
            "titulo": titulo_limpio,
            "horaInicio": hora_inicio,
            "horaFin": hora_fin,
            "organizador": row["organizador"],
            "fecha": hora_inicio.date(),
            "duracion_horas": duracion_horas
        }

        logger.info(f"✅ Reunión {i+1}: {reunion}")
        reuniones.append(reunion)

    return reuniones
