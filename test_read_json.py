# from utils.read_json_gmail import extraer_reuniones_json_gmail
# from dotenv import load_dotenv
# import os
# import logging

# # Configurar logging para ver los mensajes en consola
# logging.basicConfig(level=logging.INFO)

# load_dotenv()

# USUARIO = os.getenv("USUARIO_GMAIL")
# CLAVE = os.getenv("CLAVE_GMAIL")
# ASUNTO_BASE = "Reuniones JSON realizadas el"
# FECHA = "2025-04-09"  # Cambia la fecha si quieres otra

# if __name__ == "__main__":
#     reuniones = extraer_reuniones_json_gmail(USUARIO, CLAVE, ASUNTO_BASE, FECHA)
#     print("📋 Reuniones encontradas:")
#     for r in reuniones:
#         print("-", r.get("titulo"))


from utils.read_json_gmail import leer_reuniones_json, extraer_json_de_gmail
from datetime import date

from dotenv import load_dotenv
import os

load_dotenv()

USUARIO = os.getenv("GMAIL_USER")  # mildred.moreno@sofka.com.co
CLAVE_APP = os.getenv("GMAIL_APP_PASSWORD")  # la que generaste de 16 dígitos

ASUNTO = "Reuniones JSON realizadas el 2025-04-09"  # cámbialo si lo deseas probar otro día

reuniones = extraer_json_de_gmail(USUARIO, CLAVE_APP, ASUNTO)

print("📅 Reuniones extraídas:")
for r in reuniones:
    print(r)

