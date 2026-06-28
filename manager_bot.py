# -*- coding: utf-8 -*-
# START OF FILE manager_bot.py

import subprocess
import time
import json
import os
import sys
import math
import psutil
from threading import Thread

# central environmental db toggle
os.environ["USE_DB"] = "TRUE"
import data_coordinator

# Configurations
MAINTENANCE_FILE = 'maintenance.json'
LIMIT_FILE = 'limit.json'
RUN_TIME_HOURS = 5
MAINTENANCE_TIME_MINS = 10

# Process holders
p_app = None
p_main = None
p_info = None

# Local DB Configurations
USERS_DIR = 'users'
BAD_ACCS_FILE = 'bad_accounts.json'
BOT_FILE = 'bot.json'
VV_FILE = 'vv.json'
ACTIVE_FILE = 'active.json'
MEMBERS_FILE = 'members.json'
CHECK_FILE = 'check.txt'
LIVE_FILE = 'bots_live_status.json'
STOCK_FILE = 'account/stock.json'
API_FILE = 'api.json'
TARGETS_TXT = 'targets.txt'
INFO_JSON = 'info.json'
UID_JSON = 'uid.json'

def load_json(path, default):
    return data_coordinator.load_data(path, default)

def save_json(path, data):
    data_coordinator.save_data(path, data)

def get_user_bots(username):
    path = os.path.join(USERS_DIR, f"{username}.json")
    data = load_json(path, {"bot": [], "vv": [], "failed": []})
    
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
    save_json(path, data)

def normalize_bot_list(bots_data, key):
    raw_data = bots_data.get(key, [])
    normalized = []
    
    if isinstance(raw_data, dict):
        for uid, password in raw_data.items():
            normalized.append({
                "uid": str(uid).strip(),
                "password": str(password).strip()
            })
            
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

def compile_master_bots():
    """Combines active bots from all users into main system files"""
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
                    
    save_json(BOT_FILE, master_bot)
    save_json(VV_FILE, master_vv)

def get_user_usable_limit(username):
    members = load_json(MEMBERS_FILE, [])
    user = next((m for m in members if m['username'] == username), None)
    
    if not user:
        return 0
        
    limit_cfg = load_json(LIMIT_FILE, {"global_limit": 200})
    global_limit = int(limit_cfg.get('global_limit', 200))

    if user.get('role') == 'owner':
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
    bot_data = load_json(BOT_FILE, [])
    active_data = load_json(ACTIVE_FILE, [])
    
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
                
    save_json(ACTIVE_FILE, active_data)
    
    bot_count = len(bot_data) if isinstance(bot_data, list) and len(bot_data) > 0 else 1
    distribution = {str(i): [] for i in range(1, bot_count + 1)}
    
    if bot_count > 0:
        for index, uid in enumerate(running_uids):
            distribution[str((index % bot_count) + 1)].append(uid)
            
    save_json(CHECK_FILE, distribution)

