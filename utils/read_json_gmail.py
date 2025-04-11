import imaplib
import email
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv

import json
import pandas as pd
from typing import List, Dict



from email.header import decode_header

import logging

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


load_dotenv()

IMAP_SERVER = "imap.gmail.com"
EMAIL_ACCOUNT = os.getenv("EMAIL_GMAIL")
EMAIL_PASSWORD = os.getenv("EMAIL_GMAIL_PASSWORD")  # App Password generada
OUTPUT_DIR = "json_reuniones"

def descargar_json_adjuntos(fecha: str):
    asunto_buscado = f"Reuniones JSON realizadas el {fecha}"
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    with imaplib.IMAP4_SSL(IMAP_SERVER) as mail:
        mail.login(EMAIL_ACCOUNT, EMAIL_PASSWORD)
        mail.select("inbox")

        status, mensajes = mail.search(None, f'SUBJECT "{asunto_buscado}"')
        ids = mensajes[0].split()

        if not ids:
            print(f"❌ No se encontró ningún correo con asunto '{asunto_buscado}'")
            return None

        ultimo_id = ids[-1]
        status, datos = mail.fetch(ultimo_id, "(RFC822)")
        raw_email = datos[0][1]
        mensaje = email.message_from_bytes(raw_email)

        for parte in mensaje.walk():
            if parte.get_content_disposition() == "attachment" and parte.get_filename().endswith(".json"):
                nombre_archivo = parte.get_filename()
                ruta_archivo = os.path.join(OUTPUT_DIR, nombre_archivo)
                with open(ruta_archivo, "wb") as f:
                    f.write(parte.get_payload(decode=True))
                print(f"✅ Archivo JSON descargado: {ruta_archivo}")
                return ruta_archivo

        print("⚠️ No se encontró archivo .json adjunto en el correo.")
        return None


def leer_reuniones_json(ruta_archivo: str) -> List[Dict]:
    with open(ruta_archivo, "r", encoding="utf-8") as f:
        reuniones = json.load(f)

    # Convertir strings de fecha a objetos datetime si hace falta
    for reunion in reuniones:
        reunion["horaInicio"] = pd.to_datetime(reunion["horaInicio"])
        reunion["horaFin"] = pd.to_datetime(reunion["horaFin"])
        reunion["fecha"] = reunion["horaInicio"].date()
        reunion["duracion_horas"] = (reunion["horaFin"] - reunion["horaInicio"]).total_seconds() / 3600

    return reuniones

# ✅ Esta es tu función principal para extraer el JSON, ya sea del cuerpo o del adjunto

def extraer_reuniones_json_gmail(usuario, clave_app, asunto_filtro, fecha_objetivo):  

    mail = imaplib.IMAP4_SSL("imap.gmail.com")
    mail.login(usuario, clave_app)
    mail.select("inbox")

    # Filtrar por correos de los últimos 3 días
    fecha_limite = (datetime.now() - timedelta(days=3)).strftime('%d-%b-%Y')

    status, mensajes = mail.search(None, f'(SINCE {fecha_limite})')
    correos_ids = mensajes[0].split()[::-1]

    for correo_id in correos_ids:
        res, msg_data = mail.fetch(correo_id, "(RFC822)")
        if res != "OK":
            continue

        raw_email = msg_data[0][1]
        mensaje = email.message_from_bytes(raw_email)

        subject_raw = mensaje["Subject"]
        logger.info(f"🔍 Revisando correo con raw subject: {subject_raw}")

        if not subject_raw:
            logger.warning("⚠️ Correo sin asunto. Saltando...")
            continue

        asunto = decode_header(subject_raw)[0][0]
        if isinstance(asunto, bytes):
            asunto = asunto.decode("utf-8")
        logger.info(f"📧 Asunto decodificado: {asunto}")

        if not asunto.startswith(asunto_filtro):
            continue

        # 1️⃣ Leer JSON del cuerpo
        if mensaje.is_multipart():
            for parte in mensaje.walk():
                content_type = parte.get_content_type()
                content_disposition = str(parte.get("Content-Disposition"))

                if "attachment" not in content_disposition and content_type == "text/plain":
                    cuerpo = parte.get_payload(decode=True).decode("utf-8")
                    try:
                        reuniones = json.loads(cuerpo.strip())
                        logger.info("✅ JSON encontrado en el cuerpo del mensaje")
                        return reuniones
                    except Exception as e:
                        logger.warning(f"⚠️ Error procesando cuerpo como JSON: {e}")

        else:
            cuerpo = mensaje.get_payload(decode=True).decode("utf-8")
            try:
                reuniones = json.loads(cuerpo.strip())
                logger.info("✅ JSON encontrado en el cuerpo del mensaje (sin multipart)")
                return reuniones
            except Exception as e:
                logger.warning(f"⚠️ Error procesando cuerpo como JSON: {e}")

        # 2️⃣ Si no está en el cuerpo, buscar adjunto .json
        for parte in mensaje.walk():
            if parte.get_content_disposition() == "attachment" and parte.get_filename().endswith(".json"):
                nombre_archivo = parte.get_filename()
                ruta_archivo = os.path.join("data", nombre_archivo)
                with open(ruta_archivo, "wb") as f:
                    f.write(parte.get_payload(decode=True))
                logger.info(f"📎 JSON descargado desde adjunto: {ruta_archivo}")
                with open(ruta_archivo, "r", encoding="utf-8") as f:
                    return json.load(f)

    logger.warning("❌ No se encontró correo con JSON válido.")
    return []


