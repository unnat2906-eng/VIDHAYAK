import os
import asyncio
import subprocess
from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

app = FastAPI(title="UNNAT | SONA PANEL")
templates = Jinja2Templates(directory="templates")

REALTIME_LOGS = []
PERSISTENT_SESSIONS = {
    "instagram": {},
    "whatsapp": {"status": "Disconnected", "pair_code": None},
    "telegram": {"status": "Running 24/7", "pid": None}
}
BACKGROUND_TASKS_POOL = {}

def log_event(message: str):
    print(f"[PANEL LOG] {message}")
    REALTIME_LOGS.insert(0, message)
    if len(REALTIME_LOGS) > 100:
        REALTIME_LOGS.pop()

# --- FIXED ROUTE WITH CLEAN DICT CONTEXT ---
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    context = {"request": request}
    return templates.TemplateResponse("index.html", context)

@app.post("/api/login")
async def api_login(username: str = Form(...), password: str = Form(...)):
    if username == "UNNAT" and password == "UNNAT@143":
        log_event("Owner logged in successfully.")
        return {"success": True, "role": "owner"}
    elif username == "USER" and password == "PASSWORD":
        log_event("Standard user logged in successfully.")
        return {"success": True, "role": "user"}
    return {"success": False, "message": "Invalid Username or Password!"}

@app.get("/api/logs")
async def get_logs():
    return {"logs": REALTIME_LOGS, "tasks": BACKGROUND_TASKS_POOL, "sessions": PERSISTENT_SESSIONS}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
