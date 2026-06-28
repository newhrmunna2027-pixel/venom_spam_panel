# -*- coding: utf-8 -*-
# START OF FILE app.py

import os
import json
import time
import math
import urllib.parse
import threading
import asyncio
from datetime import timedelta
from functools import wraps
from cachetools import TTLCache
from flask import Flask, request, jsonify, render_template, session, redirect, url_for

# database dual system coordinator import
import data_coordinator

app = Flask(__name__, template_folder='templates')
app.secret_key = "out_of_law_super_secret_key"

# 🚀 Target Add Safe Thread Lock (Prevents Race-Condition Double Adds)
target_add_lock = threading.Lock()

# ==========================================
# 🚀 INTEGRATED API CACHE & LIMITER (Replaces api.py)
# ==========================================
api_cache = TTLCache(maxsize=500, ttl=300)

class AntiCrashLimiter:
    def __init__(self, limit=30, max_waiting=50):
        self.limit = limit
        self.max_waiting = max_waiting 
        self.semaphore = threading.Semaphore(limit)
        self.lock = threading.Lock()
        self.current_waiting = 0 

    def acquire(self):
        with self.lock:
            if self.current_waiting >= self.max_waiting:
                return False
            self.current_waiting += 1
            
        acquired = self.semaphore.acquire(timeout=8.0)
        
        with self.lock:
            self.current_waiting -= 1 
        return acquired

    def release(self):
        self.semaphore.release()

api_limiter = AntiCrashLimiter(limit=30, max_waiting=50)

def cached_endpoint(ttl=300):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*a, **k):
            key = (request.path, tuple(request.args.items()))
            if key in api_cache:
                return api_cache[key]
            res = fn(*a, **k)
            api_cache[key] = res
            return res
        return wrapper
    return decorator

def run_async(coro):
    """Bridge runner to safely execute async functions inside sync Flask view"""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(coro)

# --- Configurations ---
USERS_DIR = 'users'
STOCK_DIR = 'account'
STOCK_FILE = os.path.join(STOCK_DIR, 'stock.json')
LIMIT_FILE = 'limit.json'

FILES = {
    'active': 'active.json', 
    'profile': 'profile.json', 
    'history': 'history.json',
    'data': 'data.json', 
    'vv': 'vv.json', 
    'live': 'bots_live_status.json',
    'check_txt': 'check.txt', 
    'targets_txt': 'targets.txt', 
    'maintenance': 'maintenance.json',
    'whitelist': 'whitelist.json',
    'info': 'info.json',
    'bot': 'bot.json',
    'members': 'members.json',
    'target_logs': 'target_logs.json',
    'bad_accounts': 'bad_accounts.json',
    'api_json': 'api.json'
}

# ==========================================
# 🟢 1. EXPOSED GARENA API ENDPOINT
# ==========================================
@app.route('/player-info')
@cached_endpoint(ttl=300)
def api_get_account_info():
    uid = request.args.get('uid')
    if not uid:
        return jsonify({"error": "Please provide UID."}), 400

    if not api_limiter.acquire():
        return jsonify({
            "error": "Server is currently experiencing extremely high traffic. Please try again in a few seconds.",
            "status": 503
        }), 503

    try:
        # Dynamically import manager module
        from manager import GetAccountInformation
        
        # Runs the async Garena scraper synchronously safely
        data = run_async(GetAccountInformation(uid, "7", "/GetPlayerPersonalShow"))
        
        formatted_json = json.dumps(data, indent=2, ensure_ascii=False)
        return formatted_json, 200, {'Content-Type': 'application/json; charset=utf-8'}
        
    except Exception as e:
        return jsonify({"error": f"Failed to fetch info: {str(e)}"}), 500
        
    finally:
        api_limiter.release()

# ==========================================
# 🟢 2. CORE SYSTEM FUNCTIONS
# ==========================================
def load_json_safe(path, default):
    return data_coordinator.load_data(path, default)

def save_json_locked(path, data):
    data_coordinator.save_data(path, data)

def is_owner(user_data):
    """Creator is inherently an Owner with extra powers."""
    return user_data and user_data.get('role') in ['owner', 'creator']

def is_creator(user_data):
    """Strictly checks for Creator tier."""
    return user_data and user_data.get('role') == 'creator'

def check_maintenance():
    return load_json_safe(FILES['maintenance'], {"status": False, "end_time": 0}).get("status", False)

def get_limit_config():
    return load_json_safe(LIMIT_FILE, {
        "global_limit": 40, 
        "api_limit": 20, 
        "default_line_3": "TIKTOK [FF00FF]→OUT OF LAW",
        "allow_user_add_bot": True
    })

def get_user_bots(username):
    path = os.path.join(USERS_DIR, f"{username}.json")
    data = load_json_safe(path, {"bot": [], "vv": [], "failed": []})
    if not isinstance(data, dict):
        data = {"bot": [], "vv": [], "failed": []}
    if "bot" not in data:
        data["bot"] = []
    if "vv" not in data:
        data["vv"] = []
    if "failed" not in data:
        data["failed"] = []
    return data

def save_user_bots(username, data):
    path = os.path.join(USERS_DIR, f"{username}.json")
    save_json_locked(path, data)

def normalize_bot_list(bots_data, key):
    raw_data = bots_data.get(key, [])
    normalized = []
    if isinstance(raw_data, dict):
        for uid, password in raw_data.items():
            normalized.append({"uid": str(uid).strip(), "password": str(password).strip()})
    elif isinstance(raw_data, list):
        for item in raw_data:
            if isinstance(item, dict):
                uid = str(item.get('uid', item.get('Game uid', ''))).strip()
                password = str(item.get('password', item.get('pass', ''))).strip()
                if uid:
                    normalized.append({"uid": uid, "password": password})
            elif isinstance(item, (str, int)):
                uid = str(item).strip()
                if uid:
                    normalized.append({"uid": uid, "password": ""})
    return normalized

def normalize_failed_bots(user_bots):
    normalized = []
    for item in user_bots.get('failed', []):
        if isinstance(item, dict):
            uid = str(item.get('uid', '')).strip()
            if uid:
                normalized.append({
                    "uid": uid,
                    "source": item.get('source', 'Unknown'),
                    "reason": item.get('reason', 'Banned / Login Failed'),
                    "type": item.get('type', 'Unknown'),
                    "time": item.get('time', 'N/A')
                })
        elif isinstance(item, (str, int)):
            uid = str(item).strip()
            if uid:
                normalized.append({
                    "uid": uid,
                    "source": "Unknown",
                    "reason": "Banned / Login Failed",
                    "type": "Unknown",
                    "time": "N/A"
                })
    return normalized