def auto_distribute_bots():
    limit_cfg = load_json(LIMIT_FILE, {"global_limit": 40, "api_limit": 2})
    global_limit = int(limit_cfg.get('global_limit', 40))
    api_limit = int(limit_cfg.get('api_limit', 2))
    
    stock = load_json(STOCK_FILE, [])
    api_bots = load_json(API_FILE, []) 
    bot_bots = load_json(BOT_FILE, [])
    vv_bots = load_json(VV_FILE, {})
    
    if not isinstance(api_bots, list):
        api_bots = []
    if not isinstance(bot_bots, list):
        bot_bots = []
    if not isinstance(vv_bots, dict):
        vv_bots = {}
    if not isinstance(stock, list):
        stock = []
    
    changed = False
    
    def pull_account():
        if len(stock) > 0:
            return stock.pop(0)
        return None

    if len(api_bots) < api_limit and len(stock) > 0:
        while len(api_bots) < api_limit and len(stock) > 0:
            new_acc = pull_account()
            if new_acc:
                api_bots.append({
                    "uid": str(new_acc['uid']).strip(),
                    "password": str(new_acc['password']).strip()
                })
                changed = True
            else:
                break

    check_data = load_json(CHECK_FILE, {})
    all_valid_uids = []
    if isinstance(check_data, dict):
        for ulist in check_data.values():
            if isinstance(ulist, list):
                all_valid_uids.extend([str(u).strip() for u in ulist if str(u).strip()])
                
    info_data = load_json(INFO_JSON, {})
    active_leaders = {}
    for t_uid, info in info_data.items():
        l_uid = info.get('leader')
        if l_uid and l_uid.isdigit() and len(l_uid) > 5:
            active_leaders[l_uid] = t_uid
            
    uid_data = load_json(UID_JSON, {})
    current_ts = time.time()
    
    for l_uid, source_uid in active_leaders.items():
        if l_uid not in uid_data:
            uid_data[l_uid] = {
                "expire_at": current_ts + 86400, 
                "permanent": False, 
                "source": source_uid, 
                "spam_on": True
            }
        else:
            uid_data[l_uid]["source"] = source_uid
            if "spam_on" not in uid_data[l_uid]:
                uid_data[l_uid]["spam_on"] = True
            if not uid_data[l_uid].get("permanent", False):
                uid_data[l_uid]["expire_at"] = current_ts + 86400
            
    expired_keys = [l_uid for l_uid, meta in uid_data.items() if not meta.get("permanent", False) and current_ts > meta.get("expire_at", 0)]
    for k in expired_keys:
        del uid_data[k]
        
    save_json(UID_JSON, uid_data)
    
    valid_leader_uids = [u for u in active_leaders.keys() if uid_data.get(u, {}).get("spam_on", True)]
    total_uids_to_spam = list(set(all_valid_uids + valid_leader_uids))
    
    whitelist = load_json('whitelist.json', {"players": [], "guilds": []})
    profiles = load_json('profile.json', {})
    filtered_uids = []
    
    for u in total_uids_to_spam:
        u_str = str(u)
        if u_str in whitelist.get("players", []):
            continue
        clan_id = str(profiles.get(u_str, {}).get("clanBasicInfo", {}).get("clanId", "N/A"))
        if clan_id != "N/A" and clan_id in whitelist.get("guilds", []):
            continue
        filtered_uids.append(u_str)

    num_attacker_keys = len(vv_bots) if len(vv_bots) > 0 else 1
    chunk_size_att = len(filtered_uids) // num_attacker_keys
    remainder_att = len(filtered_uids) % num_attacker_keys
    last_chunk_att_size = chunk_size_att + (1 if (num_attacker_keys - 1) < remainder_att else 0) if filtered_uids else 0
    
    add_attacker = False
    if last_chunk_att_size >= 1:
        add_attacker = True
    if len(vv_bots) < 2:
        add_attacker = True

    max_vv_slots = global_limit * 2
    if len(vv_bots) >= max_vv_slots:
        add_attacker = False

    if add_attacker and len(stock) > 0:
        new_acc = pull_account()
        if new_acc:
            vv_bots[str(new_acc['uid'])] = new_acc['password']
            changed = True
            num_attacker_keys = len(vv_bots)
            print(f"[+] Scaled Attackers! Added Bot: {new_acc['uid']} (Max Slot Capacity: {max_vv_slots})")

    seq_keys_att = [str(i) for i in range(1, num_attacker_keys + 1)]
    targets_data = {k: [] for k in seq_keys_att}
    
    if seq_keys_att and filtered_uids:
        chunk_size_att = len(filtered_uids) // num_attacker_keys
        remainder_att = len(filtered_uids) % num_attacker_keys
        start = 0
        for i, k in enumerate(seq_keys_att):
            end = start + chunk_size_att + (1 if i < remainder_att else 0)
            targets_data[k] = filtered_uids[start:end]
            start = end
            
    save_json(TARGETS_TXT, targets_data)

    num_tracker_keys = len(bot_bots) if len(bot_bots) > 0 else 1
    chunk_size_tr = len(all_valid_uids) // num_tracker_keys
    remainder_tr = len(all_valid_uids) % num_tracker_keys
    last_chunk_tr_size = chunk_size_tr + (1 if (num_tracker_keys - 1) < remainder_tr else 0) if all_valid_uids else 0
    
    add_tracker = False
    if last_chunk_tr_size >= 3:
        add_tracker = True
    if len(bot_bots) < 1:
        add_tracker = True

    max_tracker_slots = math.ceil(global_limit / 3)
    if len(bot_bots) >= max_tracker_slots:
        add_tracker = False

    if add_tracker and len(stock) > 0:
        new_acc = pull_account()
        if new_acc:
            bot_bots.append(new_acc)
            changed = True
            print(f"[+] Scaled Trackers! Added Bot: {new_acc['uid']} (Max Slot Capacity: {max_tracker_slots})")

    if changed:
        save_json(STOCK_FILE, stock)
        save_json(API_FILE, api_bots)
        save_json(BOT_FILE, bot_bots)
        save_json(VV_FILE, vv_bots)
        distribute_targets()

