from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import json, os, random, datetime

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

DATA = "flamegram_data.json"

def load():
    if os.path.exists(DATA):
        with open(DATA, "r") as f:
            d = json.load(f)
            d.setdefault("chats", {})
            return d
    return {"accounts": {}, "pending_codes": {}, "chats": {}}

def save(d):
    with open(DATA, "w") as f: json.dump(d, f, ensure_ascii=False, indent=2)

db = load()

# WebSocket соединения
active_connections: dict[str, WebSocket] = {}

@app.websocket("/ws/{username}")
async def websocket_endpoint(websocket: WebSocket, username: str):
    await websocket.accept()
    active_connections[username] = websocket
    try:
        while True:
            data = await websocket.receive_json()
            action = data.get("action")
            
            if action == "mark_read":
                chat_id = data["chat_id"]
                for msg in db["chats"].get(chat_id, []):
                    if msg["from"] != username:
                        msg["read"] = True
                save(db)
                # Уведомить отправителя
                other = chat_id.replace(f"{username}_", "").replace(f"_{username}", "")
                if other in active_connections:
                    await active_connections[other].send_json({"action": "read", "chat_id": chat_id})
                    
            elif action == "typing":
                chat_id = data["chat_id"]
                other = chat_id.replace(f"{username}_", "").replace(f"_{username}", "")
                if other in active_connections:
                    await active_connections[other].send_json({"action": "typing", "from": username})
    except WebSocketDisconnect:
        active_connections.pop(username, None)
