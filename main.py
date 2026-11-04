import os
import json
import time
import random
import threading
import collections
import asyncio
from pathlib import Path
from flask import Flask, render_template, request, jsonify
from instagrapi import Client
from playwright.sync_api import sync_playwright
import werkzeug

app = Flask(__name__)
DATA_FILE = "data.json"
UPLOAD_FOLDER = "uploads"
SESSIONS_FOLDER = "sessions"

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(SESSIONS_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

BASE = Path(__file__).parent
SETTINGS_DIR = BASE / "sessions_settings"
SETTINGS_DIR.mkdir(exist_ok=True)

data_lock = threading.Lock()

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE) as f:
            try:
                return json.load(f)
            except:
                pass
    return {"accounts": {}, "creators": {}, "spammers": {}, "telegram_bots": {}, "uploaded_files": {}, "global_sessions": []}

def save_data(d):
    with open(DATA_FILE, "w") as f:
        json.dump(d, f, indent=2)

bot_threads = {}
bot_stop = {}
bot_status = {}
bot_logs = {}

def log(task_id, msg):
    ts = time.strftime("%H:%M:%S")
    line = f"[{ts}] {msg}"
    if task_id not in bot_logs:
        bot_logs[task_id] = collections.deque(maxlen=200)
    bot_logs[task_id].append(line)

def extract_thread_id(s):
    if not s:
        return ""
    s = str(s).strip()
    if "instagram.com/direct/t/" in s:
        parts = s.rstrip("/").split("/")
        for p in parts:
            if p.isdigit():
                return p
    if s.isdigit():
        return s
    return s

# --- PLAYWRIGHT + API MIX WORKER FOR MULTI GC SPAM ---
def bot_worker(task_id, cfg, stop_event):
    groups = [extract_thread_id(g) for g in cfg.get("groups", "").split("\n") if g.strip()]
    messages = [m.strip() for m in cfg.get("message", "").split(",") if m.strip()]
    delay = float(cfg.get("delay", 2))
    nc_configs = cfg.get("nc_configs", [])
    session_id = cfg.get("session_id", "").strip()

    bot_logs[task_id] = collections.deque(maxlen=200)
    bot_status[task_id] = {"running": True, "sent": 0, "failed": 0, "last_action": "Launching Playwright Engine...", "started_at": time.time()}
    log(task_id, f"🕷️ Starting Playwright + API Mix Multi GC Bot (24/7 Persistent)...")

    if not groups or not messages:
        log(task_id, "❌ No groups or messages provided!")
        bot_status[task_id]["running"] = False
        return

    cl = Client()
    if session_id:
        try:
            cl.login_by_sessionid(session_id)
            log(task_id, "✅ Instagrapi API client initialized successfully for NC updates.")
        except Exception as e:
            log(task_id, f"⚠️ API client login warning: {e}")

    msg_idx = 0
    nc_timers = [0] * len(nc_configs)

    while not stop_event.is_set():
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(
                    headless=True,
                    args=["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage"]
                )
                context = browser.new_context(
                    user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 16_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 Instagram 284.0.0.21.114 (iPhone14,3; iOS 16_5; en_US; en-US; scale=3.00; 1284x2778; 471924622)"
                )
                if session_id:
                    context.add_cookies([{"name": "sessionid", "value": session_id, "domain": ".instagram.com", "path": "/"}])
                
                page = context.new_page()
                log(task_id, "✅ Playwright browser session initialized successfully.")

                while not stop_event.is_set():
                    for group_id in groups:
                        if stop_event.is_set():
                            break
                        curr_msg = messages[msg_idx % len(messages)]
                        bot_status[task_id]["last_action"] = f"Sending message to GC {group_id}"
                        try:
                            page.goto(f"https://www.instagram.com/direct/t/{group_id}/", timeout=35000)
                            page.wait_for_timeout(2500)
                            
                            page.fill('div[contenteditable="true"]', curr_msg)
                            page.keyboard.press("Enter")
                            
                            bot_status[task_id]["sent"] += 1
                            log(task_id, f"✅ Sent via Playwright to {group_id}: {curr_msg[:30]}...")
                        except Exception as e:
                            bot_status[task_id]["failed"] += 1
                            log(task_id, f"❌ Failed {group_id}: {e}")
                        
                        msg_idx += 1
                        time.sleep(delay)

                    if nc_configs and not stop_event.is_set():
                        current_time = time.time()
                        for i, nc in enumerate(nc_configs):
                            if stop_event.is_set():
                                break
                            nc_text = nc.get("text", "").strip()
                            nc_delay = float(nc.get("delay", 30))
                            if nc_text and (current_time - nc_timers[i] >= nc_delay):
                                bot_status[task_id]["last_action"] = f"Changing NC to: {nc_text}"
                                for group_id in groups:
                                    if stop_event.is_set():
                                        break
                                    try:
                                        cl.direct_thread_update_title(int(group_id), nc_text)
                                        log(task_id, f"✨ NC Updated for {group_id}: {nc_text}")
                                        time.sleep(2)
                                    except Exception as ex:
                                        log(task_id, f"⚠️ NC Update warning ({group_id}): {ex}")
                                nc_timers[i] = time.time()

                browser.close()
        except Exception as worker_err:
            log(task_id, f"⚠️ Playwright session disconnected: {worker_err}. Reconnecting in 5s...")
            time.sleep(5)

    log(task_id, "🛑 Multi GC Bot Stopped.")
    bot_status[task_id]["running"] = False

