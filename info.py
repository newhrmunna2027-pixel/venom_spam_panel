# START OF FILE info.py

import os
import sys
import json
import asyncio
import socket
import traceback
import random
import string
import ssl
import time
import aiohttp
import certifi
import jwt
import uuid
import psutil
import urllib3
from io import BytesIO
from datetime import datetime

# central db coordinator import
import data_coordinator

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

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
    },
    {
        "os": "Android OS 10 / API-29",
        "cpu_short": "sm4250",
        "cpu_long": "Qualcomm Snapdragon 460 | 8 cores",
        "gpu": "Adreno (TM) 610",
        "opengl": "OpenGL ES 3.2 V@490.0",
        "width": 720,
        "height": 1600,
        "dpi": "270",
        "ram": 4096,
        "operator": "Teletalk"
    },
    {
        "os": "Android OS 12 / API-31",
        "cpu_short": "mt6785",
        "cpu_long": "MediaTek Helio G95 | 8 cores",
        "gpu": "Mali-G76 MC4",
        "opengl": "OpenGL ES 3.2 v1.r24p0",
        "width": 1080,
        "height": 2400,
        "dpi": "409",
        "ram": 8192,
        "operator": "Airtel"
    }
]

# ==========================================
# === SINGLETON LOCK (PORT MUTEX) ===
# ==========================================
def enforce_singleton_lock(port=59289):
    """Binds to a dedicated local port as a mutex to prevent duplicate running instances"""
    global _lock_socket
    _lock_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        _lock_socket.bind(('127.0.0.1', port))
    except socket.error:
        print("[FATAL] Another info.py instance is running. Terminating to avoid collision.")
        sys.exit(0)

# ==========================================
# === ZOMBIE PROCESS KILLER ===
# ==========================================
def Kill_Zombie_Processes():
    """Kills any old instances of info.py to prevent connection conflicts"""
    current_pid = os.getpid()
    for p in psutil.process_iter(['pid', 'cmdline']):
        try:
            cmd = p.info['cmdline']
            if cmd and 'info.py' in ' '.join(cmd) and 'python' in ' '.join(cmd).lower():
                if p.info['pid'] != current_pid:
                    print(f"[!] Killing Zombie info.py (PID: {p.info['pid']})")
                    p.kill()
        except: pass

Kill_Zombie_Processes()

try:
    from Crypto.Cipher import AES
    from Crypto.Util.Padding import pad, unpad
    from protobuf_decoder.protobuf_decoder import Parser
    from google.protobuf.timestamp_pb2 import Timestamp
    from google.protobuf.internal import builder as _builder
    from google.protobuf import descriptor_pool as _descriptor_pool
    from google.protobuf import symbol_database as _symbol_database
except ImportError as e:
    print(f"\n[FATAL ERROR] Missing Module: {e}")
    sys.exit()

_sym_db = _symbol_database.Default()
DESCRIPTOR_XKEYS = _descriptor_pool.Default().AddSerializedFile(b'\n\x10my_message.proto\">\n\tMyMessage\x12\x0f\n\x07\x66ield21\x18\x15 \x01(\x03\x12\x0f\n\x07\x66ield22\x18\x16 \x01(\x0c\x12\x0f\n\x07\x66ield23\x18\x17 \x01(\x0c\x62\x06proto3')
_xkeys_globals = {}
_builder.BuildMessageAndEnumDescriptors(DESCRIPTOR_XKEYS, _xkeys_globals)
_builder.BuildTopDescriptorsAndMessages(DESCRIPTOR_XKEYS, 'xKEys', _xkeys_globals)
MyMessage = _xkeys_globals['MyMessage']

BOT_FILE = 'bot.json' 
CHECK_TXT = 'check.txt'
INFO_JSON = 'info.json'
DATA_JSON = 'data.json'
VV_JSON = 'vv.json'
BAD_ACCS = 'bad_accounts.json'
UID_JSON = 'uid.json'

global_info_data = {}  
global_leader_history = {}  