def clean_orphan_user_bots(username):
    my_bots = get_user_bots(username)
    master_bot = load_json_safe(FILES['bot'], [])
    master_vv = load_json_safe(FILES['vv'], {})
    stock = load_json_safe(STOCK_FILE, [])
    
    valid_uids = set()
    for b in master_bot:
        if isinstance(b, dict) and b.get('uid'):
            valid_uids.add(str(b.get('uid')).strip())
    for uid in master_vv:
        valid_uids.add(str(uid).strip())
    for b in stock:
        if isinstance(b, dict) and b.get('uid'):
            valid_uids.add(str(b.get('uid')).strip())
            
    changed = False
    
    original_bots = normalize_bot_list(my_bots, 'bot')
    cleaned_bots = []
    for b in original_bots:
        if b.get('uid') in valid_uids:
            cleaned_bots.append(b)
        else:
            changed = True
            
    original_vvs = normalize_bot_list(my_bots, 'vv')
    cleaned_vvs = []
    for v in original_vvs:
        if v.get('uid') in valid_uids:
            cleaned_vvs.append(v)
        else:
            changed = True
            
    if changed:
        my_bots['bot'] = cleaned_bots
        my_bots['vv'] = cleaned_vvs
        save_user_bots(username, my_bots)
        compile_master_bots()
        distribute_targets()

def init_files():
    os.makedirs(USERS_DIR, exist_ok=True)
    os.makedirs(STOCK_DIR, exist_ok=True)
    load_json_safe(STOCK_FILE, [])
    get_limit_config()
    
    for key, path in FILES.items():
        if key == 'vv': 
            load_json_safe(path, {})
        elif key == 'live': 
            load_json_safe(path, {})
        elif key == 'maintenance': 
            load_json_safe(path, {"status": False, "end_time": 0})
        elif key == 'whitelist': 
            load_json_safe(path, {"players": [], "guilds": []})
        elif key in ['profile', 'data', 'info', 'check_txt', 'targets_txt']: 
            load_json_safe(path, {})
        elif key.endswith('.json') and key not in ['members']: 
            load_json_safe(path, [])
    
    members = load_json_safe(FILES['members'], [])
    
    creator_exists = any(is_creator(m) or m.get('username') == 'creator' for m in members)
    if not creator_exists:
        converted = False
        for m in members:
            if m.get('username') == 'owner':
                m['username'] = 'creator'
                m['name'] = 'System Creator'
                m['role'] = 'creator'
                converted = True
        if not converted:
            members.append({
                "name": "System Creator",
                "pic": "902000003",
                "username": "creator",
                "password": "123",
                "role": "creator",
                "limit": 999999,
                "active_limit": 999999
            })
        save_json_locked(FILES['members'], members)

def add_history(action, uid, name):
    history = load_json_safe(FILES['history'], [])
    history.insert(0, {"time": time.strftime("%Y-%m-%d %H:%M:%S"), "action": action, "uid": uid, "name": name})
    save_json_locked(FILES['history'], history[:100])

def add_target_log(action, uid, name, duration, by_user):
    logs = load_json_safe(FILES['target_logs'], [])
    logs.insert(0, {
        "action": action,
        "uid": uid,
        "name": name,
        "duration": duration,
        "by": by_user,
        "time": int(time.time() * 1000)
    })
    save_json_locked(FILES['target_logs'], logs[:1000])

def compile_master_bots():
    master_bot = []
    master_vv = {}
    
    if os.path.exists(USERS_DIR):
        for filename in os.listdir(USERS_DIR):
            if filename.endswith('.json'):
                username = filename[:-5]
                data = get_user_bots(username)
                master_bot.extend(normalize_bot_list(data, 'bot'))
                for v in normalize_bot_list(data, 'vv'):
                    master_vv[str(v['uid'])] = v['password']
                
    save_json_locked(FILES['bot'], master_bot)
    save_json_locked(FILES['vv'], master_vv)

def get_user_usable_limit(username):
    members = load_json_safe(FILES['members'], [])
    user = next((m for m in members if m['username'] == username), None)
    if not user: 
        return 0
    
    limit_cfg = get_limit_config()
    global_limit = int(limit_cfg.get('global_limit', 40))

    if is_owner(user): 
        return global_limit
    
    user_bots = get_user_bots(username)
    total_bot_json = len(normalize_bot_list(user_bots, 'bot'))
    total_vv_json = len(normalize_bot_list(user_bots, 'vv'))
    
    supported_by_trackers = total_bot_json * 3
    supported_by_attackers = math.floor(total_vv_json / 2)
    
    self_usable = min(supported_by_attackers, supported_by_trackers)
    owner_given_active_limit = int(user.get('active_limit', 0))
    
    return self_usable + owner_given_active_limit

def distribute_targets():
    bot_data = load_json_safe(FILES['bot'], [])
    active_data = load_json_safe(FILES['active'], [])
    
    user_targets = {}
    for t in active_data:
        if not isinstance(t, dict):
            continue
        uname = t.get('addedByUsername', 'owner')
        if uname not in user_targets: 
            user_targets[uname] = []
        user_targets[uname].append(t)
        
    running_uids = []
    for uname, targets in user_targets.items():
        usable_limit = get_user_usable_limit(uname)
        targets.sort(key=lambda x: x.get('addTime', 0)) 
        for i, t in enumerate(targets):
            if i < usable_limit:
                running_uids.append(t['uid'])
                t['status'] = 'Running'
            else:
                t['status'] = 'Paused (BY OWNER)'

    save_json_locked(FILES['active'], active_data)
    
    bot_count = len(bot_data) if isinstance(bot_data, list) and len(bot_data) > 0 else 1
    distribution = {str(i): [] for i in range(1, bot_count + 1)}
    if bot_count > 0:
        for index, uid in enumerate(running_uids): 
            distribution[str((index % bot_count) + 1)].append(uid)
            
    save_json_locked(FILES['check_txt'], distribution)

def fix_orphan_targets(active_data):
    members = load_json_safe(FILES['members'], [])
    owner_user = next((m for m in members if is_creator(m)), None)
    if not owner_user: 
        return False

    changed = False
    for t in active_data:
        if isinstance(t, dict) and not t.get('addedByUsername'):
            t['addedByUsername'] = owner_user['username']
            t['addedByName'] = owner_user.get('name', owner_user['username'])
            t['addedByRole'] = 'creator'
            changed = True
    return changed

