from fastapi import FastAPI, Query
from dotenv import load_dotenv
import os
import pandas as pd
from datetime import date,datetime, time
import random

import logging

from services.azure_client import (
    obtener_proyecto_predeterminado,
    obtener_habilitador_semanal
)

from utils.reuniones_excel import leer_reuniones_excel
from utils.read_json_gmail import leer_reuniones_json

from config import EXCEL_PATH

TITULOS_TAREA_GENERICA = [
    "Revisión de Logs y Azure Portal",
    "Apoyo a QA y Validaciones",
    "Tareas generales de Base de Datos",
    "Apoyo a despliegues y configuración",
    "Investigación técnica interna"
]

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
#logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")

from utils.pr_json import cargar_prs_revisados_por_fecha


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

# Configuración del logger global
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

logger.info("🚀 Iniciando API de Registro de Reuniones en Azure DevOps")

# Cargar variables del .env
load_dotenv()

app = FastAPI()

@app.get("/")
def read_root():
    return {"mensaje": "🚀 API de Registro de Reuniones en Azure DevOps funcionando"}


@app.get("/obtener-habilitador-semanal")
def obtener_habilitador_semanal_endpoint(
    fecha: str = Query(...)
):
    try:
        logger.info(f"📥 Fecha recibida vía parámetro: {fecha}")
        habilitador_id = obtener_habilitador_semanal(fecha)

        logger.info(f"✅ Habilitador encontrado (ID: {habilitador_id})")
        return {"id": habilitador_id}

    except Exception as e:
        logger.exception("❌ Error al obtener habilitador semanal")
        return {"error": str(e)}





@app.post("/registrar-reuniones")
def registrar_reuniones(
    habilitador_id: int = Query(None),
    usuario: str = Query("Mildred Moreno"),
    fecha: str = Query(..., embed=True)  # formato esperado: "AAAA-MM-dd"
):
    try:
        logger.info(f"📥 Fecha recibida: {fecha}")
        logger.info(f"👤 Usuario recibido: {usuario}")
        fecha_actual = datetime.strptime(fecha, "%Y-%m-%d").date()

        # Si no se pasa el habilitador_id, intentar obtenerlo automáticamente
        if not habilitador_id or habilitador_id <= 0:
            logger.info("🔄 Habilitador no proporcionado o inválido. Buscando automáticamente...")            
            habilitador_id = obtener_habilitador_semanal(fecha)  # ✅ Ya estás obteniendo directamente el ID
            logger.info(f"✅ Habilitador automático encontrado: {habilitador_id}")

        nombre_archivo = f"reuniones-outlook-{fecha_actual.strftime('%Y-%m-%d')}.xlsx"
        ruta_archivo = os.path.join(EXCEL_PATH, nombre_archivo)

        logger.info(f"📥 Iniciando validación de reuniones desde {nombre_archivo} para habilitador {habilitador_id}")

        reuniones = leer_reuniones_excel(ruta_archivo)
        if not reuniones:
            return {"mensaje": "No hay reuniones en el archivo."}

        logger.info(f"📆 Fecha de ejecución: {fecha_actual}")
        
        tareas_existentes = obtener_actividades_dia(usuario, fecha_actual)
        #tareas_existentes = obtener_horas_totales_del_dia(usuario, fecha_actual)
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
            "archivo": nombre_archivo,
            "mensaje": f"{len(tareas_a_crear)} reuniones registradas exitosamente",
            "horas_registradas": total_horas_registradas,
            "horas_restantes": horas_disponibles,
            "tareas": tareas_a_crear,
            "mensaje_cerradas": f"{len(tareas_cerradas)} tareas cerradas",
            "ids_cerrados": tareas_cerradas
        }

    except Exception as e:
        logger.error(f"❌ Error en el registro de reuniones: {e}", exc_info=True)
        return {"error": str(e)}
    