# Dynamic Tracker bots
ACTIVE_INFO_BOTS = {}

Key = bytes([89, 103, 38, 116, 99, 37, 68, 69, 117, 104, 54, 37, 90, 99, 94, 56])
Iv = bytes([54, 111, 121, 90, 68, 114, 50, 50, 69, 51, 121, 99, 104, 106, 77, 37])

HTTP_SESSION = None

async def get_http_session():
    global HTTP_SESSION
    if HTTP_SESSION is None:
        connector = aiohttp.TCPConnector(ssl=False, limit=0, ttl_dns_cache=300, use_dns_cache=True)
        HTTP_SESSION = aiohttp.ClientSession(connector=connector)
    return HTTP_SESSION

def DecodE_HeX_sync(H):
    R = hex(H)
    F = str(R)[2:]
    if len(F) == 1: F = "0" + F
    return F

def EnC_PacKeT_sync(HeX, K, V):
    return AES.new(K, AES.MODE_CBC, V).encrypt(pad(bytes.fromhex(HeX), 16)).hex()

def EnC_AEs_sync(HeX):
    cipher = AES.new(Key, AES.MODE_CBC, Iv)
    return cipher.encrypt(pad(bytes.fromhex(HeX), AES.block_size)).hex()

def EnC_Vr_sync(N):
    if N < 0: return b''
    H =[]
    while True:
        BesTo = N & 0x7F; N >>= 7
        if N: BesTo |= 0x80
        H.append(BesTo)
        if not N: break
    return bytes(H)

def CrEaTe_VarianT_sync(f, v):
    return EnC_Vr_sync((f << 3) | 0) + EnC_Vr_sync(v)

def CrEaTe_LenGTh_sync(f, v):
    encoded = v.encode() if isinstance(v, str) else v
    return EnC_Vr_sync((f << 3) | 2) + EnC_Vr_sync(len(encoded)) + encoded

def CrEaTe_ProTo_sync(fields):
    packet = bytearray()
    for field, value in fields.items():
        if isinstance(value, dict):
            nested = CrEaTe_ProTo_sync(value)
            packet.extend(CrEaTe_LenGTh_sync(field, nested))
        elif isinstance(value, int):
            packet.extend(CrEaTe_VarianT_sync(field, value))
        elif isinstance(value, (str, bytes)):
            packet.extend(CrEaTe_LenGTh_sync(field, value))
    return packet

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
        "X-Unity-Version": "2018.4.11f1", "ReleaseVersion": "OB54", "Content-Type": "application/x-www-form-urlencoded", 
        "X-GA": "v1 1", 
        "Host": "loginbp.ggblueshark.com", "Connection": "Keep-Alive", "Accept-Encoding": "gzip"
    }
    try:
        async with session.post(url, data=PyL, headers=headers, timeout=15) as res:
            if res.status in[200, 201]:
                raw = await res.read()
                return raw.hex() 
    except: pass
    return None

def GeT_Key_Iv(serialized_data):
    my_message = MyMessage()
    my_message.ParseFromString(serialized_data)
    ts_obj = Timestamp()
    ts_obj.FromNanoseconds(my_message.field21)
    return ts_obj.seconds * 1_000_000_000 + ts_obj.nanos, my_message.field22, my_message.field23