def check_expired_targets():
    if check_maintenance(): 
        return
    active_data = load_json_safe(FILES['active'], [])
    profiles = load_json_safe(FILES['profile'], {})
    current_time = int(time.time() * 1000)
    
    new_active = []
    changed = False
    
    if fix_orphan_targets(active_data):
        changed = True
        
    for t in active_data:
        if not isinstance(t, dict):
            continue
        expire_at = t.get('expireAt')
        
        is_expired = False
        if expire_at == 'permanent':
            is_expired = False
        elif isinstance(expire_at, (int, float)):
            is_expired = int(expire_at) <= current_time
        elif isinstance(expire_at, str) and expire_at.isdigit():
            is_expired = int(expire_at) <= current_time
        else:
            is_expired = True

        if not is_expired:
            new_active.append(t)
        else:
            changed = True
            add_history("Expired", t.get('uid', 'N/A'), t.get('name', 'Unknown'))
            add_target_log("EXPIRED", t.get('uid', 'N/A'), t.get('name', 'Unknown'), t.get('duration', 'N/A'), "System")
            uid = t.get('uid')
            if uid and uid in profiles: 
                del profiles[uid]
                
    if changed:
        save_json_locked(FILES['active'], new_active)
        save_json_locked(FILES['profile'], profiles)
        distribute_targets()

# 🚀 3. NATIVE INTERNAL FETCHER (Bypasses HTTP overhead entirely)
def fetch_and_parse_ff_api(uid):
    for attempt in range(1, 4):
        try:
            from manager import GetAccountInformation
            raw_data = run_async(GetAccountInformation(uid, "7", "/GetPlayerPersonalShow"))
            
            if raw_data and "error" not in raw_data:
                basic = raw_data.get("basicInfo") or raw_data.get("basic_info") or {}
                clan = raw_data.get("clanBasicInfo") or raw_data.get("clan_like_info") or {}
                social = raw_data.get("socialInfo") or raw_data.get("social_info") or {}
                
                try: create_at = int(basic.get("createAt") or basic.get("create_at") or 0)
                except: create_at = 0

                try: last_login_at = int(basic.get("lastLoginAt") or basic.get("last_login_at") or 0)
                except: last_login_at = 0

                try: level = int(basic.get("level") or 0)
                except: level = 0

                try: liked = int(basic.get("liked") or 0)
                except: liked = 0

                try: head_pic = int(basic.get("headPic") or basic.get("head_pic") or 902000003)
                except: head_pic = 902000003

                try: banner_id = int(basic.get("bannerId") or basic.get("banner_id") or 901000001)
                except: banner_id = 901000001

                data = {
                    "basicInfo": {
                        "nickname": basic.get("nickname", "Unknown"), 
                        "level": level,
                        "headPic": head_pic,
                        "bannerId": banner_id,
                        "region": basic.get("region", "N/A"), 
                        "liked": liked,
                        "createAt": create_at,
                        "lastLoginAt": last_login_at
                    },
                    "clanBasicInfo": {
                        "clanName": clan.get("clanName") or clan.get("clan_name") or "No Guild", 
                        "clanId": clan.get("clanId") or clan.get("clan_id") or "N/A",
                        "captainId": clan.get("captainId") or clan.get("captain_id") or "N/A"
                    },
                    "socialInfo": {
                        "signature": social.get("signature", "Default Signature")
                    }
                }
                return {"success": True, "data": data}
            else:
                return {"success": False, "msg": raw_data.get("error", "Player not found.")}
        except Exception as e:
            time.sleep(1)
            
    return {"success": False, "msg": "API Local Scraper Connection Error."}

init_files()

# ==========================================
# 🟢 4. WEB DASHBOARD ROUTING
# ==========================================

@app.before_request
def check_valid_session():
    if request.endpoint in ['login', 'static', 'api_get_account_info']:
        return
    if session.get('logged_in') and 'user' in session:
        current_username = session['user'].get('username')
        current_password = session['user'].get('password')
        
        members = load_json_safe(FILES['members'], [])
        db_user = next((m for m in members if m['username'] == current_username), None)
        
        if not db_user or db_user.get('password') != current_password:
            session.clear()
            if request.path.startswith('/api/'):
                return jsonify({"error": "Session expired or password changed", "logout": True}), 401
            return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = request.form.get('username').strip()
        pwd = request.form.get('password').strip()
        remember = request.form.get('remember')
        
        members = load_json_safe(FILES['members'], [])
        user_data = next((m for m in members if m['username'] == user and m['password'] == pwd), None)
        
        if user_data:
            session['logged_in'] = True
            session['user'] = user_data
            if remember:
                session.permanent = True
                app.permanent_session_lifetime = timedelta(days=30)
            else:
                session.permanent = False
            return redirect(url_for('index'))
        else:
            return render_template('index.html', show_login=True, error="Invalid Credentials!")
    
    if session.get('logged_in') and session.get('user'): 
        return redirect(url_for('index'))
    return render_template('index.html', show_login=True)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/')
def index():
    if not session.get('logged_in') or not session.get('user'): 
        session.clear()
        return redirect(url_for('login'))
    
    members = load_json_safe(FILES['members'], [])
    current_username = session['user']['username']
    updated_user = next((m for m in members if m['username'] == current_username), None)
    if updated_user:
        session['user'] = updated_user
    else:
        session.clear()
        return redirect(url_for('login'))
        
    return render_template('index.html', show_login=False, current_user=session['user'])

# ==========================================
# 🟢 5. APP API ENDPOINTS (DASHBOARD)
# ==========================================

@app.route('/api/stock/upload', methods=['POST'])
def upload_stock_accounts():
    if not session.get('logged_in') or not is_creator(session['user']):
        return jsonify({"success": False, "msg": "Unauthorized Access"}), 401
    
    try:
        raw_uploaded = request.json
        parsed_accounts = []
        if isinstance(raw_uploaded, dict):
            for uid, password in raw_uploaded.items():
                clean_uid = str(uid).strip()
                clean_pwd = str(password).strip()
                if clean_uid and clean_pwd:
                    parsed_accounts.append({"uid": clean_uid, "password": clean_pwd})
        elif isinstance(raw_uploaded, list):
            for entry in raw_uploaded:
                if isinstance(entry, dict):
                    uid = str(entry.get('uid') or entry.get('account') or '').strip()
                    pwd = str(entry.get('password') or '').strip()
                    if uid and pwd:
                        parsed_accounts.append({"uid": uid, "password": pwd})
                elif isinstance(entry, str):
                    parsed_query = urllib.parse.parse_qs(entry)
                    uid = str(parsed_query.get('account', [''])[0]).strip()
                    pwd = str(parsed_query.get('password', [''])[0]).strip()
                    if uid and pwd:
                        parsed_accounts.append({"uid": uid, "password": pwd})
                        
        if not parsed_accounts:
            return jsonify({"success": False, "msg": "Could not identify any valid account configurations in the uploaded file!"})
            
        current_stock = load_json_safe(STOCK_FILE, [])
        existing_uids = {str(b.get('uid')).strip() for b in current_stock if 'uid' in b}
        
        added_count = 0
        for entry in parsed_accounts:
            uid = entry['uid']
            pwd = entry['password']
            if uid not in existing_uids:
                current_stock.append({"uid": uid, "password": pwd})
                existing_uids.add(uid)
                added_count += 1
                
        save_json_locked(STOCK_FILE, current_stock)
        return jsonify({"success": True, "msg": f"Identified & parsed {len(parsed_accounts)} accounts. Appended {added_count} unique bots to stock.json!"})
    except Exception as e:
        return jsonify({"success": False, "msg": f"Stock upload processing failed: {str(e)}"})