def process_bad_accounts():
    """Manager watches bad accounts every second, processes, and purges instantly"""
    bad_accs = load_json(BAD_ACCS_FILE, [])
    if not bad_accs:
        return
        
    save_json(BAD_ACCS_FILE, [])
    
    # 🟢 DYNAMIC ORPHAN SYSTEM CLEANER
    global_bot_bots = load_json(BOT_FILE, [])
    global_vv_bots = load_json(VV_FILE, {})
    global_changed = False
    
    for bad in bad_accs:
        bad_uid = str(bad.get('uid'))
        source = str(bad.get('source', ''))
        
        if source == 'bot.json':
            temp_bots = []
            for b in global_bot_bots:
                current_uid = str(b.get('uid') if isinstance(b, dict) else b)
                if current_uid != bad_uid:
                    temp_bots.append(b)
                    
            if len(temp_bots) != len(global_bot_bots):
                global_bot_bots = temp_bots
                global_changed = True
                
        elif source == 'vv.json':
            if bad_uid in global_vv_bots:
                del global_vv_bots[bad_uid]
                global_changed = True
                
    if global_changed:
        save_json(BOT_FILE, global_bot_bots)
        save_json(VV_FILE, global_vv_bots)
            
    changed = False
    if os.path.exists(USERS_DIR):
        for filename in os.listdir(USERS_DIR):
            if not filename.endswith('.json'):
                continue
                
            username = filename[:-5]
            user_data = get_user_bots(username)
            user_changed = False
            
            for bad in bad_accs:
                uid = str(bad.get('uid'))
                source = str(bad.get('source', ''))
                
                if source == 'bot.json':
                    bot_list = user_data.get('bot', [])
                    new_bot = []
                    found = False
                    for b in bot_list:
                        if str(b.get('uid')) == uid:
                            bad['type'] = 'Tracker Server'
                            if 'failed' not in user_data:
                                user_data['failed'] = []
                            user_data['failed'].insert(0, bad)
                            found = True
                            user_changed = True
                        else:
                            new_bot.append(b)
                    if found:
                        user_data['bot'] = new_bot
                        
                elif source == 'vv.json':
                    vv_list = user_data.get('vv', [])
                    new_vv = []
                    found = False
                    for v in vv_list:
                        if str(v.get('uid')) == uid:
                            bad['type'] = 'Attack Server'
                            if 'failed' not in user_data:
                                user_data['failed'] = []
                            user_data['failed'].insert(0, bad)
                            found = True
                            user_changed = True
                        else:
                            new_vv.append(v)
                    if found:
                        user_data['vv'] = new_vv
                        
            if user_changed:
                save_user_bots(username, user_data)
                changed = True
                
    # safe purge from bots_live_status.json (Console Status) immediately
    live_status = load_json(LIVE_FILE, {})
    live_changed = False
    for key, bot_data in list(live_status.items()):
        bot_uid = str(bot_data.get('Game uid', ''))
        bot_id = str(bot_data.get('Id', ''))
        for bad in bad_accs:
            bad_uid = str(bad.get('uid'))
            if bot_uid == bad_uid or bot_id == bad_uid:
                del live_status[key]
                live_changed = True
                break
                
    if live_changed:
        save_json(LIVE_FILE, live_status)
            
    if changed or global_changed:
        compile_master_bots()
        distribute_targets()

