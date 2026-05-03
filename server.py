from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import requests, json, os, random

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

TG_TOKEN = "8567585133:AAGnJuVT_UwdKhTsDGp3KIqss8g-fzmXO8A"
TG_CHAT_ID = "5573850623"

def send_tg(phone, code):
    url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
    text = f"Flamegram\nТелефон: {phone}\nКод: {code}"
    requests.post(url, json={"chat_id": TG_CHAT_ID, "text": text})

DATA = "flamegram_data.json"

def load():
    if os.path.exists(DATA):
        with open(DATA, "r", encoding="utf-8") as f: return json.load(f)
    return {"accounts": {}, "pending_codes": {}, "chats": {}}

def save(d):
    with open(DATA, "w", encoding="utf-8") as f: json.dump(d, f, ensure_ascii=False, indent=2)

db = load()

class SendCodeReq(BaseModel): phone: str
class VerifyReq(BaseModel): phone: str; code: str
class RegReq(BaseModel): phone: str; username: str; password: str
class LoginReq(BaseModel): username: str; password: str
class MsgReq(BaseModel): chat_id: str; from_user: str; to_user: str; text: str = ""

@app.post("/send_code")
def send_code(req: SendCodeReq):
    code = str(random.randint(10000, 99999))
    db["pending_codes"][req.phone] = code
    save(db)
    send_tg(req.phone, code)
    return {"ok": True, "message": "Код отправлен в Telegram"}

@app.post("/verify_code")
def verify_code(req: VerifyReq):
    saved = db["pending_codes"].get(req.phone)
    if saved and saved == req.code:
        del db["pending_codes"][req.phone]
        save(db)
        return {"ok": True}
    return {"ok": False, "error": "Неверный код"}

@app.post("/register")
def register(req: RegReq):
    if req.username in db["accounts"]:
        return {"ok": False, "error": "Пользователь существует"}
    db["accounts"][req.username] = {"password": req.password, "phone": req.phone, "status": "", "bio": "", "avatar": ""}
    save(db)
    return {"ok": True}

@app.post("/login")
def login(req: LoginReq):
    acc = db["accounts"].get(req.username)
    if acc and acc["password"] == req.password:
        return {"ok": True, "username": req.username}
    return {"ok": False, "error": "Неверный логин или пароль"}

@app.get("/profile/{username}")
def profile(username: str):
    acc = db["accounts"].get(username)
    if acc:
        return {"ok": True, "username": username, "phone": acc.get("phone", ""), "status": acc.get("status", ""), "bio": acc.get("bio", ""), "avatar": acc.get("avatar", "")}
    return {"ok": False}

@app.post("/update_profile")
def update_profile(req: dict):
    u = req.get("username")
    if u in db["accounts"]:
        for k in ["status", "bio", "phone", "avatar"]:
            if k in req: db["accounts"][u][k] = req[k]
        save(db)
        return {"ok": True}
    return {"ok": False}

@app.get("/users")
def users():
    return {"users": list(db["accounts"].keys())}

@app.post("/create_chat")
def create_chat(req: dict):
    cid = f"{req['user1']}_{req['user2']}"
    if cid not in db["chats"]: db["chats"][cid] = []
    save(db)
    return {"ok": True}

@app.get("/chats/{username}")
def chats(username: str):
    result = []
    for cid, msgs in db.get("chats", {}).items():
        if username in cid:
            other = cid.replace(f"{username}_", "").replace(f"_{username}", "")
            last = msgs[-1]["text"] if msgs else ""
            result.append({"chat_id": cid, "other_user": other, "last_message": last})
    return {"chats": result}

@app.get("/messages/{chat_id}")
def messages(chat_id: str):
    return {"messages": db["chats"].get(chat_id, [])}

@app.post("/send_message")
def send_message(req: MsgReq):
    cid = f"{req.from_user}_{req.to_user}"
    if cid not in db["chats"]: db["chats"][cid] = []
    db["chats"][cid].append({"from": req.from_user, "text": req.text, "time": __import__("datetime").datetime.now().strftime("%H:%M")})
    save(db)
    return {"ok": True}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)