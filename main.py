from fastapi import FastAPI, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr, field_validator
from datetime import datetime
import json
import os
import re
import smtplib
from email.mime.text import MIMEText

app = FastAPI()

# =========================
# CONFIGURACIÓN EMAIL (PRODUCCIÓN)
# =========================

EMAIL_ORIGEN = os.getenv("EMAIL_ORIGEN", "vasagioempresa@gmail.com")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD", "sapq muri yaqh xyza")

def enviar_email(asunto, contenido):
    try:
        msg = MIMEText(contenido)
        msg["Subject"] = asunto
        msg["From"] = EMAIL_ORIGEN
        msg["To"] = EMAIL_ORIGEN

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(EMAIL_ORIGEN, EMAIL_PASSWORD)
            server.send_message(msg)

        print("EMAIL ENVIADO CORRECTAMENTE")

    except Exception as e:
        print("ERROR EMAIL:", str(e))


# =========================
# 🔐 AUTENTICACIÓN CRM
# =========================

USERNAME = "admin"
PASSWORD = "vasagio123"

def verificar_auth(auth: str):
    if auth != f"{USERNAME}:{PASSWORD}":
        raise HTTPException(status_code=401, detail="No autorizado")


# =========================
# CORS
# =========================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =========================
# VALIDACIONES
# =========================

def validar_telefono(valor: str):
    if not re.match(r"^\d{10}$", valor):
        raise ValueError("El teléfono debe tener 10 dígitos")
    return valor

# =========================
# CLASIFICACIÓN DE LEADS
# =========================

def clasificar_lead_medico(data):
    if "lote" in data["interes"].lower():
        return "ALTO"
    elif "distribuir" in data["interes"].lower():
        return "ALTO"
    else:
        return "MEDIO"

def clasificar_lead_paciente(data):
    if data["movilidad"] in ["V4", "V5"]:
        return "ALTO"
    elif data["movilidad"] in ["V2", "V3"]:
        return "MEDIO"
    else:
        return "BAJO"

# =========================
# MODELOS
# =========================

class Medico(BaseModel):
    nombre: str
    email: EmailStr
    telefono: str
    clinica: str
    interes: str
    mensaje: str

    @field_validator("telefono")
    def telefono_valido(cls, v):
        return validar_telefono(v)


class Paciente(BaseModel):
    nombre: str
    email: EmailStr
    talla: str
    movilidad: str
    mensaje: str


# =========================
# GUARDADO
# =========================

def guardar_dato(data, archivo):

    if not os.path.exists("data"):
        os.makedirs("data")

    ruta = f"data/{archivo}"

    if not os.path.exists(ruta):
        with open(ruta, "w") as f:
            json.dump([], f)

    with open(ruta, "r") as f:
        contenido = json.load(f)

    data["fecha"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    contenido.append(data)

    with open(ruta, "w") as f:
        json.dump(contenido, f, indent=4)


# =========================
# ENDPOINTS
# =========================

@app.get("/")
def root():
    return {"message": "VASAGIO API funcionando correctamente"}


@app.post("/medico")
def recibir_medico(medico: Medico):

    data = medico.dict()

    data["prioridad"] = clasificar_lead_medico(data)

    guardar_dato(data, "medicos.json")

    asunto = f"[{data['prioridad']}] Nuevo lead médico - VASAGIO"

    contenido = f"""
    NUEVO LEAD MÉDICO

    Prioridad: {data['prioridad']}
    Nombre: {data['nombre']}
    Email: {data['email']}
    Teléfono: {data['telefono']}
    Clínica: {data['clinica']}
    Interés: {data['interes']}
    Mensaje: {data['mensaje']}
    Fecha: {data['fecha']}
    """

    enviar_email(asunto, contenido)

    return {
        "status": "ok",
        "message": "Información médica recibida correctamente"
    }


@app.post("/paciente")
def recibir_paciente(paciente: Paciente):

    data = paciente.dict()

    data["prioridad"] = clasificar_lead_paciente(data)

    guardar_dato(data, "pacientes.json")

    asunto = f"[{data['prioridad']}] Nuevo paciente - VASAGIO"

    contenido = f"""
    NUEVO PACIENTE

    Prioridad: {data['prioridad']}
    Nombre: {data['nombre']}
    Email: {data['email']}
    Talla: {data['talla']}
    Movilidad: {data['movilidad']}
    Mensaje: {data['mensaje']}
    Fecha: {data['fecha']}
    """

    enviar_email(asunto, contenido)

    return {
        "status": "ok",
        "message": "Solicitud recibida correctamente"
    }


# =========================
# 🔒 ENDPOINTS PROTEGIDOS
# =========================

@app.get("/leads/medicos")
def obtener_medicos(authorization: str = Header(None)):

    verificar_auth(authorization)

    try:
        with open("data/medicos.json", "r") as f:
            return json.load(f)
    except:
        return []


@app.get("/leads/pacientes")
def obtener_pacientes(authorization: str = Header(None)):

    verificar_auth(authorization)

    try:
        with open("data/pacientes.json", "r") as f:
            return json.load(f)
    except:
        return []


@app.put("/leads/actualizar")
def actualizar_lead(tipo: str, index: int):

    archivo = f"data/{tipo}.json"

    try:
        with open(archivo, "r") as f:
            datos = json.load(f)

        if index < 0 or index >= len(datos):
            return {"error": "Index inválido"}

        datos[index]["estado"] = "CONTACTADO"

        with open(archivo, "w") as f:
            json.dump(datos, f, indent=4)

        return {"message": "Lead actualizado"}

    except Exception as e:
        return {"error": str(e)}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