@app.route('/api/access/metrics', methods=['GET'])
def get_access_metrics():
    if not session.get('logged_in') or not is_creator(session['user']):
        return jsonify({}), 401
        
    bot_data = load_json_safe(FILES['bot'], [])
    vv_data = load_json_safe(FILES['vv'], {})
    api_data = load_json_safe(FILES['api_json'], [])
    stock_data = load_json_safe(STOCK_FILE, [])
    members = load_json_safe(FILES['members'], [])
    
    total_slots = len(vv_data) + len(stock_data)
    used_slots = sum(get_user_usable_limit(m['username']) for m in members if not is_owner(m))
    limit_cfg = get_limit_config()
    
    return jsonify({
        "bot_count": len(bot_data),
        "vv_count": len(vv_data),
        "api_count": len(api_data),
        "stock_count": len(stock_data),
        "total_slots": total_slots,
        "used_slots": used_slots,
        "global_limit": limit_cfg.get("global_limit", 40),
        "api_limit": limit_cfg.get("api_limit", 20),
        "default_line_3": limit_cfg.get("default_line_3", "TIKTOK [FF00FF]→OUT OF LAW"),
        "allow_user_add_bot": limit_cfg.get("allow_user_add_bot", True)
    })

@app.route('/api/access/update_limit', methods=['POST'])
def update_global_limit():
    if not session.get('logged_in') or not is_creator(session['user']):
        return jsonify({"success": False}), 401
        
    data = request.json
    new_limit = int(data.get('global_limit', 40))
    limit_cfg = get_limit_config()
    limit_cfg['global_limit'] = new_limit
    save_json_locked(LIMIT_FILE, limit_cfg)
    return jsonify({"success": True})

@app.route('/api/access/update_api_limit', methods=['POST'])
def update_api_limit():
    if not session.get('logged_in') or not is_creator(session['user']):
        return jsonify({"success": False}), 401
        
    data = request.get_json(force=True) or {}
    new_api_limit = int(data.get('api_limit', 20))
    limit_cfg = get_limit_config()
    limit_cfg['api_limit'] = new_api_limit
    save_json_locked(LIMIT_FILE, limit_cfg)
    return jsonify({"success": True})

@app.route('/api/access/toggle_add_bot', methods=['POST'])
def toggle_add_bot():
    if not session.get('logged_in') or not is_creator(session['user']):
        return jsonify({"success": False}), 401
    data = request.json or {}
    status = bool(data.get('status', True))
    limit_cfg = get_limit_config()
    limit_cfg['allow_user_add_bot'] = status
    save_json_locked(LIMIT_FILE, limit_cfg)
    return jsonify({"success": True})

@app.route('/api/access/check_user', methods=['POST'])
def check_user_access():
    if not session.get('logged_in') or not is_creator(session['user']):
        return jsonify({"success": False}), 401
        
    username = request.json.get('username', '').strip()
    members = load_json_safe(FILES['members'], [])
    user = next((m for m in members if m['username'] == username), None)
    if not user:
        return jsonify({"success": False, "msg": "Target username ID not found."})
        
    return jsonify({
        "success": True,
        "username": user['username'],
        "name": user.get('name', user['username']),
        "limit": user.get('active_limit', 0), 
        "role": user.get('role', 'admin')
    })

@app.route('/api/access/save_user_limit', methods=['POST'])
def save_user_limit():
    if not session.get('logged_in') or not is_creator(session['user']):
        return jsonify({"success": False}), 401
        
    data = request.json
    username = data.get('username', '').strip()
    new_active_limit = int(data.get('limit', 0))
    
    members = load_json_safe(FILES['members'], [])
    user = next((m for m in members if m['username'] == username), None)
    if not user:
        return jsonify({"success": False, "msg": "User not found."})
        
    user['active_limit'] = new_active_limit
    save_json_locked(FILES['members'], members)
    distribute_targets()
    return jsonify({"success": True})

@app.route('/api/duo/check', methods=['POST'])
def check_duo_status():
    if not session.get('logged_in'):
        return jsonify({"success": False, "msg": "Unauthorized"}), 401
        
    data = request.get_json(force=True) or {}
    target_uid = str(data.get('uid', '')).strip()
    if not target_uid:
        return jsonify({"success": False, "msg": "Target UID cannot be empty."}), 400
        
    stock_bots = load_json_safe(STOCK_FILE, [])
    if not stock_bots:
        return jsonify({"success": False, "msg": "No active bots in stock.json for Garena authentication."}), 500
        
    temp_bot = stock_bots[0]
    bot_uid = str(temp_bot.get('uid')).strip()
    bot_pwd = str(temp_bot.get('password')).strip()
    
    try:
        from bio_changer import check_player_duo
        success, result = run_async(check_player_duo(bot_uid, bot_pwd, target_uid))
        if success and isinstance(result, dict):
            partner_uid = str(result.get("Partner UID", "0")).strip()
            profiles = load_json_safe(FILES['profile'], {})
            
            target_profile = None
            if target_uid in profiles:
                target_profile = profiles[target_uid]
            else:
                t_res = fetch_and_parse_ff_api(target_uid)
                if t_res and t_res.get("success"):
                    target_profile = t_res.get("data")
                    profiles[target_uid] = target_profile
            
            partner_profile = None
            if partner_uid and partner_uid != "0" and partner_uid != "N/A":
                if partner_uid in profiles:
                    partner_profile = profiles[partner_uid]
                else:
                    p_res = fetch_and_parse_ff_api(partner_uid)
                    if p_res and p_res.get("success"):
                        partner_profile = p_res.get("data")
                        profiles[partner_uid] = partner_profile
            
            save_json_locked(FILES['profile'], profiles)
            return jsonify({
                "success": True, "duo_info": result, "target_profile": target_profile, "partner_profile": partner_profile
            })
        else:
            return jsonify({"success": False, "msg": "This player DUO Partner status is Hide.. Try other player"})
    except Exception as e:
        return jsonify({"success": False, "msg": f"Duo check system failure: {str(e)}"}), 500

@app.route('/api/bio/save_default_line_3', methods=['POST'])
def save_default_line_3():
    if not session.get('logged_in') or not is_creator(session['user']):
        return jsonify({"success": False}), 401
    text = request.json.get('text', '').strip()
    limit_cfg = get_limit_config()
    limit_cfg['default_line_3'] = text
    save_json_locked(LIMIT_FILE, limit_cfg)
    return jsonify({"success": True})

