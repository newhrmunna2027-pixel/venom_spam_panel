# START OF FILE data_coordinator.py

import os
import json
import sqlite3

# ==========================================
# MONGODB INTEGRATION & TERMUX DNS FIX
# ==========================================
try:
    import dns.resolver
    # 🚀 CRITICAL FIX FOR TERMUX/ANDROID
    # Bypasses the missing /etc/resolv.conf error by forcing Google Public DNS
    dns.resolver.default_resolver = dns.resolver.Resolver(configure=False)
    dns.resolver.default_resolver.nameservers = ['8.8.8.8', '1.1.1.1']
    
    from pymongo import MongoClient
    MONGO_AVAILABLE = True
except ImportError:
    MONGO_AVAILABLE = False
    print("[!] 'pymongo' or 'dnspython' is not installed. Run 'pip install pymongo dnspython'.")

DB_FILE = "database.db"
USE_DB = os.environ.get("USE_DB") == "TRUE"

# 🚀 মঙ্গোডিবি সিঙ্ক শুধুমাত্র ম্যানেজার বটের মাধ্যমে রান করলেই চালু হবে
MONGO_SYNC_ENABLED = os.environ.get("MONGO_SYNC_ENABLED") == "TRUE"

# MongoDB Configuration
MONGO_URI = os.environ.get("MONGO_URI", "mongodb+srv://munnadhali017_db_user:m0172326@cluster0.beetmpq.mongodb.net/?appName=Cluster0")
MONGO_DB_NAME = "venom_db"

mongo_client = None
mongo_db = None
MONGO_CONNECTED = False

# শুধুমাত্র MONGO_SYNC_ENABLED সত্য হলেই মঙ্গোডিবি কানেক্ট হবে
if MONGO_AVAILABLE and MONGO_SYNC_ENABLED:
    try:
        mongo_client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
        mongo_db = mongo_client[MONGO_DB_NAME]
        mongo_client.server_info()  # Force connection check to verify status
        MONGO_CONNECTED = True
        print(f"[✓] MongoDB Connected Successfully! Database: {MONGO_DB_NAME} (Active Background Sync Mode)")
    except Exception as e:
        print(f"[!] MongoDB Connection Failed: {e}. Running exclusively on Local Physical Storage.")
else:
    MONGO_CONNECTED = False
    if MONGO_AVAILABLE:
        print("[*] MongoDB Sync Disabled (Running Standalone Mode). Using Local Physical Files.")