@app.post("/registrar-revision-prs")
def registrar_revision_prs(
    habilitador_id: int = Query(None),
    usuario: str = Query("Mildred Moreno"),
    fecha: str = Query(...)
):
    try:
        logging.info(f"📥 Fecha recibida vía parámetro: {fecha}")

        if not habilitador_id:
            try:
                habilitador_id = obtener_habilitador_semanal(fecha)
                logging.info(f"📌 Habilitador obtenido automáticamente: {habilitador_id}")
            except Exception as e:
                logging.warning(f"⚠️ No se pudo obtener habilitador automático: {e}")
                return {"error": "Debe especificar un habilitador válido o asegurarse que uno automático esté disponible para la fecha."}

        prs = cargar_prs_revisados_por_fecha(fecha)
        logging.info(f"📦 PRs cargados correctamente. Total: {len(prs)}")

        prs_aprobados = [pr for pr in prs.values() if pr.get("estado") == "aprobado"]
        if not prs_aprobados:
            logging.warning("⚠️ No se encontraron PRs aprobados para registrar actividad.")
            return {"mensaje": "No hay PRs aprobados para registrar."}

        repositorios = sorted(set(pr["repositorio"] for pr in prs_aprobados if pr.get("repositorio")))
        descripcion = (
            "Se revisaron y aprobaron PRs correspondientes a los siguientes repositorios: "
            + ", ".join(repositorios) + "."
        )

        cantidad_prs = len(prs_aprobados)
        minutos_totales = cantidad_prs * 10
        horas_estimadas = round((minutos_totales / 60) * 2) / 2  # redondea a múltiplos de .5
        duracion = min(max(0.5, horas_estimadas), 2.5)

        fecha_dt = datetime.strptime(fecha, "%Y-%m-%d")
        horas_info = obtener_horas_totales_del_dia(usuario, fecha)
        horas_existentes = horas_info.get("total_horas", 0.0)
        horas_disponibles = max(0.0, 9.0 - horas_existentes)

        if duracion > horas_disponibles:
            logging.info(f"⛔ Ajustando duración. Disponible: {horas_disponibles:.2f}h, calculado: {duracion:.2f}h")
            duracion = horas_disponibles

        hora_fin = datetime.combine(fecha_dt.date(), time(hour=17, minute=10))

        logging.info(f"📅 TargetDate (fecha objetivo): {fecha_dt.date().isoformat()}")
        logging.info(f"🕓 FinishDate (hora fin): {hora_fin.isoformat()}")
        logging.info(f"⏱️ Duración estimada final: {duracion:.2f} horas")

        payload = generar_payload_tarea(
            titulo="Revisión y Aprobación de PRs",
            descripcion=descripcion,
            usuario=usuario,
            duracion_horas=duracion,
            fecha=hora_fin,  # 🟢 aquí va datetime completo como en reuniones
            #fecha = hora_fin.date(),
            hora_fin=hora_fin,
            habilitador_id=habilitador_id
        )

        resultado = crear_tarea_en_azure(payload, proyecto="P2P Project")

        if resultado["success"]:
            logger.info(f"✅ Actividad de revisión PRs creada: ID {resultado['id']}")
            cerradas = cerrar_tareas_por_fecha(usuario, fecha_dt.date(), "P2P Project")
            return {
                "mensaje": "Actividad registrada con éxito.",
                "id": resultado["id"],
                "tareas_cerradas": cerradas
            }
        else:
            logging.error(f"❌ Error al registrar tarea: {resultado['status_code']}")
            return {"error": resultado["error"], "status_code": resultado["status_code"]}

    except FileNotFoundError as e:
        logging.error(str(e))
        return {"error": str(e)}
    except Exception as ex:
        logging.exception("❌ Error inesperado")
        return {"error": str(ex)}



