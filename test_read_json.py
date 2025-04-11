from utils.read_json_gmail import leer_reuniones_json, extraer_json_de_gmail
from datetime import date


from dotenv import load_dotenv
import os

load_dotenv()

USUARIO = os.getenv("GMAIL_USER")  # mildred.moreno@sofka.com.co
CLAVE_APP = os.getenv("GMAIL_APP_PASSWORD")  # la que generaste de 16 dígitos

ASUNTO = "Reuniones JSON realizadas el 2025-04-09"  # cámbialo si lo deseas probar otro día

reuniones = extraer_json_de_gmail(USUARIO, CLAVE_APP, ASUNTO)

print("✅ JSON cargado:")
for r in reuniones:
    print(f"- {r['titulo']} [{r['horaInicio']} → {r['horaFin']}]")