def extraer_json_de_gmail(usuario, clave_app, asunto_filtro):
    mail = imaplib.IMAP4_SSL("imap.gmail.com")
    mail.login(usuario, clave_app)
    mail.select("inbox")

    #status, mensajes = mail.search(None, 'ALL')    
   
    fecha_limite = (datetime.now() - timedelta(days=3)).strftime('%d-%b-%Y')
    status, mensajes = mail.search(None, f'(SINCE {fecha_limite})')

        
    correos_ids = mensajes[0].split()[::-1]  # buscar desde el más reciente

    for correo_id in correos_ids:
        res, msg_data = mail.fetch(correo_id, "(RFC822)")
        if res != "OK":
            continue

        raw_email = msg_data[0][1]
        mensaje = email.message_from_bytes(raw_email)

        subject_raw = mensaje["Subject"]
        logger.info(f"🔍 Revisando correo con raw subject: {subject_raw}")

        if not subject_raw:
            logger.warning("⚠️ Correo sin asunto. Saltando...")
            continue

        asunto = decodificar_asunto(mensaje["Subject"])
        logger.info(f"📧 Asunto decodificado: {asunto}")

        # if not asunto.startswith(asunto_filtro):
        #     logger.debug(f"📛 Asunto no coincide: '{asunto}' vs filtro '{asunto_filtro}'")
        #     continue
        
        if asunto.startswith(asunto_filtro):
            logger.info("✅ Asunto coincide, inspeccionando partes del mensaje...")
            for parte in mensaje.walk():
                content_type = parte.get_content_type()
                content_disposition = str(parte.get("Content-Disposition"))
                filename = parte.get_filename()
                logger.info(f"📦 Parte encontrada: content_type={content_type}, disposition={content_disposition}, filename={filename}")

        if mensaje.is_multipart():
            for parte in mensaje.walk():
                content_type = parte.get_content_type()
                content_disposition = str(parte.get("Content-Disposition"))
                logger.debug(f"🔍 Parte encontrada: content_type={content_type}, disposition={content_disposition}")
                logger.debug(f"📦 Parte: content_type={content_type}, disposition={content_disposition}, filename={parte.get_filename()}")


                # ✅ Buscar cuerpo del mensaje con JSON
                if "attachment" not in content_disposition and content_type == "text/plain":
                    cuerpo = parte.get_payload(decode=True).decode()
                    logger.debug(f"📨 Cuerpo recibido:\n{cuerpo}")
                    try:
                        return json.loads(cuerpo.strip())
                    except Exception as e:
                        logger.warning(f"⚠️ Error procesando cuerpo como JSON: {e}")
                
        else:
            cuerpo = mensaje.get_payload(decode=True).decode()
            try:
                return json.loads(cuerpo.strip())
            except Exception as e:
               logger.warning(f"⚠️ Error procesando cuerpo como JSON: {e}")

    logger.warning("❌ No se encontró correo con el asunto esperado.")
    return []


def decodificar_asunto(subject_raw):
    decoded = decode_header(subject_raw)
    subject_final = ""
    for parte, codificacion in decoded:
        if isinstance(parte, bytes):
            subject_final += parte.decode(codificacion or "utf-8", errors="ignore")
        else:
            subject_final += parte
    return subject_final


def redondear_duracion(duracion):
    """
    Redondea una duración en horas al múltiplo más cercano de 0.25.
    Ejemplos:
        0.13 → 0.25
        0.37 → 0.5
        1.78 → 1.75
    """
    return round(duracion * 4) / 4

