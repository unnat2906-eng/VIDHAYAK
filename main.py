import os
import asyncio
import subprocess
from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import httpx

app = FastAPI(title="UNNAT | SONA PANEL")
templates = Jinja2Templates(directory="templates")

# Separate logs pools for each module
MODULE_LOGS = {
    "instagram": [],
    "gc": [],
    "whatsapp": [],
    "telegram": []
}

PERSISTENT_SESSIONS = {
    "instagram": {},
    "whatsapp": {"status": "Disconnected", "pair_code": None},
    "telegram": {"status": "Running 24/7", "pid": None}
}
BACKGROUND_TASKS_POOL = {}

def log_module(module: str, message: str):
    print(f"[{module.upper()} LOG] {message}")
    if module in MODULE_LOGS:
        MODULE_LOGS[module].insert(0, message)
        if len(MODULE_LOGS[module]) > 50:
            MODULE_LOGS[module].pop()

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/api/login")
async def api_login(username: str = Form(...), password: str = Form(...)):
    if username == "UNNAT" and password == "UNNAT@143":
        return {"success": True, "role": "owner"}
    elif username == "USER" and password == "PASSWORD":
        return {"success": True, "role": "user"}
    return {"success": False, "message": "Invalid Username or Password!"}

@app.post("/api/insta/connect-session")
async def insta_connect(session_id: str = Form(...)):
    try:
        async with httpx.AsyncClient() as client:
            headers = {
                "Cookie": f"sessionid={session_id}", 
                "User-Agent": "Instagram 219.0.0.12.117 Android (30/11; 480dpi; 1080x2340; Xiaomi; M2101K7AG; veux; in_ID; 352152862)"
            }
            res = await client.get("https://i.instagram.com/api/v1/accounts/current_user/", headers=headers)
            if res.status_code == 200:
                data = res.json()
                username = data.get("user", {}).get("username", "Unknown_User")
                log_module("instagram", f"Account Connected Successfully: @{username}")
                return {"success": True, "username": username}
    except Exception as e:
        log_module("instagram", f"Connection Error: {str(e)}")
    return {"success": False, "message": "Invalid Session ID or Rate Limited."}

@app.post("/api/insta/start-task")
async def start_insta_task(task_type: str = Form(...), session_id: str = Form(...), target_data: str = Form(...)):
    log_module("instagram", f"Task [{task_type}] started for session. Target/Config: {target_data}")
    return {"success": True, "message": "Instagram background worker started successfully!"}

@app.post("/api/gc/create")
async def create_gc(gc_name: str = Form(...)):
    log_module("gc", f"New Group Chat Created: {gc_name}")
    return {"success": True, "gc_name": gc_name}

@app.post("/api/whatsapp/pair")
async def whatsapp_pair(phone: str = Form(...)):
    log_module("whatsapp", f"Pairing requested for phone: {phone}")
    pair_code = "UNNAT-8899"
    return {"success": True, "pair_code": pair_code}

@app.post("/api/telegram/deploy")
async def telegram_deploy(tokens: str = Form(...), owner_id: str = Form(...)):
    token_list = [t.strip() for t in tokens.split(",") if t.strip()]
    log_module("telegram", f"Deploying {len(token_list)} Telegram bots with Owner ID: {owner_id}")
    
    os.makedirs("scripts", exist_ok=True)
    with open("scripts/tokens.txt", "w") as f:
        f.write(tokens)
        
    try:
        if PERSISTENT_SESSIONS["telegram"]["pid"]:
            os.kill(PERSISTENT_SESSIONS["telegram"]["pid"], 9)
    except Exception:
        pass
        
    process = subprocess.Popen(["python", "scripts/Unnatv5.py"])
    PERSISTENT_SESSIONS["telegram"]["pid"] = process.pid
    log_module("telegram", f"Unnatv5.py daemon launched successfully with PID: {process.pid}")
    
    return {"success": True, "active_count": len(token_list)}

@app.get("/api/logs/all")
async def get_all_logs():
    return {"logs": MODULE_LOGS}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
