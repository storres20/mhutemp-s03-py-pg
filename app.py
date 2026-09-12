from fastapi import (
    FastAPI,
    WebSocket,
    WebSocketDisconnect,
    HTTPException
)

from fastapi.middleware.cors import CORSMiddleware

from pydantic import BaseModel

from datetime import datetime, timezone

from contextlib import asynccontextmanager

import time


from database import (
    test_connection,
    init_database,
    insert_measurement,
    get_measurements
)


# =========================================================
# STARTUP
# =========================================================

@asynccontextmanager
async def lifespan(app: FastAPI):

    test_connection()

    init_database()

    yield


# =========================================================
# APP
# =========================================================

app = FastAPI(
    title="MHUTEMP Stack 03",
    version="1.0.0",
    lifespan=lifespan
)


# =========================================================
# CORS
# =========================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",

        # Más adelante colocaremos aquí:
        # https://mhutemp-s03-nextjs.netlify.app
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =========================================================
# WEBSOCKET CLIENTS
# =========================================================

connected_clients = {}


# =========================================================
# LOGIN MODEL
# =========================================================

class LoginRequest(BaseModel):

    username: str
    password: str


# =========================================================
# ROOT
# =========================================================

@app.get("/")
def root():

    return {
        "system": "MHUTEMP",
        "stack": "03",
        "backend": "Python / FastAPI",
        "database": "PostgreSQL",
        "status": "running"
    }


# =========================================================
# LOGIN DEMO
# =========================================================

@app.post("/api/auth/login")
def login(data: LoginRequest):

    if (
        data.username == "doctor03"
        and data.password == "123456"
    ):

        return {

            "user": {

                "username": "doctor03",

                "hospital": {
                    "_id": "stack03-hospital",
                    "name": "MHUTEMP Stack 03 Test Site"
                },

                "area": {
                    "_id": "stack03-area",
                    "name": "Experimental Monitoring Area"
                }

            },

            "token": "stack03-demo-token"

        }


    raise HTTPException(
        status_code=401,
        detail="Invalid credentials"
    )


# =========================================================
# DEVICE
# =========================================================

@app.get("/api/devices/by-sensor/{username}")
def get_device_by_sensor(
    username: str
):

    if username == "BLD-prueba":

        return {

            "_id":
                "stack03-device-001",

            "name":
                "MHUTEMP Test Node",

            "brand":
                "MHUTEMP",

            "model":
                "Stack 03 Experimental Node",

            "serie":
                "BLD-prueba",

            "assigned_sensor_username":
                "BLD-prueba",

            "hospital": {
                "_id":
                    "stack03-hospital",

                "name":
                    "MHUTEMP Stack 03 Test Site"
            },

            "area": {
                "_id":
                    "stack03-area",

                "name":
                    "Experimental Monitoring Area"
            }

        }


    raise HTTPException(
        status_code=404,
        detail="Device not found"
    )


# =========================================================
# REST - TODAS LAS MEDICIONES
# =========================================================

@app.get("/api/measurements")
def measurements_all(
    limit: int = 20
):

    limit = min(
        max(limit, 1),
        100
    )

    return get_measurements(
        limit=limit
    )


# =========================================================
# REST - MEDICIONES POR NODO
# =========================================================

@app.get("/api/measurements/{username}")
def measurements_by_node(
    username: str,
    limit: int = 20
):

    limit = min(
        max(limit, 1),
        100
    )

    return get_measurements(
        username=username,
        limit=limit
    )


# =========================================================
# WEBSOCKET
# =========================================================

@app.websocket("/")
async def websocket_endpoint(
    websocket: WebSocket
):

    await websocket.accept()

    username = None

    print(
        "WebSocket conectado"
    )


    try:

        while True:

            data = await websocket.receive_json()


            # =============================================
            # PING / PONG
            # =============================================

            if data.get("type") == "ping":

                await websocket.send_json(
                    {
                        "type": "pong",

                        "timestamp":
                            int(
                                time.time()
                                * 1000
                            )
                    }
                )

                print(
                    "PING recibido → "
                    "PONG enviado"
                )

                continue


            # =============================================
            # IDENTIFICACIÓN
            # =============================================

            if (
                "username" in data
                and len(data) == 1
            ):

                username = data[
                    "username"
                ]

                connected_clients[
                    username
                ] = websocket

                print(
                    f"Nodo identificado: "
                    f"{username}"
                )

                continue


            # =============================================
            # MEDICIÓN
            # =============================================

            if "username" in data:

                username = data[
                    "username"
                ]


                document = {

                    "username":
                        data.get(
                            "username"
                        ),

                    "dsTemperature":
                        data.get(
                            "dsTemperature"
                        ),

                    "temperature":
                        data.get(
                            "temperature"
                        ),

                    "humidity":
                        data.get(
                            "humidity"
                        ),

                    "datetime":
                        data.get(
                            "datetime"
                        ),

                    "doorStatus":
                        data.get(
                            "doorStatus"
                        ),

                    "receivedAt":
                        datetime.now(
                            timezone.utc
                        )

                }


                # =========================================
                # POSTGRESQL
                # =========================================

                insert_measurement(
                    document
                )


                print(

                    f"Medición guardada | "

                    f"{username} | "

                    f"DS: "
                    f"{data.get('dsTemperature')} | "

                    f"T: "
                    f"{data.get('temperature')} | "

                    f"H: "
                    f"{data.get('humidity')} | "

                    f"Door: "
                    f"{data.get('doorStatus')}"

                )


                # =========================================
                # BROADCAST
                # =========================================

                broadcast_data = {

                    "username":
                        document["username"],

                    "dsTemperature":
                        document["dsTemperature"],

                    "temperature":
                        document["temperature"],

                    "humidity":
                        document["humidity"],

                    "datetime":
                        document["datetime"],

                    "doorStatus":
                        document["doorStatus"]

                }


                disconnected = []


                for (
                    client_name,
                    client_ws
                ) in list(
                    connected_clients.items()
                ):

                    try:

                        await client_ws.send_json(
                            broadcast_data
                        )

                    except Exception:

                        disconnected.append(
                            client_name
                        )


                for client_name in disconnected:

                    connected_clients.pop(
                        client_name,
                        None
                    )


    except WebSocketDisconnect:

        print(
            f"WebSocket desconectado: "
            f"{username}"
        )


    except Exception as e:

        print(
            f"Error WebSocket: {e}"
        )


    finally:

        if username:

            connected_clients.pop(
                username,
                None
            )