async def GeT_LoGin_PorTs(JwT_ToKen, PayLoad, bot_uid, auth_url):
    session = await get_http_session()
    nickname = "Unknown"
    async def fetch_nick():
        try:
            api_url = f"https://munna2233.vercel.app/player-info?uid={bot_uid}"
            async with session.get(api_url, timeout=7) as api_res:
                if api_res.status == 200: return (await api_res.json()).get('basic_info', {}).get('nickname', 'Unknown')
        except: pass
        return "Unknown"

    async def fetch_login_data():
        url = f"{auth_url}/GetLoginData"
        headers = {"Authorization": f"Bearer {JwT_ToKen}", "ReleaseVersion": "OB54", "Content-Type": "application/x-www-form-urlencoded", "X-GA": "v1 1", "X-Unity-Version": "2018.4.11f1"}
        try:
            async with session.post(url, headers=headers, data=PayLoad, timeout=15) as res:
                if res.status == 200: return (await res.read()).hex()
        except: pass
        return None

    nick_task = asyncio.create_task(fetch_nick())
    data_task = asyncio.create_task(fetch_login_data())
    nickname, hex_data = await asyncio.gather(nick_task, data_task)
    
    if hex_data:
        try:
            dec_pkt = DeCode_PackEt(hex_data)
            if dec_pkt:
                data = json.loads(dec_pkt)
                if nickname == "Unknown": nickname = data.get("4", {}).get("data", "Unknown")
                if "32" in data and "14" in data:
                    a1, a2 = data["32"]["data"], data["14"]["data"]
                    return a1[:-6], a1[-5:], a2[:-6], a2[-5:], nickname
        except: pass
    return None, None, None, None, nickname

async def ToKen_GeneRaTe(U, P, dev):
    try:
        acc, open_id = await G_AccEss(U, P)
        if not acc: return None
        
        # DYNAMIC RANDOMIZATIONS
        selected_network = random.choice(["WIFI", "4G", "5G"])
        total_storage = random.randint(30000, 60000)
        avail_storage = random.randint(10000, 29000)
        total_internal = random.randint(2000, 4000)
        avail_internal = random.randint(500, 1500)
        avail_game_disk = random.randint(20000, 25000)
        total_game_disk = random.randint(25000, 28000)
        
        pyl = {
            3: str(datetime.now())[:-7], 4: "free fire", 5: 2, 7: "1.126.1", 
            8: dev["os"], 9: dev["cpu_short"], 10: dev["operator"], 
            11: selected_network, 12: dev["width"], 13: dev["height"], 14: dev["dpi"], 
            15: dev["cpu_long"], 16: dev["ram"], 17: dev["gpu"], 
            18: dev["opengl"], 
            19: f"Google|{uuid.uuid4()}", 
            20: f"{random.randint(1,254)}.{random.randint(1,254)}.{random.randint(1,254)}.{random.randint(1,254)}", 
            21: "en", 22: open_id, 
            23: "4", 24: "Handheld", 25: {6: 55, 8: random.randint(70, 99)}, 29: acc, 30: 2, 
            41: dev["operator"], 42: selected_network, 
            57: "7428b253defc164018c604a1ebbfebdf", 
            60: total_storage, 61: avail_storage, 62: total_internal, 63: avail_internal, 
            64: avail_game_disk, 65: total_game_disk, 66: avail_storage, 67: total_storage, 
            73: 3, 
            74: "/data/app/com.dts.freefireth-YPKM8jHEwAJlhpmhDhv5MQ==/lib/arm64", 76: 1, 
            77: "5b892aaabd688e571f688053118a162b|/data/app/com.dts.freefireth-YPKM8jHEwAJlhpmhDhv5MQ==/base.apk", 
            78: 3, 79: 2, 81: "64", 83: "2019120775", 86: "OpenGLES2", 87: 16383, 88: 4, 
            89: b"FwQVTgUPX1UaUllDDwcWCRBpWA0FUgsvA1snWlBaO1kFYg==", 
            92: random.randint(8000, 18000), 
            93: "android", 94: "KqsHTymw5/5GB23YGniUYN2/q47GATrq7eFeRatf0NkwLKEMQ0PK5BKEk72dPflAxUlEBir6Vtey83XqF593qsl8hwY=", 
            95: 110009, 97: 2, 98: 0, 99: "4", 100: "4"
        }
        payload_hex = CrEaTe_ProTo_sync(pyl).hex()
        final_payload = bytes.fromhex(EnC_AEs_sync(payload_hex))
        
        resp = await MajorLoGin(final_payload)
        
        if resp:
            dec_pkt = DeCode_PackEt(resp)
            if not dec_pkt: return None
            besto = json.loads(dec_pkt)
            uid = besto.get("1", {}).get("data")
            jwt_token = besto.get("8", {}).get("data")
            auth_url = besto.get("10", {}).get("data", "https://clientbp.ggblueshark.com")
            
            if not uid or not jwt_token: return None
            ts, key, iv = GeT_Key_Iv(bytes.fromhex(resp))
            ip, port, ip2, port2, nickname = await GeT_LoGin_PorTs(jwt_token, final_payload, uid, auth_url)
            
            if not ip2 or not port2: return None
            return (jwt_token, key, iv, ts, ip, port, ip2, port2, uid, nickname)
    except Exception: pass
    return None

