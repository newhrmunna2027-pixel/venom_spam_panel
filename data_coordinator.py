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

# MongoDB Configuration (From your credentials)
MONGO_URI = os.environ.get("MONGO_URI", "mongodb+srv://munnadhali017_db_user:m0172326@cluster0.beetmpq.mongodb.net/?appName=Cluster0")
MONGO_DB_NAME = "out_of_law_db"

mongo_client = None
mongo_db = None
MONGO_CONNECTED = False

if MONGO_AVAILABLE:
    try:
        mongo_client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
        mongo_db = mongo_client[MONGO_DB_NAME]
        mongo_client.server_info()  # Force connection check to verify status
        MONGO_CONNECTED = True
        print(f"[✓] MongoDB Connected Successfully! Database: {MONGO_DB_NAME} (7 Core Collections Synced)")
    except Exception as e:
        print(f"[!] MongoDB Connection Failed: {e}. Falling back to SQLite/JSON exclusively.")


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
# 1ST TIME RUN MONGODB ⇄ LOCAL MIGRATION
# ==========================================
def init_mongo():
    """Synchronizes MongoDB with Local DB perfectly on 1st startup"""
    global MONGO_CONNECTED
    if not MONGO_CONNECTED: 
        return
    
    print("[*] Initiating MongoDB ⇄ Local Database Sync for 7 Core Files...")

    # 1. Synchronize Members (members.json)
    if mongo_db['members'].count_documents({}) == 0:
        local_members = load_data('members.json', [], bypass_mongo=True)
        if local_members:
            mongo_db['members'].insert_many([dict(x) for x in local_members])
        else:
            default_member = [{
                "username": "creator", "password": "123", "name": "System Creator", 
                "pic": "902000003", "role": "creator", "limit": 999999, "active_limit": 999999
            }]
            mongo_db['members'].insert_many([dict(x) for x in default_member])
            save_data('members.json', default_member, sync_mongo=False)

    # 2. Synchronize Active Targets (active.json)
    if mongo_db['targets'].count_documents({}) == 0:
        local_targets = load_data('active.json', [], bypass_mongo=True)
        if local_targets:
            mongo_db['targets'].insert_many([dict(x) for x in local_targets])

    # 3. Synchronize API Accounts, Bot Accounts, Stock Accounts
    files_to_sync = [('api.json', 'api'), ('bot.json', 'bot'), ('account/stock.json', 'stock')]
    for filename, collection_name in files_to_sync:
        if mongo_db[collection_name].count_documents({}) == 0:
            local_data = load_data(filename, [], bypass_mongo=True)
            if local_data:
                mongo_db[collection_name].insert_many([dict(x) for x in local_data])

    # 4. Synchronize VV Accounts (Dict Format mapping)
    if mongo_db['vv'].count_documents({}) == 0:
        local_vv = load_data('vv.json', {}, bypass_mongo=True)
        if local_vv:
            vv_list = [{"uid": k, "password": v} for k, v in local_vv.items()]
            mongo_db['vv'].insert_many(vv_list)

    # 5. 🚀 Synchronize Profile Cached Data (profile.json)
    if mongo_db['profiles'].count_documents({}) == 0:
        local_profiles = load_data('profile.json', {}, bypass_mongo=True)
        if local_profiles:
            profile_list = [{"uid": k, "val": v} for k, v in local_profiles.items()]
            mongo_db['profiles'].insert_many(profile_list)