def kill_orphaned_instances():
    """Guarantees absolute termination of previous script instances to prevent duplicates"""
    current_pid = os.getpid()
    scripts_to_kill = ['main.py', 'info.py', 'app.py']
    
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            cmd = proc.info['cmdline']
            if cmd:
                cmd_str = ' '.join(cmd).lower()
                if any(script in cmd_str for script in scripts_to_kill) and proc.info['pid'] != current_pid:
                    proc.kill()
        except Exception:
            pass

def system_daemon():
    """১-সেকেন্ডের রিয়েল-টাইম ডেমো থ্রেড লুপ"""
    while True:
        try:
            process_bad_accounts()
            auto_distribute_bots()
        except Exception:
            pass
        time.sleep(1)

def set_maintenance(status, duration_secs=0):
    end_time = int(time.time() + duration_secs) if status else 0
    data = {"status": status, "end_time": end_time}
    save_json(MAINTENANCE_FILE, data)
    status_str = "ON" if status else "OFF"
    print(f"[*] Maintenance mode turned {status_str}")

def start_process(script_name):
    print(f"[+] Starting {script_name}...")
    my_env = os.environ.copy()
    my_env["USE_DB"] = "TRUE" # enforce sqlite for spawned scripts
    return subprocess.Popen([sys.executable, script_name], env=my_env)

def stop_process(proc, script_name):
    if proc and proc.poll() is None:
        print(f"[-] Stopping {script_name}...")
        proc.terminate()
        proc.wait()

def main():
    global p_app, p_main, p_info
    
    print("=========================================")
    print("    OUT OF LAW - SUPERVISOR ACTIVE       ")
    print("=========================================\n")
    
    set_maintenance(False)

    print("[*] Cleaning legacy background operations...")
    kill_orphaned_instances()
    time.sleep(1)

    # Clean existing status file on fresh startup
    save_json(LIVE_FILE, {})

    # ডেমো থ্রেড স্টার্ট করা
    watcher_thread = Thread(target=system_daemon, daemon=True)
    watcher_thread.start()
    print("[✓] Dynamic System Daemon Watcher Active (1s Loop).")

    # ক্রমানুসারে সবগুলো স্ক্রিপ্ট সঠিকভাবে চালু করা হচ্ছে (API.py Removed)
    p_app = start_process('app.py')
    time.sleep(3)
    p_info = start_process('info.py')
    time.sleep(2)
    p_main = start_process('main.py')
    
    print("\n[✓] ALL 3 CORE SYSTEMS ARE ONLINE AND RUNNING! (API Merged)")

    run_time_secs = RUN_TIME_HOURS * 3600
    maintenance_time_secs = MAINTENANCE_TIME_MINS * 60

    try:
        while True:
            print(f"\n[*] Next maintenance scheduled in {RUN_TIME_HOURS} hours.")
            time.sleep(run_time_secs)

            print("\n[!] === INITIATING SCHEDULED MAINTENANCE ===")
            set_maintenance(True, maintenance_time_secs)
            
            stop_process(p_main, 'main.py')
            stop_process(p_info, 'info.py')
            
            print(f"[*] System is resting... Waiting for {MAINTENANCE_TIME_MINS} minutes.")
            time.sleep(maintenance_time_secs)

            print("\n[!] === ENDING MAINTENANCE ===")
            set_maintenance(False)
            
            p_info = start_process('info.py')
            time.sleep(2)
            p_main = start_process('main.py')
            
            print("[✓] SYSTEM RESTORED SUCCESSFULLY!")

    except KeyboardInterrupt:
        print("\n\n[!] Manager Bot stopped manually. Cleaning up processes...")
        stop_process(p_app, 'app.py')
        stop_process(p_info, 'info.py')
        stop_process(p_main, 'main.py')
        set_maintenance(False)
        print("[✓] All processes closed safely. Exiting.")

if __name__ == "__main__":
    main()

# END OF FILE manager_bot.py