class SimpleProtobufDecoder:
    @staticmethod
    def parse(hex_data):
        if isinstance(hex_data, str):
            try: data = bytes.fromhex(hex_data)
            except: return {}
        else: data = hex_data
        return SimpleProtobufDecoder._parse_bytes(data)

    @staticmethod
    def _parse_bytes(data):
        results = {}
        idx = 0
        length = len(data)
        while idx < length:
            try:
                tag, idx = SimpleProtobufDecoder._read_varint(data, idx)
                field_number = str(tag >> 3)
                wire_type = tag & 0x07
                if wire_type == 0:
                    value, idx = SimpleProtobufDecoder._read_varint(data, idx)
                    results[field_number] = {"data": value}
                elif wire_type == 2:
                    chunk_len, idx = SimpleProtobufDecoder._read_varint(data, idx)
                    if idx + chunk_len > length: break
                    chunk = data[idx : idx + chunk_len]
                    idx += chunk_len
                    try:
                        nested = SimpleProtobufDecoder._parse_bytes(chunk)
                        if nested: results[field_number] = {"data": nested}
                        else: results[field_number] = {"data": chunk.decode('utf-8', errors='ignore')}
                    except: results[field_number] = {"data": chunk.decode('utf-8', errors='ignore')}
                else: return results 
            except: break
        return results

    @staticmethod
    def _read_varint(data, idx):
        result = 0; shift = 0
        while True:
            if idx >= len(data): raise IndexError
            b = data[idx]; idx += 1
            result |= (b & 0x7F) << shift
            if not (b & 0x80): return result, idx
            shift += 7

async def parse_status_response(packet_bytes):
    try:
        start_index = -1
        for i in range(min(10, len(packet_bytes))):
            if packet_bytes[i] == 0x08:
                start_index = i
                break
        if start_index != -1: packet_body = packet_bytes[start_index:]
        else: packet_body = packet_bytes[5:]

        decoded = SimpleProtobufDecoder.parse(packet_body)
        core_data = decoded.get("5", {}).get("data", {}).get("1", {}).get("data", {})
        if not core_data: return None
        
        target_uid = str(core_data.get("1", {}).get("data", "Unknown"))
        status_code = core_data.get("3", {}).get("data", 0)
        
        status_map = {1: "SOLO", 2: "IN SQUAD", 3: "PLAYING", 4: "IN ROOM", 5: "PLAYING", 6: "SOCIAL ISLAND", 7: "SOCIAL ISLAND"}
        status_str = status_map.get(status_code, "OFFLINE")
        
        # Default initialization
        leader_uid = "N/A"
        squad_size = "N/A"
        room_id = "N/A"
        
        if status_code != 1 and status_str != "OFFLINE":
            leader_uid = str(core_data.get("8", {}).get("data", "N/A"))
            if "9" in core_data:
                curr = core_data["9"]["data"]
                if "10" in core_data:
                    maxx = core_data["10"]["data"] + 1
                    squad_size = f"{curr}/{maxx}"
                else: 
                    squad_size = f"{curr}"
        
        if status_code == 4: 
            room_id = str(core_data.get("4", {}).get("data", "N/A"))

        return {"uid": target_uid, "status": status_str, "leader": leader_uid, "squad_size": squad_size, "room_id": room_id}
    except: return None