@app.route('/api/bio/change', methods=['POST'])
def execute_bio_change():
    if not session.get('logged_in'):
        return jsonify({"success": False}), 401
        
    data = request.json
    uid = data.get('uid', '').strip()
    pwd = data.get('password', '').strip()
    l1 = data.get('l1', '').strip()
    l2 = data.get('l2', '').strip()
    l3 = data.get('l3', '').strip()
    merged_bio = f"{l1}\n{l2}\n{l3}"
    
    try:
        from bio_changer import change_bot_bio
        success, msg = run_async(change_bot_bio(uid, pwd, merged_bio))
        if success:
            return jsonify({"success": True, "msg": "Bot biography updated successfully!"})
        return jsonify({"success": False, "msg": f"Garena protocall returned error: {msg}"})
    except Exception as e:
        return jsonify({"success": False, "msg": f"Bio changer execution failed: {str(e)}"})

@app.route('/api/my_bots', methods=['GET'])
def get_my_bots():
    if not session.get('logged_in'): 
        return jsonify({}), 401
    username = session['user']['username']
    
    clean_orphan_user_bots(username)
    user_bots = get_user_bots(username)
    normalized_bots = {
        "bot": normalize_bot_list(user_bots, 'bot'),
        "vv": normalize_bot_list(user_bots, 'vv'),
        "failed": normalize_failed_bots(user_bots)
    }
    limit_cfg = get_limit_config()
    global_limit = int(limit_cfg.get('global_limit', 40))
    members = load_json_safe(FILES['members'], [])
    db_user = next((m for m in members if m['username'] == username), None)
    
    provided_bot = len(normalized_bots['bot'])
    provided_vv = len(normalized_bots['vv'])
    self_usable_limit = min(math.floor(provided_vv / 2), provided_bot * 3)
    
    if is_owner(session['user']):
        display_limit = "∞"
        needed_bot = math.ceil(global_limit / 3) 
        needed_vv = global_limit * 2
        total_allocated = sum(int(m.get('active_limit', 0)) for m in members if not is_owner(m))
        usable_limit = total_allocated
    else:
        owner_given_active_limit = int(db_user.get('active_limit', 0)) if db_user else 0
        display_limit = owner_given_active_limit
        needed_bot = math.ceil(owner_given_active_limit / 3) 
        needed_vv = owner_given_active_limit * 2
        usable_limit = self_usable_limit + owner_given_active_limit
    
    return jsonify({
        "limit": display_limit,
        "needed_bot": needed_bot,
        "needed_vv": needed_vv,
        "provided_bot": provided_bot,
        "provided_vv": provided_vv,
        "self_usable_limit": self_usable_limit,
        "usable_limit": usable_limit,
        "allow_user_add_bot": limit_cfg.get('allow_user_add_bot', True),
        "bots": normalized_bots
    })

@app.route('/api/add_bot', methods=['POST'])
def add_my_bot():
    if not session.get('logged_in'): 
        return jsonify({"success": False}), 401
    username = session['user']['username']
    data = request.json
    uid = data.get('uid').strip()
    pwd = data.get('password').strip()
    
    master_bots = load_json_safe(FILES['bot'], [])
    master_vv = load_json_safe(FILES['vv'], {})
    limit_cfg = get_limit_config()
    
    global_limit = int(limit_cfg.get('global_limit', 40))
    max_bot_slots = math.ceil(global_limit / 3)
    max_vv_slots = global_limit * 2
    
    global_in_bot = any(str(b.get('uid')) == uid for b in master_bots)
    global_in_vv = uid in master_vv
    if global_in_bot or global_in_vv:
        return jsonify({"success": False, "msg": "This Bot UID is already active in the system!"})

    my_bots = get_user_bots(username)
    my_bots['failed'] = [b for b in my_bots.get('failed', []) if str(b.get('uid') if isinstance(b, dict) else b) != uid]
    current_bot_list = normalize_bot_list(my_bots, 'bot')
    current_vv_list = normalize_bot_list(my_bots, 'vv')
    current_bot = len(current_bot_list)
    current_vv = len(current_vv_list)
    
    if current_vv >= current_bot * 6:
        if len(master_bots) >= max_bot_slots:
            return jsonify({"success": False, "msg": f"Server Full! All {max_bot_slots} Tracker slots are fully loaded."})
        current_bot_list.append({"uid": uid, "password": pwd})
        usable = min(math.floor(current_vv / 2), (current_bot + 1) * 3)
        msg = "Added to Tracker Server (bot.json)."
    else:
        if len(master_vv) >= max_vv_slots:
            stock = load_json_safe(STOCK_FILE, [])
            stock.append({"uid": uid, "password": pwd})
            save_json_locked(STOCK_FILE, stock)
            current_vv_list.append({"uid": uid, "password": pwd})
            my_bots['vv'] = current_vv_list
            save_user_bots(username, my_bots)
            return jsonify({"success": True, "msg": "System slots are fully loaded! Your bot has been saved to Stock.json but allocated to your usability credit successfully."})
            
        current_vv_list.append({"uid": uid, "password": pwd})
        usable = min(math.floor((current_vv + 1) / 2), current_bot * 3)
        msg = "Added to Attack Server (vv.json)."
        
    my_bots['bot'] = current_bot_list
    my_bots['vv'] = current_vv_list
    save_user_bots(username, my_bots)
    compile_master_bots()
    distribute_targets() 
    
    if usable == 0:
        msg += "\n⚠️ Notice: You need at least 1 Tracker AND 2 Attack bots to activate targets!"
    else:
        msg += f"\n✅ Your active limit is now {usable} targets."
    return jsonify({"success": True, "msg": msg})

@app.route('/api/remove_failed_bot', methods=['POST'])
def remove_failed_bot():
    if not session.get('logged_in'): 
        return jsonify({"success": False}), 401
    username = session['user']['username']
    data = request.get_json(force=True) or {}
    uid = str(data.get('uid', '')).strip()
    if not uid:
        return jsonify({"success": False, "msg": "UID is empty"}), 400
    my_bots = get_user_bots(username)
    new_failed = []
    for b in my_bots.get('failed', []):
        current_uid = ""
        if isinstance(b, dict): current_uid = str(b.get('uid', '')).strip()
        elif isinstance(b, (str, int)): current_uid = str(b).strip()
        if current_uid != uid and current_uid != "":
            new_failed.append(b)
    my_bots['failed'] = new_failed
    save_user_bots(username, my_bots)
    return jsonify({"success": True})

