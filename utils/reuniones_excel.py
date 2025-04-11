import pandas as pd
import logging
from datetime import date

from services.azure_devops import (
    generar_payload_tarea,
    obtener_actividades_dia,
    obtener_detalles_actividades,
    calcular_total_horas,
    crear_tarea_en_azure,
    cerrar_tareas_por_fecha,
    obtener_horas_por_habilitador_y_fecha,   
    obtener_horas_totales_del_dia
    #,imprimir_titulos_y_horas 
)

from services.azure_client import (
    obtener_proyecto_predeterminado,
    obtener_habilitador_semanal
)

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


def procesar_reuniones_data(
    reuniones: list,
    habilitador_id: int,
    usuario: str,
    fecha_actual: date
) -> dict:
    logger.info(f"📆 Procesando reuniones para el {fecha_actual}")

    tareas_existentes = obtener_actividades_dia(usuario, fecha_actual)
    detalles = obtener_detalles_actividades(tareas_existentes)
    horas_actuales = calcular_total_horas(detalles)

    logger.info(f"🕒 Horas acumuladas hoy: {horas_actuales:.2f}")
    horas_disponibles = 9.0 - horas_actuales
    logger.info(f"🟩 Horas disponibles: {horas_disponibles:.2f}")

    tareas_a_crear = []
    reuniones_mildred = []
    reuniones_normales = []

    for reunion in reuniones:
        if reunion["fecha"] != fecha_actual:
            logger.info(f"⏩ Ignorando reunión fuera de hoy: {reunion['titulo']}")
            continue

        organizador = reunion["organizador"].strip().lower()
        if organizador == "mildred.moreno@innovacionypagos.com.pa":
            reuniones_mildred.append(reunion)
        else:
            reuniones_normales.append(reunion)

    proyecto = obtener_proyecto_predeterminado()

    for reunion in reuniones_normales:
        if reunion["duracion_horas"] <= horas_disponibles:
            duracion = reunion["duracion_horas"]
        elif horas_disponibles > 0:
            duracion = horas_disponibles
            reunion["horaFin"] = reunion["horaInicio"] + pd.Timedelta(hours=duracion)
            reunion["duracion_horas"] = duracion
            logger.warning(f"⚠️ Reunión recortada por tiempo: {reunion['titulo']} → {duracion:.2f}h")
        else:
            logger.warning(f"🛑 Tiempo agotado. Reunión omitida: {reunion['titulo']}")
            continue

        payload = generar_payload_tarea(
            titulo=reunion["titulo"],
            descripcion=reunion.get("descripcion", ""),
            usuario=usuario,
            duracion_horas=duracion,
            fecha=reunion["horaInicio"],
            hora_fin=reunion["horaFin"],
            habilitador_id=habilitador_id
        )

        resultado = crear_tarea_en_azure(payload, proyecto)
        if resultado["success"]:
            reunion["id"] = resultado["id"]
            reunion["url"] = resultado["url"]
            tareas_a_crear.append(reunion)
            logger.info(f"✅ Tarea creada: {reunion['titulo']} - ID: {resultado['id']}")
            horas_disponibles -= duracion
        else:
            logger.error(f"❌ Error al crear la tarea: {resultado['status_code']} - {resultado['error']}")

    if reuniones_mildred:
        total_horas_mildred = sum(r["duracion_horas"] for r in reuniones_mildred)
        if total_horas_mildred <= horas_disponibles:
            titulos = "\n".join(f"- {r['titulo']}" for r in reuniones_mildred)
            descripcion_consolidada = f"Reuniones organizadas por Mildred:\n{titulos}"
            hora_inicio = min(r["horaInicio"] for r in reuniones_mildred)
            hora_fin = hora_inicio + pd.Timedelta(hours=total_horas_mildred)

            payload = generar_payload_tarea(
                titulo="Reuniones varias y con equipo",
                descripcion=descripcion_consolidada,
                usuario=usuario,
                duracion_horas=total_horas_mildred,
                fecha=hora_inicio,
                hora_fin=hora_fin,
                habilitador_id=habilitador_id
            )

            resultado = crear_tarea_en_azure(payload, proyecto)
            if resultado["success"]:
                tareas_a_crear.append({
                    "titulo": "Reuniones de sincronización varias",
                    "descripcion": descripcion_consolidada,
                    "duracion_horas": total_horas_mildred,
                    "id": resultado["id"],
                    "url": resultado["url"]
                })
                logger.info(f"✅ Tarea consolidada creada: Reuniones varias y con equipo - ID: {resultado['id']}")
                horas_disponibles -= total_horas_mildred
            else:
                logger.error(f"❌ Error al crear la tarea consolidada: {resultado['status_code']} - {resultado['error']}")

    total_horas_registradas = sum(t["duracion_horas"] for t in tareas_a_crear)
    tareas_cerradas = cerrar_tareas_por_fecha(usuario, fecha_actual, proyecto)

    return {
        "mensaje": f"{len(tareas_a_crear)} reuniones registradas exitosamente",
        "horas_registradas": total_horas_registradas,
        "horas_restantes": horas_disponibles,
        "tareas": tareas_a_crear,
        "mensaje_cerradas": f"{len(tareas_cerradas)} tareas cerradas",
        "ids_cerrados": tareas_cerradas
    }
