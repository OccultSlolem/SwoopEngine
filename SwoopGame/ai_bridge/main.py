from typing import Union
from fastapi import FastAPI, WebSocket

app = FastAPI()

@app.get("/")
def read_root():
    return { "Hello": "World" }

@app.websocket("/ws")
async def websocket(websocket: WebSocket):
    await websocket.accept()
    while True:
        data = await websocket.receive_text()
        await websocket.send_text(data)
