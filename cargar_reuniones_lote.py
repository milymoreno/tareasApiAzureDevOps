import requests
from datetime import date, timedelta
import os

def obtener_habilitador_por_fecha(fecha: date) -> int:
    if date(2025, 3, 3) <= fecha <= date(2025, 3, 9):
        return 16345
    if date(2025, 3, 10) <= fecha <= date(2025, 3, 16):
        return 16760
    elif date(2025, 3, 17) <= fecha <= date(2025, 3, 21):
        return 17301
    elif date(2025, 3, 25) <= fecha <= date(2025, 3, 28):  # lunes 24 fue festivo
        return 17476
    else:
        return 0



if __name__ == "__main__":
    import requests
    from datetime import date, timedelta
    import os

    usuario = "Mildred Moreno"
    fecha_inicio = date(2025, 3, 3)
    fecha_fin = date(2025, 3, 28)

    EXCEL_PATH = "data"
    URL = "http://localhost:8000/registrar-reuniones"

    fecha_actual = fecha_inicio
    delta = timedelta(days=1)

    while fecha_actual <= fecha_fin:
        habilitador_id = obtener_habilitador_por_fecha(fecha_actual)
        nombre_archivo = f"reuniones-outlook-{fecha_actual.strftime('%Y-%m-%d')}.xlsx"
        ruta = os.path.join(EXCEL_PATH, nombre_archivo)

        if habilitador_id and os.path.exists(ruta):
            payload = {
                "usuario": usuario,
                "habilitador_id": habilitador_id,
                "fecha": fecha_actual.strftime("%Y-%m-%d")
            }

            print(f"📅 Procesando: {nombre_archivo} (habilitador: {habilitador_id})")
            response = requests.post(URL, params=payload)

            if response.status_code == 200:
                print("✅ OK:", response.json().get("mensaje"))
            else:
                print("❌ Error:", response.status_code, response.text)
        else:
            print(f"⚠️ Archivo no encontrado o sin habilitador: {nombre_archivo}")

        fecha_actual += delta