@app.post("/registrar-tarea-generica")
def registrar_tarea_generica(
    fecha: str = Query(...),
    usuario: str = Query("Mildred Moreno"),
    habilitador_id: int = Query(None)
):
    try:
        logger.info(f"📥 Fecha recibida: {fecha} - Usuario: {usuario}")

        # Aceptar fecha con formato completo tipo: 2025-04-04T12:45:00.0000000
        fecha_dt = pd.to_datetime(fecha)
        fecha_iso = fecha_dt.isoformat()

        logger.info("📊 Verificando horas ya registradas...")
        horas_info = obtener_horas_totales_del_dia(usuario, fecha_dt.date())
        horas_actuales = horas_info["total_horas"]
        logger.info(f"🕒 Horas acumuladas el {fecha_dt.date()}: {horas_actuales:.2f}")

        if horas_actuales >= 9.0:
            logger.info("✅ Ya se cumplieron las 9 horas. No se requiere tarea adicional.")
            return {"mensaje": "No se requiere tarea adicional. Ya se cumplieron las 9 horas."}

        # Calcular horas faltantes
        horas_faltantes = round(9.0 - horas_actuales, 2)
        logger.info(f"🟨 Horas a completar: {horas_faltantes:.2f}")

        # Obtener habilitador si no viene explícitamente
        if not habilitador_id:
            try:
                habilitador_id = obtener_habilitador_semanal(fecha)  # ← ya retorna directamente el ID
                logger.info(f"🔄 Habilitador detectado automáticamente: {habilitador_id}")
            except Exception as e:
                logger.error("❌ No se encontró habilitador automático ni fue proporcionado uno.")
                return {"error": "No se encontró habilitador automático ni fue proporcionado uno."}


        # Elegir título aleatorio
        titulo = random.choice(TITULOS_TAREA_GENERICA)

        hora_fin = datetime.combine(fecha_dt.date(), time(hour=17, minute=10))
              
        logging.info(f"🕓 FinishDate (hora fin): {hora_fin.isoformat()}")
        logging.info(f"⏱️ Horas estimadas: {horas_faltantes:.2f} horas")       
       
        payload = generar_payload_tarea(
            titulo=titulo,
            descripcion="",
            usuario=usuario,
            duracion_horas=horas_faltantes,
            fecha=hora_fin,
            hora_fin=hora_fin,
            habilitador_id=habilitador_id
        )

        resultado = crear_tarea_en_azure(payload, proyecto=obtener_proyecto_predeterminado())
        # Después de crear la tarea
        if resultado["success"]:
            logger.info(f"✅ Tarea genérica creada: ID {resultado['id']} - {titulo}")

            # 🔒 Cierre automático de tareas abiertas
            proyecto = obtener_proyecto_predeterminado()
            tareas_cerradas = cerrar_tareas_por_fecha(usuario, fecha_dt.date(), proyecto)
            logger.info(f"🔐 Tareas cerradas: {tareas_cerradas}")

            return {
                "mensaje": "Tarea genérica registrada",
                "id": resultado["id"],
                "titulo": titulo,
                "tareas_cerradas": tareas_cerradas
            }
            
    except Exception as e:
        logger.exception("❌ Error inesperado en tarea genérica")
        return {"error": str(e)}


@app.get("/total-horas-dia")
def total_horas_dia_endpoint(
    usuario: str = Query(..., embed=True),
    fecha: str = Query(..., embed=True)
):
    try:
        logger.info(f"📅 Calculando horas totales para {usuario} en {fecha}")
        fecha_dt = datetime.strptime(fecha, "%Y-%m-%d").date()

        horas = obtener_horas_totales_del_dia(usuario, fecha_dt)
        total = horas['total_horas']
        logger.info(f"⏱️ Total horas registradas: {total:.2f}")

        # Evaluar el mensaje
        if total == 9.0:
            estado = "✅ ¡Día completado!"
        elif total > 9.0:
            estado = f"⚠️ ¡Sobrepasaste las 9 horas por {total - 9:.2f} horas!"
        else:
            estado = f"⏳ Aún faltan {9.0 - total:.2f} horas para completar el día."

        return {
            "usuario": usuario,
            "fecha": fecha,
            "horas_trabajadas": total,
            "mensaje": estado,
            "detalle": horas["items"]
        }

    except Exception as e:
        logger.exception("❌ Error al calcular horas totales")
        return {"error": str(e)}


    
@app.post("/cerrar-tareas-dia")
def cerrar_tareas_dia(
    usuario: str = Query(..., embed=True),
    fecha: str = Query(..., embed=True)
):
    try:
        fecha_obj = datetime.strptime(fecha, "%Y-%m-%d").date()
    except ValueError:
        return {"error": "Formato de fecha inválido. Usa YYYY-MM-DD."}

    proyecto = obtener_proyecto_predeterminado()
    tareas_cerradas = cerrar_tareas_por_fecha(usuario, fecha_obj, proyecto)

    return {
        "mensaje": f"{len(tareas_cerradas)} tareas cerradas",
        "ids_cerrados": tareas_cerradas
    }
    
@app.get("/estado-horas-habilitador")
def estado_horas_habilitador(
    usuario: str = Query(..., description="Nombre del usuario asignado (ej: Mildred Moreno)"),
    fecha: str = Query(..., description="Fecha en formato YYYY-MM-DD"),
    habilitador_id: int = Query(..., description="ID del habilitador semanal")
):
    try:
        fecha_obj = datetime.strptime(fecha, "%Y-%m-%d").date()
    except ValueError:
        return {"error": "Formato de fecha inválido. Usa YYYY-MM-DD."}

    proyecto = obtener_proyecto_predeterminado()

    resultado = obtener_horas_por_habilitador_y_fecha(usuario, fecha_obj, habilitador_id, proyecto)

    return resultado
   