# --- INSTAGRAM GC CREATOR WORKER ---
def remove_user_from_thread(cl, thread_id, user_id):
    try:
        cl.private.post(
            f"https://i.instagram.com/api/v1/direct_v2/threads/{thread_id}/remove_users/",
            data={"user_ids": f"[{user_id}]"}
        )
    except:
        pass

def gc_creator_worker(task_id, cfg, stop_event):
    session_id = cfg.get("session_id", "").strip()
    usernames = [u.strip() for u in cfg.get("usernames", "").replace(",", "|").split("|") if u.strip()]
    remove_users = [u.strip() for u in cfg.get("remove_users", "").split(",") if u.strip()]
    gc_count = int(cfg.get("gc_count", 1))
    delay = float(cfg.get("delay", 2))

    bot_logs[task_id] = collections.deque(maxlen=200)
    bot_status[task_id] = {"running": True, "created": 0, "failed": 0, "last_action": "Logging in for GC Creation...", "started_at": time.time()}
    log(task_id, "🕷️ Starting Instagram GC Creator Loop...")

    cl = Client()
    try:
        cl.login_by_sessionid(session_id)
        acc_info = cl.account_info()
        log(task_id, f"✅ Logged in successfully as @{acc_info.username}")
    except Exception as e:
        log(task_id, f"❌ Login failed: {e}")
        bot_status[task_id]["running"] = False
        return

    try:
        user_ids = [cl.user_id_from_username(u) for u in usernames if u]
        remove_user_id = cl.user_id_from_username(remove_users[0]) if remove_users else None
    except Exception as e:
        log(task_id, f"❌ User resolve failed: {e}")
        bot_status[task_id]["running"] = False
        return

    created_total = 0
    while created_total < gc_count and not stop_event.is_set():
        try:
            bot_status[task_id]["last_action"] = f"Creating GC #{created_total + 1}"
            cl.direct_send("GC Created Successfully", user_ids=user_ids)
            time.sleep(3)
            threads = cl.direct_threads(amount=1)
            if not threads:
                bot_status[task_id]["failed"] += 1
                continue
            thread_id = str(threads[0].id)
            time.sleep(1)
            if remove_user_id:
                remove_user_from_thread(cl, thread_id, remove_user_id)
                log(task_id, f"👤 Removed user from GC ID: {thread_id}")
            created_total += 1
            bot_status[task_id]["created"] = created_total
            log(task_id, f"✅ Created GC #{created_total} (ID: {thread_id})")
        except Exception as e:
            bot_status[task_id]["failed"] += 1
            log(task_id, f"❌ GC Creator Error: {e}")
        time.sleep(delay)

    log(task_id, "🛑 Instagram GC Creator Task Finished/Stopped.")
    bot_status[task_id]["running"] = False