def Encrypt_Varint(number):
    number = int(number)
    encoded_bytes =[]
    while True:
        byte = number & 0x7F
        number >>= 7
        if number: byte |= 0x80
        encoded_bytes.append(byte)
        if not number: break
    return bytes(encoded_bytes).hex()

def dec_to_hex(decimal):
    hex_str = hex(decimal)[2:]
    return hex_str.upper() if len(hex_str) % 2 == 0 else '0' + hex_str.upper()

async def encrypt_packet_manual(packet_hex, key, iv):
    cipher = AES.new(key, AES.MODE_CBC, iv)
    packet_bytes = bytes.fromhex(packet_hex)
    padded_packet = pad(packet_bytes, AES.block_size)
    return cipher.encrypt(padded_packet).hex()

async def create_status_check_packet(target_uid, key, iv):
    try:
        ida = Encrypt_Varint(target_uid)
        packet = f"080112090A05{ida}1005"
        encrypted_packet_hex = await encrypt_packet_manual(packet, key, iv)
        
        header_lenth = len(encrypted_packet_hex) // 2
        header_lenth_final = dec_to_hex(header_lenth)
        
        if len(header_lenth_final) == 2: final_packet = "0F15000000" + header_lenth_final + encrypted_packet_hex
        elif len(header_lenth_final) == 3: final_packet = "0F1500000" + header_lenth_final + encrypted_packet_hex
        elif len(header_lenth_final) == 4: final_packet = "0F150000" + header_lenth_final + encrypted_packet_hex
        else: final_packet = "0F15000" + header_lenth_final + encrypted_packet_hex
            
        return bytes.fromhex(final_packet)
    except: return None

def get_time(): return datetime.now().strftime('%Y-%m-%d %H:%M:%S')

def save_json(filepath, data):
    data_coordinator.save_data(filepath, data)

def load_json(filepath, default_type=dict):
    return data_coordinator.load_data(filepath, default_type())

def save_bad_account(uid, source, reason="Login Failed"):
    """Safe bad account saver with 5x retries to bypass Windows file locks"""
    bad_data = data_coordinator.load_data('bad_accounts.json', [])
    bad_data.append({
        "uid": str(uid),
        "source": source,
        "reason": reason,
        "time": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    })
    data_coordinator.save_data('bad_accounts.json', bad_data)

