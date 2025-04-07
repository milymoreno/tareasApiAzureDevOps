from fastapi import FastAPI, Request
from pydantic import BaseModel
from typing import List
from datetime import datetime

app = FastAPI()

class Reunion(BaseModel):
    titulo: str
    horaInicio: datetime
    horaFin: datetime
    organizador: str

@app.post("/reuniones-outlook")
async def recibir_reuniones(reuniones: List[Reunion]):
    print("📥 Reuniones recibidas:")
    for reunion in reuniones:
        print(f"📅 {reunion.titulo} — {reunion.horaInicio} ➡️ {reunion.horaFin} (organizador: {reunion.organizador})")
    return {"mensaje": "Reuniones recibidas correctamente"}