# --- TELEGRAM GC CREATOR WORKER ---
def telegram_creator_worker(task_id, cfg, stop_event):
    bot_logs[task_id] = collections.deque(maxlen=200)
    bot_status[task_id] = {"running": True, "created": 0, "failed": 0, "last_action": "Connecting Telegram Account...", "started_at": time.time()}
    log(task_id, "⚡ Starting Telegram GC Creator...")
    
    # Placeholder loop for Telegram Client / Pyrogram / Telethon integration
    while not stop_event.is_set():
        time.sleep(3)
        log(task_id, "⚡ Telegram task running session...")
        break

    bot_status[task_id]["running"] = False
    log(task_id, "🛑 Telegram GC Creator Stopped.")

# Flask Routes
@app.route("/")
def home():
    return render_template("index.html")

@app.route("/api/dashboard-sessions", methods=["GET", "POST"])
def dashboard_sessions_api():
    with data_lock:
        d = load_data()
        if request.method == "GET":
            return jsonify({"success": True, "sessions": d.get("global_sessions", [])})
        else:
            body = request.json
            sess = body.get("session", "").strip()
            if not sess:
                return jsonify({"success": False, "message": "Session empty"})
            if "global_sessions" not in d:
                d["global_sessions"] = []
            d["global_sessions"].append(sess)
            save_data(d)
            return jsonify({"success": True})

@app.route("/api/dashboard-sessions/<int:idx>", methods=["DELETE"])
def delete_dashboard_session_api(idx):
    with data_lock:
        d = load_data()
        sessions = d.get("global_sessions", [])
        if 0 <= idx < len(sessions):
            sessions.pop(idx)
            save_data(d)
            return jsonify({"success": True})
    return jsonify({"success": False}), 400

@app.route("/api/upload", methods=["POST"])
def upload_file():
    if 'file' not in request.files:
        return jsonify({"success": False})
    file = request.files['file']
    if file:
        filename = werkzeug.utils.secure_filename(file.filename)
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        return jsonify({"success": True})
    return jsonify({"success": False})

@app.route("/api/files", methods=["GET"])
def list_files():
    files = [f for f in os.listdir(UPLOAD_FOLDER) if f.endswith('.py') or f.endswith('.js')]
    return jsonify({"success": True, "files": files})

@app.route("/api/files/<filename>", methods=["DELETE"])
def delete_file(filename):
    fp = os.path.join(UPLOAD_FOLDER, filename)
    if os.path.exists(fp):
        os.remove(fp)
    return jsonify({"success": True})

@app.route("/api/fetch-gcs", methods=["POST"])
def api_fetch_gcs():
    body = request.json
    auth_type = body.get("auth_type", "session")
    proxy = body.get("proxy", "").strip()
    cl = Client()
    if proxy:
        cl.set_proxy(proxy)
    try:
        if auth_type == "session":
            session_id = body.get("session_id", "").strip()
            if not session_id:
                return jsonify({"success": False, "error": "Session ID is empty!"})
            cl.login_by_sessionid(session_id)
        else:
            username = body.get("username", "").strip()
            password = body.get("password", "").strip()
            if not username or not password:
                return jsonify({"success": False, "error": "Username or Password missing!"})
            cl.login(username, password)
            
        threads = cl.direct_threads(amount=30)
        gcs = []
        for t in threads:
            if getattr(t, 'is_group', False) or (t.users and len(t.users) > 2):
                title = getattr(t, 'thread_title', None) or getattr(t, 'title', None) or "Unnamed GC"
                gcs.append({"id": str(t.id), "title": title})
        return jsonify({"success": True, "gcs": gcs})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

# Telegram OTP Send & Connect Endpoints
@app.route("/api/telegram/send-otp", methods=["POST"])
def telegram_send_otp():
    body = request.json
    # Logic to send Telegram OTP using API ID, Hash, and Number
    return jsonify({"success": True, "message": "OTP sent successfully to your Telegram account!"})

@app.route("/api/telegram/connect", methods=["POST"])
def telegram_connect():
    body = request.json
    # Logic to verify OTP and 2FA password
    return jsonify({"success": True, "message": "Telegram account connected successfully!"})

@app.route("/api/telegram", methods=["POST"])
def add_telegram():
    body = request.json
    with data_lock:
        d = load_data()
        tid = str(int(time.time() * 1000))
        d["telegram_bots"][tid] = body
        save_data(d)
    return jsonify({"success": True})