class StatusBot:
    def __init__(self, bot_id, login_uid, password):
        self.bot_id = str(bot_id)
        self.login_uid = str(login_uid)
        self.password = str(password)
        self.key = None
        self.iv = None
        self.online_ip_port = None
        self.account_uid = None  
        self.auth_token_hex = None
        self.reader = None
        self.writer = None
        self.connected = False
        self.is_running = True
        self.hb_task = None
        self.sc_task = None
        # Select device matching sequential bot counter rotation
        self.device = DEVICE_PROFILES[(int(bot_id) - 1) % len(DEVICE_PROFILES)]

    async def login_with_retry(self):
        for attempt in range(1, 4):
            print(f"[*] Info Tracker Bot (UID: {self.login_uid}) - Login Attempt {attempt}/3...")
            res = await ToKen_GeneRaTe(self.login_uid, self.password, self.device)
            if res:
                jwt_token, key, iv, ts, ip, port, ip2, port2, uid, nickname = res
                self.key = key; self.iv = iv; self.online_ip_port = f"{ip2}:{port2}"; self.account_uid = uid
                acc_id = jwt.decode(jwt_token, options={"verify_signature": False}).get("account_id")
                enc_acc = hex(acc_id)[2:]
                ts_hex = DecodE_HeX_sync(ts)
                token_enc = EnC_PacKeT_sync(jwt_token.encode().hex(), key, iv)
                zeros = "0000000" if len(enc_acc) == 9 else "00000000"
                self.auth_token_hex = f"0115{zeros}{enc_acc}{ts_hex}00000{hex(len(token_enc)//2)[2:]}{token_enc}"
                print(f"[+] Tracker Bot {self.login_uid} Logged In!")
                return True
            await asyncio.sleep(3)
        
        print(f"[-] Tracker Bot {self.login_uid} Banned/Failed. Moving to bad_accounts.")
        save_bad_account(self.login_uid, "bot.json", "Tracker Login Failed (3x)")
        self.is_running = False
        return False

    async def _create_socket_connection(self, ip, port):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
        if hasattr(socket, 'SIO_KEEPALIVE_VALS'): sock.ioctl(socket.SIO_KEEPALIVE_VALS, (1, 10000, 3000))
        sock.setblocking(False)
        await asyncio.get_running_loop().sock_connect(sock, (ip, port))
        reader, writer = await asyncio.open_connection(sock=sock)
        return reader, writer

    async def connect_and_listen(self):
        disconnect_count = 0
        while self.is_running:
            try:
                if not self.connected:
                    ip, port = self.online_ip_port.split(':')
                    self.reader, self.writer = await self._create_socket_connection(ip, int(port))
                    self.writer.write(bytes.fromhex(self.auth_token_hex))
                    await self.writer.drain()
                    self.connected = True
                    disconnect_count = 0 
                    if self.hb_task: self.hb_task.cancel()
                    if self.sc_task: self.sc_task.cancel()
                    self.hb_task = asyncio.create_task(self.heartbeat_loop())
                    self.sc_task = asyncio.create_task(self.status_check_loop())
                
                data = await self.reader.read(8192)
                if not data: 
                    raise ConnectionError("Connection closed by server")
                if data.hex().startswith('0f00'):
                    status_info = await parse_status_response(data)
                    if status_info:
                        target_uid = str(status_info['uid'])
                        if target_uid == self.account_uid: continue
                        status_str = status_info['status']
                        l_uid = status_info['leader']

                        if status_str == "OFFLINE":
                            l_uid = "N/A"
                            status_info['leader'] = "N/A"
                            status_info['squad_size'] = "N/A"
                            status_info['room_id'] = "N/A"
                        
                        global_info_data[target_uid] = {
                            "status": status_str, "leader": l_uid,
                            "squad": status_info['squad_size'], "room_id": status_info['room_id'],
                            "last_update": get_time()
                        }
                        
                        if status_str != "OFFLINE" and l_uid.isdigit() and len(l_uid) > 5:
                            if target_uid not in global_leader_history: global_leader_history[target_uid] = {}
                            global_leader_history[target_uid][l_uid] = get_time()
            except Exception:
                if self.writer:
                    try: self.writer.close()
                    except: pass
                self.writer = None
                self.connected = False
                disconnect_count += 1
                
                if disconnect_count >= 3:
                    print(f"[-] Tracker Bot {self.login_uid} Disconnected Permanently.")
                    save_bad_account(self.login_uid, "bot.json", "Tracker Disconnected (3x)")
                    self.is_running = False
                    break
                await asyncio.sleep(3)

    async def heartbeat_loop(self):
        while self.connected and self.is_running:
            try:
                pkt = await create_status_check_packet(self.account_uid, self.key, self.iv)
                if pkt: self.writer.write(pkt); await self.writer.drain()
            except: pass
            await asyncio.sleep(30)

    async def status_check_loop(self):
        while self.connected and self.is_running:
            try:
                check_data = load_json(CHECK_TXT, dict)
                my_targets = check_data.get(self.bot_id, [])
                tasks = []
                for t_uid in my_targets:
                    t_uid_str = str(t_uid).strip()
                    if not t_uid_str.isdigit(): continue
                    if t_uid_str not in global_info_data:
                        global_info_data[t_uid_str] = {"status": "OFFLINE", "leader": "N/A", "squad": "N/A", "room_id": "N/A", "last_update": get_time()}
                    pkt = await create_status_check_packet(t_uid_str, self.key, self.iv)
                    if pkt: tasks.append(self.send_packet(pkt))
                if tasks: await asyncio.gather(*tasks)
            except: pass
            await asyncio.sleep(3) 

    async def send_packet(self, packet):
        try: self.writer.write(packet); await self.writer.drain()
        except: self.connected = False