@app.route('/api/dashboard', methods=['GET'])
def get_dashboard():
    if not session.get('logged_in') or not session.get('user'): 
        return jsonify({"error": "Unauthorized"}), 401
    check_expired_targets()
    active_targets = load_json_safe(FILES['active'], [])
    live_bots = load_json_safe(FILES['live'], {})
    bots_list = [{"no": i+1, "name": d.get("Name", "Unknown"), "uid": d.get("Game uid", "N/A"), "status": d.get("Status", "Offline")} for i, (b, d) in enumerate(live_bots.items())]
    user = session['user']
    usage = sum(1 for t in active_targets if isinstance(t, dict) and t.get('addedByUsername') == user['username']) if not is_owner(user) else len(active_targets)
    return jsonify({"total_targets": len(active_targets), "total_bots": len(bots_list), "bots": bots_list, "user_usage": usage})

@app.route('/api/user_stats', methods=['GET'])
def get_user_stats():
    if not session.get('logged_in') or not session.get('user'): 
        return jsonify({}), 401
    members = load_json_safe(FILES['members'], [])
    active_targets = load_json_safe(FILES['active'], [])
    stats = {}
    for m in members:
        username = m['username']
        active_count = sum(1 for t in active_targets if isinstance(t, dict) and t.get('addedByUsername') == username)
        stats[username] = {
            "name": m.get('name', username),
            "limit": m.get('limit', 0), 
            "active_limit": m.get('active_limit', 0), 
            "role": m.get('role', 'admin'),
            "active": active_count
        }
    return jsonify(stats)

@app.route('/api/targets', methods=['GET'])
def get_targets_panel():
    if not session.get('logged_in') or not session.get('user'): 
        return jsonify([]), 401
    check_expired_targets()
    targets = load_json_safe(FILES['active'], [])
    profiles = load_json_safe(FILES['profile'], {})
    for t in targets:
        if not isinstance(t, dict): continue
        uid = t.get('uid')
        p_data = profiles.get(uid)
        if not isinstance(p_data, dict): p_data = {}
        p_basic = p_data.get('basicInfo', {}) if isinstance(p_data.get('basicInfo'), dict) else {}
        p_clan = p_data.get('clanBasicInfo', {}) if isinstance(p_data.get('clanBasicInfo'), dict) else {}
        t['headPic'] = p_basic.get('headPic') or p_basic.get('head_pic') or '902000003'
        t['level'] = p_basic.get('level', 0)
        t['liked'] = p_basic.get('liked', 0)
        t['region'] = p_basic.get('region', 'N/A')
        t['guild'] = p_clan.get('clanName') or p_clan.get('clan_name') or "No Guild"
        t['guildId'] = str(p_clan.get('clanId') or p_clan.get('clan_id') or "N/A")
        t['leader'] = str(p_clan.get('captainId') or p_clan.get('captain_id') or "N/A")
        if 'addedByRole' not in t: t['addedByRole'] = 'admin'
        if 'addedByName' not in t or not t['addedByName']: t['addedByName'] = t.get('addedByUsername', 'System')
    return jsonify(targets)


# ==========================================
# 🟢 Target adding Endpoint (Double-add proof)
# ==========================================
@app.route('/api/target/add', methods=['POST'])
def add_target():
    if not session.get('logged_in') or not session.get('user'): 
        return jsonify({"success": False, "msg": "Unauthorized"})
    user = session['user']
    data = request.get_json(force=True)
    uid = str(data.get('uid')).strip()
    reason = data.get('reason', '')
    duration_str = data.get('duration', '1 day')
    
    # 1. Quick pre-check (outside lock to avoid waiting for heavy API calls if already exists)
    active_data = load_json_safe(FILES['active'], [])
    limit_cfg = get_limit_config()
    current_global_limit = int(limit_cfg.get('global_limit', 40))
    
    if len(active_data) >= current_global_limit: 
        return jsonify({"success": False, "msg": f"Global system limit ({current_global_limit}) reached!"})
    if any(isinstance(t, dict) and t.get('uid') == uid for t in active_data): 
        return jsonify({"success": False, "msg": "Target already exists."})
    
    if not is_owner(user):
        user_active_count = sum(1 for t in active_data if isinstance(t, dict) and t.get('addedByUsername') == user['username'])
        members = load_json_safe(FILES['members'], [])
        db_user = next((m for m in members if m['username'] == user['username']), None)
        add_limit = db_user.get('limit', 0) if db_user else user.get('limit', 0)
        if user_active_count >= add_limit:
            return jsonify({"success": False, "msg": "Your target limit is maxed. Please contact owner."})
    
    # 2. Heavy API Fetch (Held outside of the lock to prevent hanging other user's requests)
    api_res = fetch_and_parse_ff_api(uid)
    if not api_res["success"]: 
        return jsonify({"success": False, "msg": api_res["msg"]})
        
    current_time = int(time.time() * 1000)
    durations = {'1 day': 86400000, '7 day': 86400000*7, '30 day': 86400000*30, 'permanent': 'permanent'}
    expire_at = 'permanent' if duration_str == 'permanent' else current_time + durations.get(duration_str, 86400000)
    target_name = api_res["data"]["basicInfo"].get("nickname", "Unknown")

    # 3. Secure Critical Section (Write operations and final verification inside Thread Lock)
    with target_add_lock:
        latest_active_data = load_json_safe(FILES['active'], [])
        
        # Double check inside lock to block rapid concurrent requests
        if any(isinstance(t, dict) and t.get('uid') == uid for t in latest_active_data): 
            return jsonify({"success": False, "msg": "Target already exists (Duplicate request rejected)."})
            
        if len(latest_active_data) >= current_global_limit: 
            return jsonify({"success": False, "msg": f"Global system limit ({current_global_limit}) reached!"})
            
        if not is_owner(user):
            user_active_count = sum(1 for t in latest_active_data if isinstance(t, dict) and t.get('addedByUsername') == user['username'])
            members = load_json_safe(FILES['members'], [])
            db_user = next((m for m in members if m['username'] == user['username']), None)
            add_limit = db_user.get('limit', 0) if db_user else user.get('limit', 0)
            if user_active_count >= add_limit:
                return jsonify({"success": False, "msg": "Your target limit is maxed. Please contact owner."})

        latest_active_data.append({
            "id": f"t_{current_time}", "uid": uid, "name": target_name,
            "reason": reason, "duration": duration_str, "addTime": current_time, "expireAt": expire_at,
            "addedByUsername": user['username'], "addedByName": user.get('name', user['username']), 
            "addedByRole": user['role'], "status": "Running"
        })
        save_json_locked(FILES['active'], latest_active_data)
        
        profiles = load_json_safe(FILES['profile'], {})
        profiles[uid] = api_res["data"]
        save_json_locked(FILES['profile'], profiles)
        
    add_target_log("ADD", uid, target_name, duration_str, user.get('name', user['username']))
    distribute_targets()
    return jsonify({"success": True, "msg": "Protocol active on target!"})