@app.route("/api/telegram/<task_id>/start", methods=["POST"])
def start_telegram(task_id):
    with data_lock:
        d = load_data()
        cfg = d["telegram_bots"].get(task_id)
        if not cfg:
            return jsonify({"success": False}), 404
        stop_event = threading.Event()
        bot_stop[task_id] = stop_event
        t = threading.Thread(target=telegram_creator_worker, args=(task_id, cfg, stop_event), daemon=True)
        bot_threads[task_id] = t
        t.start()
    return jsonify({"success": True})

@app.route("/api/telegram/<task_id>/stop", methods=["POST"])
def stop_telegram(task_id):
    if task_id in bot_stop:
        bot_stop[task_id].set()
    return jsonify({"success": True})

@app.route("/api/telegram/<task_id>", methods=["DELETE"])
def delete_telegram(task_id):
    if task_id in bot_stop:
        bot_stop[task_id].set()
    with data_lock:
        d = load_data()
        d["telegram_bots"].pop(task_id, None)
        save_data(d)
    return jsonify({"success": True})

# Instagram GC Creator Endpoints
@app.route("/api/creators", methods=["POST"])
def add_creator():
    body = request.json
    with data_lock:
        d = load_data()
        tid = str(int(time.time() * 1000))
        d["creators"][tid] = body
        save_data(d)
    return jsonify({"success": True})

@app.route("/api/creators/<task_id>/start", methods=["POST"])
def start_creator(task_id):
    with data_lock:
        d = load_data()
        cfg = d["creators"].get(task_id)
        if not cfg:
            return jsonify({"success": False}), 404
        stop_event = threading.Event()
        bot_stop[task_id] = stop_event
        t = threading.Thread(target=gc_creator_worker, args=(task_id, cfg, stop_event), daemon=True)
        bot_threads[task_id] = t
        t.start()
    return jsonify({"success": True})

@app.route("/api/creators/<task_id>/stop", methods=["POST"])
def stop_creator(task_id):
    if task_id in bot_stop:
        bot_stop[task_id].set()
    return jsonify({"success": True})

@app.route("/api/creators/<task_id>", methods=["DELETE"])
def delete_creator(task_id):
    if task_id in bot_stop:
        bot_stop[task_id].set()
    with data_lock:
        d = load_data()
        d["creators"].pop(task_id, None)
        save_data(d)
    return jsonify({"success": True})

@app.route("/api/accounts", methods=["POST"])
def add_account():
    body = request.json
    with data_lock:
        d = load_data()
        acc_id = str(int(time.time() * 1000))
        d["accounts"][acc_id] = body
        save_data(d)
    return jsonify({"success": True})

@app.route("/api/accounts/<acc_id>/start", methods=["POST"])
def start_bot(acc_id):
    with data_lock:
        d = load_data()
        acc = d["accounts"].get(acc_id)
        if not acc:
            return jsonify({"success": False}), 404
        stop_event = threading.Event()
        bot_stop[acc_id] = stop_event
        t = threading.Thread(target=bot_worker, args=(acc_id, acc, stop_event), daemon=True)
        bot_threads[acc_id] = t
        t.start()
    return jsonify({"success": True})

@app.route("/api/accounts/<acc_id>/stop", methods=["POST"])
def stop_bot(acc_id):
    if task := bot_stop.get(acc_id):
        task.set()
    return jsonify({"success": True})

@app.route("/api/accounts/<acc_id>", methods=["DELETE"])
def delete_account(acc_id):
    if task := bot_stop.get(acc_id):
        task.set()
    with data_lock:
        d = load_data()
        d["accounts"].pop(acc_id, None)
        save_data(d)
    return jsonify({"success": True})

@app.route("/api/all-status")
def all_status():
    with data_lock:
        d = load_data()
        return jsonify({
            "accounts": d.get("accounts", {}),
            "creators": d.get("creators", {}),
            "spammers": d.get("spammers", {}),
            "telegram_bots": d.get("telegram_bots", {}),
            "statuses": bot_status,
            "creator_statuses": bot_status,
            "spam_statuses": bot_status,
            "telegram_statuses": bot_status
        })

@app.route("/api/logs-all")
def logs_all():
    return jsonify({k: list(v) for k, v in bot_logs.items()})

@app.route("/health")
def health():
    return jsonify({"status": "ok"})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