# ==========================================
# UNIVERSAL DATA LOADER
# ==========================================
def load_data(filepath, default, bypass_mongo=False):
    """Loads data dynamically. Prioritizes MongoDB -> SQLite -> JSON"""
    normalized_path = filepath.replace('\\', '/').strip()
    filename = os.path.basename(normalized_path)
    
    # 🚀 MONGODB INTERCEPTOR FOR ALL 7 CORE COLLECTIONS
    if MONGO_CONNECTED and not bypass_mongo:
        try:
            if filename == 'members.json':
                rows = list(mongo_db['members'].find({}, {"_id": 0}))
                return rows if rows else default
                
            elif filename == 'active.json':
                rows = list(mongo_db['targets'].find({}, {"_id": 0}))
                return rows if rows else default
                
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
                
            elif filename in ['api.json', 'bot.json', 'stock.json']:
                col_name = filename.split('.')[0]
                rows = list(mongo_db[col_name].find({}, {"_id": 0}))
                return rows if rows else default
                
        except Exception as e:
            print(f"[Mongo Read Error] {filename}: {e}")

    # --- LOCAL FALLBACK FOR OTHER FILES (SQLite or Local JSON) ---
    if not USE_DB:
        if not os.path.exists(normalized_path):
            os.makedirs(os.path.dirname(normalized_path) if os.path.dirname(normalized_path) else '.', exist_ok=True)
            with open(normalized_path, 'w', encoding='utf-8') as f:
                json.dump(default, f, indent=4)
            return default
        try:
            with open(normalized_path, 'r', encoding='utf-8') as f:
                return json.load(f)
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
            return [{
                "uid": r["uid"], "name": r["name"], "reason": r["reason"], "duration": r["duration"], 
                "addTime": r["addTime"], "expireAt": r["expireAt"], "addedByUsername": r["addedByUsername"], 
                "addedByName": r["addedByName"], "addedByRole": r["addedByRole"], "status": r["status"]
            } for r in rows]

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
# UNIVERSAL DATA SAVER (WITH PURGE SYNC)
# ==========================================
def save_data(filepath, data, sync_mongo=True):
    """Saves data dynamically. MONGODB Live Update & Purges are handled natively!"""
    normalized_path = filepath.replace('\\', '/').strip()
    filename = os.path.basename(normalized_path)
    
    # 🚀 MONGODB LIVE SYNC & PURGE CONTROL INTERCEPTOR
    if MONGO_CONNECTED and sync_mongo:
        try:
            if filename == 'members.json':
                mongo_db['members'].delete_many({}) 
                if data: 
                    mongo_db['members'].insert_many([dict(x) for x in data])
                    
            elif filename == 'active.json':
                mongo_db['targets'].delete_many({}) 
                if data: 
                    mongo_db['targets'].insert_many([dict(x) for x in data])
                    
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
                    
            elif filename in ['api.json', 'bot.json', 'stock.json']:
                col_name = filename.split('.')[0]
                mongo_db[col_name].delete_many({})
                if data:
                    mongo_db[col_name].insert_many([dict(x) for x in data])
                
            # Keep physical backups for easy viewing
            if filename in ['members.json', 'active.json', 'api.json', 'bot.json', 'stock.json', 'vv.json', 'profile.json']:
                try:
                    os.makedirs(os.path.dirname(normalized_path) if os.path.dirname(normalized_path) else '.', exist_ok=True)
                    tmp_path = normalized_path + ".tmp"
                    with open(tmp_path, 'w', encoding='utf-8') as f:
                        json.dump(data, f, indent=4)
                    os.replace(tmp_path, normalized_path)
                except Exception:
                    pass
                return True
                
        except Exception as e:
            print(f"[Mongo Write Error] {filename}: {e}")

    # --- LOCAL FALLBACK SAVER (SQLite or Local JSON) ---
    if not USE_DB:
        os.makedirs(os.path.dirname(normalized_path) if os.path.dirname(normalized_path) else '.', exist_ok=True)
        tmp_path = normalized_path + ".tmp"
        try:
            with open(tmp_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4)
            os.replace(tmp_path, normalized_path)
            return True
        except Exception:
            return False

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
        return True
    except Exception as e:
        print(f"[DB SAVE ERROR] {filename}: {e}")
        return False
    finally:
        conn.close()

# Initialize DBs on script load
if USE_DB:
    init_db()

if MONGO_AVAILABLE:
    init_mongo()

# END OF FILE data_coordinator.py