@app.route('/api/target/delete', methods=['POST'])
def delete_target():
    if not session.get('logged_in') or not session.get('user'): 
        return jsonify({"success": False, "msg": "Unauthorized"})
    user = session['user']
    uid = request.json.get('uid')
    active_data = load_json_safe(FILES['active'], [])
    target_to_del = next((t for t in active_data if isinstance(t, dict) and t.get('uid') == uid), None)
    if not target_to_del: 
        return jsonify({"success": False, "msg": "Target not found."})
    
    if not is_owner(user) and target_to_del.get('addedByUsername') != user['username']:
        return jsonify({"success": False, "msg": "You do not have permission to delete this target."})

    new_active = [t for t in active_data if isinstance(t, dict) and t.get('uid') != uid]
    save_json_locked(FILES['active'], new_active)
    add_target_log("DELETE", uid, target_to_del.get('name', 'Unknown'), target_to_del.get('duration', 'N/A'), user.get('name', user['username']))
    distribute_targets()
    return jsonify({"success": True})

@app.route('/api/users', methods=['GET'])
def get_users():
    if not session.get('logged_in') or not is_owner(session.get('user')): 
        return jsonify([]), 401
        
    all_members = load_json_safe(FILES['members'], [])
    is_logged_in_creator = is_creator(session['user'])
    
    sanitized_members = []
    for m in all_members:
        safe_m = dict(m) 
        if safe_m.get('role') == 'creator' and not is_logged_in_creator:
            safe_m['password'] = '••••••'
        sanitized_members.append(safe_m)
        
    return jsonify(sanitized_members)
    
@app.route('/api/users/save', methods=['POST'])
def save_user():
    if not session.get('logged_in') or not is_owner(session.get('user')): 
        return jsonify({"success": False, "msg": "Unauthorized"}), 401
    data = request.json
    username = data.get('username').strip()
    password = data.get('password').strip()
    name = data.get('name', 'Unknown Admin').strip()
    pic = str(data.get('pic', '902000003')).strip()
    limit = int(data.get('limit', 0))
    active_limit = int(data.get('active_limit', 0)) if 'active_limit' in data else None
    role = data.get('role', 'admin')
    
    if not username or not password or not name: 
        return jsonify({"success": False, "msg": "Fields cannot be empty"})
        
    if username == "creator" and not is_creator(session['user']):
        return jsonify({"success": False, "msg": "Only the Creator can modify the Creator account."}), 403

    members = load_json_safe(FILES['members'], [])
    existing = next((m for m in members if m['username'] == username), None)
    
    if not is_creator(session['user']):
        if role in ['owner', 'creator'] and username != session['user']['username']:
            return jsonify({"success": False, "msg": "Owners cannot assign Owner or Creator roles."}), 403
        if existing and is_owner(existing) and existing['username'] != session['user']['username']:
            return jsonify({"success": False, "msg": "Owners cannot modify other Owners or Creators."}), 403
    
    if existing:
        existing['password'] = password
        existing['name'] = name
        existing['pic'] = pic
        existing['limit'] = limit
        if active_limit is not None: existing['active_limit'] = active_limit
        if existing['username'] == session['user']['username']: existing['role'] = session['user']['role']
        else: existing['role'] = role
    else:
        final_role = 'admin' if not is_creator(session['user']) else role
        if final_role == 'creator':
            return jsonify({"success": False, "msg": "Cannot create another Creator account."}), 403
        members.append({
            "username": username, "password": password, "name": name, "pic": pic, 
            "role": final_role, "limit": limit, "active_limit": active_limit if active_limit is not None else 0
        })
        
    save_json_locked(FILES['members'], members)
    distribute_targets() 
    return jsonify({"success": True})

@app.route('/api/users/delete', methods=['POST'])
def delete_user():
    if not session.get('logged_in') or not is_owner(session.get('user')): 
        return jsonify({"success": False, "msg": "Unauthorized"}), 401
    username = request.json.get('username')
    if username == "creator":
        return jsonify({"success": False, "msg": "The Creator account is permanent and cannot be deleted!"}), 403
    if username == session['user']['username']:
        return jsonify({"success": False, "msg": "You cannot delete your own account!"}), 403
        
    members = load_json_safe(FILES['members'], [])
    target_user = next((m for m in members if m['username'] == username), None)
    if not target_user:
        return jsonify({"success": False, "msg": "Target user not found."}), 404
        
    if not is_creator(session['user']):
        if is_owner(target_user):
            return jsonify({"success": False, "msg": "Owners cannot delete other Owners or Creators."}), 403
            
    new_members = [m for m in members if m['username'] != username]
    save_json_locked(FILES['members'], new_members)
    path = os.path.join(USERS_DIR, f"{username}.json")
    if os.path.exists(path): os.remove(path)
    compile_master_bots()
    distribute_targets()
    return jsonify({"success": True})

@app.route('/api/logs', methods=['GET'])
def get_logs():
    if not session.get('logged_in') or not is_owner(session.get('user')): 
        return jsonify([]), 401
    return jsonify(load_json_safe(FILES['target_logs'], []))

@app.route('/api/fetch_profile', methods=['POST'])
def fetch_profile():
    if not session.get('logged_in') or not session.get('user'): 
        return jsonify({"success": False, "message": "Unauthorized"}), 401
    data = request.get_json(force=True)
    uid = str(data.get('uid')).strip()
    save_profile = data.get('save', True)
    force_refresh = data.get('force', False)
    
    profiles = load_json_safe(FILES['profile'], {})
    if not force_refresh and uid in profiles: 
        return jsonify({"success": True, "data": profiles[uid]})
        
    api_res = fetch_and_parse_ff_api(uid)
    if api_res["success"] and save_profile:
        profiles[uid] = api_res["data"]
        save_json_locked(FILES['profile'], profiles)
    return jsonify(api_res)

@app.route('/api/info', methods=['GET'])
def get_info():
    if not session.get('logged_in') or not session.get('user'): 
        return jsonify({}), 401
    info_data = load_json_safe(FILES['info'], {})
    profiles = load_json_safe(FILES['profile'], {})
    for uid, d in info_data.items():
        if not isinstance(d, dict): continue
        p_data = profiles.get(uid)
        if not isinstance(p_data, dict): p_data = {}
        p_basic = p_data.get('basicInfo', {}) if isinstance(p_data.get('basicInfo'), dict) else {}
        p_clan = p_data.get('clanBasicInfo', {}) if isinstance(p_data.get('clanBasicInfo'), dict) else {}
        d['name'] = p_basic.get('nickname', 'Unknown')
        d['headPic'] = p_basic.get('headPic', '902000003')
        d['level'] = p_basic.get('level', 0)
        d['liked'] = p_basic.get('liked', 0)
        d['region'] = p_basic.get('region', 'N/A')
        d['guild'] = p_clan.get('clanName', 'No Guild')
        d['guildId'] = str(p_clan.get('clanId', 'N/A'))
        d['guild_leader'] = str(p_clan.get('captainId', 'N/A'))
    return jsonify(info_data)