# ==========================================
# SQLITE DATABASE SETUP
# ==========================================
def get_db_connection():
    """Establishes an SQLite database connection using high-speed WAL journaling"""
    conn = sqlite3.connect(DB_FILE, timeout=30.0)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Creates database schema tables on system startup"""
    if not USE_DB:
        return
    conn = get_db_connection()
    try:
        conn.execute("CREATE TABLE IF NOT EXISTS configs (key TEXT PRIMARY KEY, val TEXT)")
        conn.execute("CREATE TABLE IF NOT EXISTS members (username TEXT PRIMARY KEY, password TEXT, name TEXT, pic TEXT, role TEXT, limit_val INTEGER, active_limit INTEGER)")
        conn.execute("CREATE TABLE IF NOT EXISTS targets (uid TEXT PRIMARY KEY, name TEXT, reason TEXT, duration TEXT, addTime INTEGER, expireAt TEXT, addedByUsername TEXT, addedByName TEXT, addedByRole TEXT, status TEXT)")
        conn.execute("CREATE TABLE IF NOT EXISTS profiles (uid TEXT PRIMARY KEY, val TEXT)")
        conn.execute("CREATE TABLE IF NOT EXISTS bot_status (bot_id TEXT PRIMARY KEY, id_val TEXT, name TEXT, status TEXT, timestamp TEXT, game_uid TEXT)")
        conn.execute("CREATE TABLE IF NOT EXISTS target_logs (id INTEGER PRIMARY KEY AUTOINCREMENT, action TEXT, uid TEXT, name TEXT, duration TEXT, by_val TEXT, time_val INTEGER)")
        conn.execute("CREATE TABLE IF NOT EXISTS bad_accounts (id INTEGER PRIMARY KEY AUTOINCREMENT, uid TEXT, source TEXT, reason TEXT, time_val TEXT)")
        conn.execute("CREATE TABLE IF NOT EXISTS history (id INTEGER PRIMARY KEY AUTOINCREMENT, time_val TEXT, action TEXT, uid TEXT, name TEXT)")
        conn.commit()
    except Exception as e:
        print(f"[DB INIT ERROR] {e}")
    finally:
        conn.close()


# ==========================================
# DEDUPLICATION HELPER FOR ACTIVE TARGETS
# ==========================================
def _deduplicate_targets(targets):
    """Prevents overlapping duplicate entries for active targets"""
    if not isinstance(targets, list):
        return targets
    seen = set()
    deduped = []
    for t in targets:
        if isinstance(t, dict) and 'uid' in t:
            uid_str = str(t['uid']).strip()
            if uid_str not in seen:
                seen.add(uid_str)
                deduped.append(t)
        else:
            deduped.append(t)
    return deduped


# ==========================================
# SAFE EXPIRE PARSER TO PREVENT EXPIRATION ERRORS
# ==========================================
def parse_expire_time(expire_at):
    """Safely converts expire_at string/float to int. Falls back to permanent on error."""
    if expire_at == 'permanent' or expire_at is None:
        return 'permanent'
    try:
        # Handles decimal string representations like "1719680000000.0" safely
        return int(float(expire_at))
    except (ValueError, TypeError):
        return 'permanent'


# ==========================================
# UNIVERSAL DATA LOADER (LOCAL-FIRST)
# ==========================================
def load_data(filepath, default, bypass_mongo=True):
    """Loads data dynamically. Defaults to bypass_mongo=True to enforce Local Physical reading first."""
    normalized_path = filepath.replace('\\', '/').strip()
    filename = os.path.basename(normalized_path)
    
    # 🚀 MONGODB DIRECT ACCESS (USED EXCLUSIVELY FOR SYNCHRONIZATION RUNS)
    if MONGO_CONNECTED and not bypass_mongo:
        try:
            if filename == 'members.json':
                rows = list(mongo_db['members'].find({}, {"_id": 0}))
                return rows if rows else default
                
            elif filename == 'active.json':
                rows = list(mongo_db['targets'].find({}, {"_id": 0}))
                return _deduplicate_targets(rows) if rows else default
                
            elif filename == 'vv.json':
                rows = list(mongo_db['vv'].find({}, {"_id": 0}))
                if rows:
                    return {r['uid']: r['password'] for r in rows}
                return default
                
            elif filename == 'profile.json':
                rows = list(mongo_db['profiles'].find({}, {"_id": 0}))
                if rows:
                    return {r['uid']: r['val'] for r in rows}
                return default

            elif filename == 'limit.json':
                row = mongo_db['limit'].find_one({}, {"_id": 0})
                return row if row else default
                
            elif filename in ['api.json', 'bot.json', 'stock.json']:
                col_name = filename.split('.')[0]
                rows = list(mongo_db[col_name].find({}, {"_id": 0}))
                return rows if rows else default
                
            # 🚀 মঙ্গোডিবি নতুন ফাইলের সাপোর্ট
            elif filename == 'ex.json':
                rows = list(mongo_db['ex'].find({}, {"_id": 0}))
                return rows if rows else default
                
            elif filename == 'whitelist.json':
                row = mongo_db['whitelist'].find_one({}, {"_id": 0})
                return row if row else default
                
            elif filename == 'data.json':
                row = mongo_db['data'].find_one({}, {"_id": 0})
                return row if row else default
                
        except Exception as e:
            print(f"[Mongo Direct Read Error] {filename}: {e}")

    # --- PRIMARY LOCAL READING FROM PHYSICAL DISK ---
    if not USE_DB:
        if not os.path.exists(normalized_path):
            os.makedirs(os.path.dirname(normalized_path) if os.path.dirname(normalized_path) else '.', exist_ok=True)
            with open(normalized_path, 'w', encoding='utf-8') as f:
                json.dump(default, f, indent=4)
            return default
        try:
            with open(normalized_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if filename == 'active.json':
                    return _deduplicate_targets(data)
                return data
        except Exception:
            return default

    conn = get_db_connection()
    try:
        if filename == 'members.json':
            cursor = conn.execute("SELECT * FROM members")
            rows = cursor.fetchall()
            if not rows:
                return default
            return [{
                "username": r["username"], "password": r["password"], "name": r["name"], 
                "pic": r["pic"], "role": r["role"], "limit": r["limit_val"], 
                "active_limit": r["active_limit"]
            } for r in rows]

        elif filename == 'active.json':
            cursor = conn.execute("SELECT * FROM targets")
            rows = cursor.fetchall()
            loaded = [{
                "uid": r["uid"], "name": r["name"], "reason": r["reason"], "duration": r["duration"], 
                "addTime": r["addTime"], "expireAt": r["expireAt"], "addedByUsername": r["addedByUsername"], 
                "addedByName": r["addedByName"], "addedByRole": r["addedByRole"], "status": r["status"]
            } for r in rows]
            return _deduplicate_targets(loaded)

        elif filename == 'profile.json':
            cursor = conn.execute("SELECT uid, val FROM profiles")
            rows = cursor.fetchall()
            result = {}
            for r in rows:
                try:
                    result[r["uid"]] = json.loads(r["val"])
                except Exception:
                    pass
            return result

        elif filename == 'bots_live_status.json':
            cursor = conn.execute("SELECT * FROM bot_status")
            rows = cursor.fetchall()
            return {
                r["bot_id"]: {
                    "Id": r["id_val"], "Name": r["name"], "Status": r["status"], 
                    "Timestamp": r["timestamp"], "Game uid": r["game_uid"]
                } for r in rows
            }

        elif filename == 'target_logs.json':
            cursor = conn.execute("SELECT * FROM target_logs ORDER BY id DESC")
            return [{
                "action": r["action"], "uid": r["uid"], "name": r["name"], 
                "duration": r["duration"], "by": r["by_val"], "time": r["time_val"]
            } for r in cursor.fetchall()]

        elif filename == 'bad_accounts.json':
            cursor = conn.execute("SELECT * FROM bad_accounts ORDER BY id DESC")
            return [{
                "uid": r["uid"], "source": r["source"], "reason": r["reason"], "time": r["time_val"]
            } for r in cursor.fetchall()]

        elif filename == 'history.json':
            cursor = conn.execute("SELECT * FROM history ORDER BY id DESC")
            return [{
                "time": r["time_val"], "action": r["action"], "uid": r["uid"], "name": r["name"]
            } for r in cursor.fetchall()]

        else:
            cursor = conn.execute("SELECT val FROM configs WHERE key = ?", (filename,))
            row = cursor.fetchone()
            if row:
                try:
                    return json.loads(row["val"])
                except Exception:
                    return default
            return default
            
    except Exception as e:
        return default
    finally:
        conn.close()


# ==========================================
# UNIVERSAL DATA SAVER (LOCAL-FIRST SAVING & MONGO SYNC)
# ==========================================
def save_data(filepath, data, sync_mongo=True):
    """Saves data physically to the local disk/SQLite first, then replicates to MongoDB."""
    normalized_path = filepath.replace('\\', '/').strip()
    filename = os.path.basename(normalized_path)
    
    if filename == 'active.json':
        data = _deduplicate_targets(data)

    # --- STEP 1: PHYSICAL WRITE TO DISK OR SQLITE DATABASE ---
    local_saved = False
    if not USE_DB:
        try:
            os.makedirs(os.path.dirname(normalized_path) if os.path.dirname(normalized_path) else '.', exist_ok=True)
            tmp_path = normalized_path + ".tmp"
            with open(tmp_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4)
            os.replace(tmp_path, normalized_path)
            local_saved = True
        except Exception as e:
            print(f"[Physical Save Error] {filename}: {e}")
    else:
        conn = get_db_connection()
        try:
            if filename == 'members.json':
                conn.execute("DELETE FROM members")
                for u in data:
                    conn.execute("INSERT INTO members (username, password, name, pic, role, limit_val, active_limit) VALUES (?, ?, ?, ?, ?, ?, ?)",
                                 (u.get("username"), u.get("password"), u.get("name"), u.get("pic"), u.get("role"), u.get("limit"), u.get("active_limit")))

            elif filename == 'active.json':
                conn.execute("DELETE FROM targets")
                for t in data:
                    conn.execute("INSERT INTO targets (uid, name, reason, duration, addTime, expireAt, addedByUsername, addedByName, addedByRole, status) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                                 (t.get("uid"), t.get("name"), t.get("reason"), t.get("duration"), t.get("addTime"), str(t.get("expireAt")), t.get("addedByUsername"), t.get("addedByName"), t.get("addedByRole"), t.get("status")))

            elif filename == 'profile.json':
                conn.execute("DELETE FROM profiles")
                for uid, val in data.items():
                    conn.execute("INSERT INTO profiles (uid, val) VALUES (?, ?)", (uid, json.dumps(val)))

            elif filename == 'bots_live_status.json':
                conn.execute("DELETE FROM bot_status")
                for bot_id, val in data.items():
                    conn.execute("INSERT INTO bot_status (bot_id, id_val, name, status, timestamp, game_uid) VALUES (?, ?, ?, ?, ?, ?)",
                                 (bot_id, val.get("Id"), val.get("Name"), val.get("Status"), val.get("Timestamp"), val.get("Game uid")))

            elif filename == 'target_logs.json':
                conn.execute("DELETE FROM target_logs")
                for log in data:
                    conn.execute("INSERT INTO target_logs (action, uid, name, duration, by_val, time_val) VALUES (?, ?, ?, ?, ?, ?)",
                         (log.get("action"), log.get("uid"), log.get("name"), log.get("duration"), log.get("by"), log.get("time")))

            elif filename == 'bad_accounts.json':
                conn.execute("DELETE FROM bad_accounts")
                for bad in data:
                    conn.execute("INSERT INTO bad_accounts (uid, source, reason, time_val) VALUES (?, ?, ?, ?)",
                                 (bad.get("uid"), bad.get("source"), bad.get("reason"), bad.get("time")))

            elif filename == 'history.json':
                conn.execute("DELETE FROM history")
                for h in data:
                    conn.execute("INSERT INTO history (time_val, action, uid, name) VALUES (?, ?, ?, ?)",
                                     (h.get("time"), h.get("action"), h.get("uid"), h.get("name")))

            else:
                conn.execute("INSERT OR REPLACE INTO configs (key, val) VALUES (?, ?)", (filename, json.dumps(data)))
                
            conn.commit()
            local_saved = True
        except Exception as e:
            print(f"[SQLite Save Error] {filename}: {e}")
        finally:
            conn.close()

    # Always keep updated backup JSON files for visual alignment
    if filename in ['members.json', 'active.json', 'api.json', 'bot.json', 'stock.json', 'vv.json', 'profile.json', 'limit.json', 'ex.json', 'whitelist.json', 'data.json']:
        try:
            os.makedirs(os.path.dirname(normalized_path) if os.path.dirname(normalized_path) else '.', exist_ok=True)
            tmp_path = normalized_path + ".tmp"
            with open(tmp_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4)
            os.replace(tmp_path, normalized_path)
        except Exception:
            pass

    # --- STEP 2: REPLICATE DIRECTLY TO MONGODB IN BACKGROUND ---
    if MONGO_CONNECTED and sync_mongo:
        try:
            if filename == 'members.json':
                mongo_db['members'].delete_many({}) 
                if data: mongo_db['members'].insert_many([dict(x) for x in data])
                
            elif filename == 'active.json':
                mongo_db['targets'].delete_many({}) 
                if data: mongo_db['targets'].insert_many([dict(x) for x in data])
                
            elif filename == 'vv.json':
                mongo_db['vv'].delete_many({})
                if data:
                    vv_list = [{"uid": k, "password": v} for k, v in data.items()]
                    mongo_db['vv'].insert_many(vv_list)
                    
            elif filename == 'profile.json':
                mongo_db['profiles'].delete_many({})
                if data:
                    profile_list = [{"uid": k, "val": v} for k, v in data.items()]
                    mongo_db['profiles'].insert_many(profile_list)

            elif filename == 'limit.json':
                mongo_db['limit'].delete_many({})
                if data: mongo_db['limit'].insert_one(dict(data))
                
            elif filename in ['api.json', 'bot.json', 'stock.json']:
                col_name = filename.split('.')[0]
                mongo_db[col_name].delete_many({})
                if data: mongo_db[col_name].insert_many([dict(x) for x in data])
                
            # 🚀 মঙ্গোডিবি নতুন ফাইলের রিয়েল-টাইম সিঙ্ক
            elif filename == 'ex.json':
                mongo_db['ex'].delete_many({})
                if data: mongo_db['ex'].insert_many([dict(x) for x in data])
                
            elif filename == 'whitelist.json':
                mongo_db['whitelist'].delete_many({})
                if data: mongo_db['whitelist'].insert_one(dict(data))
                
            elif filename == 'data.json':
                mongo_db['data'].delete_many({})
                if data: mongo_db['data'].insert_one(dict(data))
                
        except Exception as e:
            print(f"[Mongo Live Write Error] {filename}: {e}")

    return local_saved


# ==========================================
# BIDIRECTIONAL STARTUP SYNCHRONIZATION
# ==========================================
def init_mongo():
    """Synchronizes MongoDB with Local DB on startup.
    1. Loads live data from MongoDB to physical files on first run (MongoDB is Master).
    2. If MongoDB is empty but Local has data, pushes local data to MongoDB to initialize.
    """
    global MONGO_CONNECTED
    if not MONGO_CONNECTED: 
        return
    
    print("[*] Initiating MongoDB ⇄ Local Physical File Sync...")

    # Generalized startup sync helper
    def sync_startup(filename, default_val):
        # Load from MongoDB directly
        mongo_data = load_data(filename, default_val, bypass_mongo=False)
        # Load from Local Physical File
        local_data = load_data(filename, default_val, bypass_mongo=True)

        # Condition 1: If MongoDB has data (not empty/default), write to local physical file
        if mongo_data and mongo_data != default_val:
            save_data(filename, mongo_data, sync_mongo=False)
            print(f"[✓] Loaded {filename} from MongoDB directly to Physical File.")
        # Condition 2: If MongoDB is empty but Local has data, push to MongoDB
        elif local_data and local_data != default_val:
            save_data(filename, local_data, sync_mongo=True)
            print(f"[✓] Pushed Local {filename} data to MongoDB (Cloud Initialized).")

    # members.json sync (separately to handle default creator account fallback)
    members_mongo = load_data('members.json', [], bypass_mongo=False)
    members_local = load_data('members.json', [], bypass_mongo=True)
    if members_mongo:
        save_data('members.json', members_mongo, sync_mongo=False)
        print("[✓] Loaded members.json from MongoDB directly to Physical File.")
    elif members_local:
        save_data('members.json', members_local, sync_mongo=True)
        print("[✓] Pushed Local members.json data to MongoDB (Cloud Initialized).")
    else:
        # Default Creator Account initialization
        default_member = [{
            "username": "creator", "password": "123", "name": "System Creator", 
            "pic": "902000003", "role": "creator", "limit": 999999, "active_limit": 999999
        }]
        save_data('members.json', default_member, sync_mongo=True)
        print("[✓] Initialized members.json with default Creator account on both local and cloud.")

    # Core synchronization runs
    sync_startup('active.json', [])
    sync_startup('api.json', [])
    sync_startup('bot.json', [])
    sync_startup('account/stock.json', [])
    sync_startup('vv.json', {})
    sync_startup('profile.json', {})
    
    # 🚀 মঙ্গোডিবি নতুন ৩টি ফাইল ক্লাউড সিঙ্ক রান
    sync_startup('ex.json', [])
    sync_startup('whitelist.json', {"players": [], "guilds": []})
    sync_startup('data.json', {})

    # limit.json configuration sync
    limits_mongo = load_data('limit.json', {}, bypass_mongo=False)
    limits_local = load_data('limit.json', {}, bypass_mongo=True)
    if limits_mongo:
        save_data('limit.json', limits_mongo, sync_mongo=False)
        print("[✓] Loaded limit.json from MongoDB directly to Physical File.")
    elif limits_local:
        save_data('limit.json', limits_local, sync_mongo=True)
        print("[✓] Pushed Local limit.json data to MongoDB (Cloud Initialized).")
    else:
        default_limit = {
            "global_limit": 40, 
            "api_limit": 20, 
            "default_line_3": "TIKTOK [FF00FF]→OUT OF LAW",
            "allow_user_add_bot": True
        }
        save_data('limit.json', default_limit, sync_mongo=True)
        print("[✓] Initialized limit.json with default configuration on both local and cloud.")

    print("[✓] Startup Sync Engine Completed successfully!")


# Initialize DBs on script load
if USE_DB:
    init_db()

if MONGO_AVAILABLE:
    init_mongo()

# END OF FILE data_coordinator.py