async def file_sync_manager():
    """Handles global data, status updates, and dynamic leader target TTLs"""
    while True:
        try:
            current_time = datetime.now()
            
            # Clean offline users
            for t_uid, info in list(global_info_data.items()):
                try:
                    last_update_obj = datetime.strptime(info["last_update"], '%Y-%m-%d %H:%M:%S')
                    if (current_time - last_update_obj).total_seconds() > 15:
                        if info["status"] != "OFFLINE":
                            global_info_data[t_uid]["status"] = "OFFLINE"
                            global_info_data[t_uid]["leader"] = "N/A"
                            global_info_data[t_uid]["squad"] = "N/A"
                            global_info_data[t_uid]["room_id"] = "N/A"
                except: pass

            check_data = load_json(CHECK_TXT, dict)
            all_valid_uids = []
            if isinstance(check_data, dict):
                for ulist in check_data.values():
                    if isinstance(ulist, list): all_valid_uids.extend([str(u).strip() for u in ulist if str(u).strip()])
            
            # Clean old tracked data
            keys_to_remove = [k for k in global_info_data.keys() if k not in all_valid_uids]
            for k in keys_to_remove: del global_info_data[k]
            save_json(INFO_JSON, global_info_data)
            
            # Save history
            formatted_data = {}
            for t_uid, leaders in global_leader_history.items():
                formatted_data[t_uid] = [f"{l}: {t}" for l, t in leaders.items()]
            save_json(DATA_JSON, formatted_data)

        except: pass
        await asyncio.sleep(3)

async def dynamic_bot_watcher():
    """Watches bot.json, dynamically updates ACTIVE_INFO_BOTS without restarting."""
    last_state = ""
    
    while True:
        try:
            bot_array = load_json(BOT_FILE, list)
            if not isinstance(bot_array, list): bot_array = []
            
            curr_state = json.dumps(bot_array, sort_keys=True)
            if curr_state != last_state:
                print("\n[SYSTEM] bot.json updated. Syncing Tracker Bots...")
                
                current_uids = [str(b['uid']) for b in bot_array if 'uid' in b]
                
                # Check for removed bots
                for active_uid in list(ACTIVE_INFO_BOTS.keys()):
                    if active_uid not in current_uids:
                        print(f"[-] Stopping Tracker Bot: {active_uid}")
                        bot_obj = ACTIVE_INFO_BOTS.pop(active_uid)
                        bot_obj.is_running = False
                        if bot_obj.writer: bot_obj.writer.close()

                # Check for new bots and update indices
                for index, b in enumerate(bot_array):
                    uid = str(b.get('uid'))
                    pwd = str(b.get('password'))
                    list_id = str(index + 1)

                    if uid in ACTIVE_INFO_BOTS:
                        ACTIVE_INFO_BOTS[uid].bot_id = list_id
                    else:
                        print(f"[+] Starting New Tracker Bot: {uid}")
                        new_bot = StatusBot(list_id, uid, pwd)
                        ACTIVE_INFO_BOTS[uid] = new_bot
                        
                        async def boot_bot(bot):
                            success = await bot.login_with_retry()
                            if success: asyncio.create_task(bot.connect_and_listen())
                                
                        asyncio.create_task(boot_bot(new_bot))
                        await asyncio.sleep(0.5)
                        
                last_state = curr_state
        except Exception: pass
        await asyncio.sleep(5)

async def main():
    print("==================================")
    print("  DYNAMIC STATUS TRACKER LIVE     ")
    print("==================================")

    await get_http_session()
        
    asyncio.create_task(file_sync_manager())
    asyncio.create_task(dynamic_bot_watcher())
    
    while True:
        await asyncio.sleep(3600)

if __name__ == "__main__":
    enforce_singleton_lock(59289)
    try:
        if sys.platform == 'win32': asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        asyncio.run(main())
    except KeyboardInterrupt: 
        print("\n[STOP] Tracker Stopped by Admin.")

# END OF FILE info.py