@app.route('/api/data', methods=['GET'])
def get_data():
    if not session.get('logged_in') or not session.get('user'): 
        return jsonify({}), 401
    history_data = load_json_safe(FILES['data'], {})
    profiles = load_json_safe(FILES['profile'], {})
    result = {}
    for uid, leaders in history_data.items():
        if not isinstance(leaders, list): continue
        p_data = profiles.get(uid)
        if not isinstance(p_data, dict): p_data = {}
        p_basic = p_data.get('basicInfo', {}) if isinstance(p_data.get('basicInfo'), dict) else {}
        p_clan = p_data.get('clanBasicInfo', {}) if isinstance(p_data.get('clanBasicInfo'), dict) else {}
        formatted_leaders = []
        for l in leaders:
            try:
                l_uid, timestamp = l.split(': ', 1)
                l_profile = profiles.get(l_uid, {})
                if not isinstance(l_profile, dict): l_profile = {}
                l_basic = l_profile.get('basicInfo', {}) if isinstance(l_profile.get('basicInfo'), dict) else {}
                l_clan = l_profile.get('clanBasicInfo', {}) if isinstance(l_profile.get('clanBasicInfo'), dict) else {}
                formatted_leaders.append({
                    "uid": l_uid, "timestamp": timestamp, "name": l_basic.get('nickname', 'Unknown'),
                    "headPic": l_basic.get('headPic', '902000003'), "guild": l_clan.get('clanName', 'No Guild'),
                    "guildId": str(l_clan.get('clanId', 'N/A'))
                })
            except Exception: pass
        result[uid] = {
            "leaders": formatted_leaders, "name": p_basic.get('nickname', 'Unknown'),
            "headPic": p_basic.get('headPic', '902000003'), "level": p_basic.get('level', 0),
            "liked": p_basic.get('liked', 0), "region": p_basic.get('region', 'N/A'),
            "guild": p_clan.get('clanName', 'No Guild'), "guildId": str(p_clan.get('clanId', 'N/A')),
            "leader": str(p_clan.get('captainId', 'N/A'))
        }
    return jsonify(result)

@app.route('/api/spam', methods=['GET'])
def get_spam():
    if not session.get('logged_in') or not session.get('user'): 
        return jsonify({}), 401
    targets = load_json_safe(FILES['targets_txt'], {})
    active = {t['uid']: t for t in load_json_safe(FILES['active'], []) if isinstance(t, dict)}
    info = load_json_safe(FILES['info'], {})
    l_to_t = {}
    for t_uid, d in info.items():
        if isinstance(d, dict):
            l_uid = d.get('leader')
            if l_uid and l_uid != "N/A": l_to_t[l_uid] = t_uid
    result = {}
    for bot, uids in targets.items():
        if not isinstance(uids, list): continue
        res_list = []
        for u in uids:
            if u in active: src = "Added By Owner (Target)"
            elif u in l_to_t: src = f"Leader of {l_to_t[u]}"
            else: src = "Unknown"
            res_list.append({"uid": u, "source": src})
        result[bot] = res_list
    return jsonify(result)

@app.route('/api/whitelist', methods=['GET'])
def get_whitelist():
    if not session.get('logged_in') or not is_owner(session.get('user')): 
        return jsonify({"players": [], "guilds": []}), 401
    return jsonify(load_json_safe(FILES['whitelist'], {"players": [], "guilds": []}))

@app.route('/api/whitelist/add', methods=['POST'])
def add_whitelist():
    if not session.get('logged_in') or not is_owner(session.get('user')): 
         return jsonify({"success": False}), 401
    data = request.json
    w_type = data.get('type')
    w_id = str(data.get('id')).strip()
    wl = load_json_safe(FILES['whitelist'], {"players": [], "guilds": []})
    if w_id not in wl[w_type]:
        wl[w_type].append(w_id)
        save_json_locked(FILES['whitelist'], wl)
    return jsonify({"success": True})

@app.route('/api/whitelist/remove', methods=['POST'])
def remove_whitelist():
    if not session.get('logged_in') or not is_owner(session.get('user')): 
         return jsonify({"success": False}), 401
    data = request.json
    w_type = data.get('type')
    w_id = str(data.get('id')).strip()
    wl = load_json_safe(FILES['whitelist'], {"players": [], "guilds": []})
    if w_id in wl[w_type]:
        wl[w_type].remove(w_id)
        save_json_locked(FILES['whitelist'], wl)
    return jsonify({"success": True})

@app.route('/api/admin/clear_data', methods=['POST'])
def clear_database_data():
    if not session.get('logged_in') or not is_creator(session['user']):
        return jsonify({"success": False, "msg": "Unauthorized Access"}), 401
    data = request.json or {}
    target = str(data.get('target', '')).strip().lower()
    try:
        if target == 'stock':
            save_json_locked(STOCK_FILE, [])
            msg = "Stock accounts database successfully cleared!"
        elif target == 'api':
            save_json_locked(FILES['api_json'], [])
            msg = "API accounts database successfully cleared!"
        elif target == 'bot':
            save_json_locked(FILES['bot'], [])
            msg = "Live tracker bots (bot.json) successfully cleared!"
        elif target == 'vv':
            save_json_locked(FILES['vv'], {})
            msg = "Live attacker bots (vv.json) successfully cleared!"
        elif target == 'targets':
            save_json_locked(FILES['targets_txt'], {})
            msg = "Attacker distribution targets successfully cleared!"
        elif target == 'check':
            save_json_locked(FILES['check_txt'], {})
            msg = "Tracker distribution targets successfully cleared!"
        elif target == 'active':
            save_json_locked(FILES['active'], [])
            save_json_locked(FILES['profile'], {}) 
            distribute_targets()
            msg = "Active targets queue successfully cleared!"
        elif target == 'data':
            save_json_locked(FILES['data'], {})
            msg = "Historical leader logs (data.json) successfully cleared!"
        elif target == 'info':
            save_json_locked(FILES['info'], {})
            save_json_locked(FILES['live'], {})
            msg = "Live status logs successfully cleared!"
        elif target == 'members':
            members = [{
                "name": "System Creator", "pic": "902000003", "username": "creator",
                "password": "123", "role": "creator", "limit": 999999, "active_limit": 999999
            }]
            save_json_locked(FILES['members'], members)
            msg = "Admins database successfully cleared!"
        else:
            return jsonify({"success": False, "msg": "Unknown database category."}), 400
        return jsonify({"success": True, "msg": msg})
    except Exception as e:
        return jsonify({"success": False, "msg": f"Purge operation failed: {str(e)}"}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 20669))
    app.run(host='0.0.0.0', port=port)

# END OF FILE app.py
