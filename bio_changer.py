# -*- coding: utf-8 -*-
# START OF FILE bio_changer.py

import asyncio
import aiohttp
import ssl
import certifi
import json
import time
import random
import os
import uuid
import sys
from datetime import datetime
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad

# ==================== INLINE PROTOBUF DEFINITIONS ====================
from google.protobuf import descriptor_pool as _descriptor_pool
from google.protobuf import symbol_database as _symbol_database
from google.protobuf.internal import builder as _builder

_sym_db = _symbol_database.Default()
_globals = globals()

# 1. Data Proto (For Bio Changer)
DESC_DATA = _descriptor_pool.Default().AddSerializedFile(
    b'\n\ndata.proto\"\xbb\x01\n\x04\x44\x61ta\x12\x0f\n\x07\x66ield_2\x18\x02 \x01(\x05\x12\x1e\n\x07\x66ield_5\x18\x05 \x01(\x0b\x32\r.EmptyMessage\x12\x1e\n\x07\x66ield_6\x18\x06 \x01(\x0b\x32\r.EmptyMessage\x12\x0f\n\x07\x66ield_8\x18\x08 \x01(\t\x12\x0f\n\x07\x66ield_9\x18\t \x01(\x05\x12\x1f\n\x08\x66ield_11\x18\x0b \x01(\x0b\x32\r.EmptyMessage\x12\x1f\n\x08\x66ield_12\x18\x0c \x01(\x0b\x32\r.EmptyMessage\"\x0e\n\x0c\x45mptyMessageb\x06proto3'
)
_builder.BuildMessageAndEnumDescriptors(DESC_DATA, _globals)
_builder.BuildTopDescriptorsAndMessages(DESC_DATA, 'data_pb2', _globals)

# 2. MajorLoginReq Proto
DESC_MAJOR_LOGIN_REQ = _descriptor_pool.Default().AddSerializedFile(
    b'\n\x13MajorLoginReq.proto\"\xfa\n\n\nMajorLogin\x12\x12\n\nevent_time\x18\x03 \x01(\t\x12\x11\n\tgame_name\x18\x04 \x01(\t\x12\x13\n\x0bplatform_id\x18\x05 \x01(\x05\x12\x16\n\x0e\x63lient_version\x18\x07 \x01(\t\x12\x17\n\x0fsystem_software\x18\x08 \x01(\t\x12\x17\n\x0fsystem_hardware\x18\t \x01(\t\x12\x18\n\x10telecom_operator\x18\n \x01(\t\x12\x14\n\x0cnetwork_type\x18\x0b \x01(\t\x12\x14\n\x0cscreen_width\x18\x0c \x01(\r\x12\x15\n\rscreen_height\x18\r \x01(\r\x12\x12\n\nscreen_dpi\x18\x0e \x01(\t\x12\x19\n\x11processor_details\x18\x0f \x01(\t\x12\x0e\n\x06memory\x18\x10 \x01(\r\x12\x14\n\x0cgpu_renderer\x18\x11 \x01(\t\x12\x13\n\x0bgpu_version\x18\x12 \x01(\t\x12\x18\n\x10unique_device_id\x18\x13 \x01(\t\x12\x11\n\tclient_ip\x18\x14 \x01(\t\x12\x10\n\x08language\x18\x15 \x01(\t\x12\x0f\n\x07open_id\x18\x16 \x01(\t\x12\x14\n\x0copen_id_type\x18\x17 \x01(\t\x12\x13\n\x0b\x64\x65vice_type\x18\x18 \x01(\t\x12\'\n\x10memory_available\x18\x19 \x01(\x0b\x32\r.GameSecurity\x12\x14\n\x0c\x61\x63\x63\x65ss_token\x18\x1d \x01(\t\x12\x17\n\x0fplatform_sdk_id\x18\x1e \x01(\x05\x12\x1a\n\x12network_operator_a\x18) \x01(\t\x12\x16\n\x0enetwork_type_a\x18* \x01(\t\x12\x1c\n\x14\x63lient_using_version\x18\x39 \x01(\t\x12\x1e\n\x16\x65xternal_storage_total\x18< \x01(\x05\x12\"\n\x1a\x65xternal_storage_available\x18= \x01(\x05\x12\x1e\n\x16internal_storage_total\x18> \x01(\x05\x12\"\n\x1ainternal_storage_available\x18? \x01(\x05\x12#\n\x1bgame_disk_storage_available\x18@ \x01(\x05\x12\x1f\n\x17game_disk_storage_total\x18\x41 \x01(\x05\x12%\n\x1d\x65xternal_sdcard_avail_storage\x18\x42 \x01(\x05\x12%\n\x1d\x65xternal_sdcard_total_storage\x18\x43 \x01(\x05\x12\x10\n\x08login_by\x18I \x01(\x05\x12\x14\n\x0clibrary_path\x18J \x01(\t\x12\x12\n\nreg_avatar\x18L \x01(\x05\x12\x15\n\rlibrary_token\x18M \x01(\t\x12\x14\n\x0c\x63hannel_type\x18N \x01(\x05\x12\x10\n\x08\x63pu_type\x18O \x01(\x05\x12\x18\n\x10\x63pu_architecture\x18Q \x01(\t\x12\x1b\n\x13\x63lient_version_code\x18S \x01(\t\x12\x14\n\x0cgraphics_api\x18V \x01(\t\x12\x1d\n\x15supported_astc_bitset\x18W \x01(\r\x12\x1a\n\x12login_open_id_type\x18X \x01(\x05\x12\x18\n\x10\x61nalytics_detail\x18Y \x01(\x0c\x12\x14\n\x0cloading_time\x18\\ \x01(\r\x12\x17\n\x0frelease_channel\x18] \x01(\t\x12\x12\n\nextra_info\x18^ \x01(\t\x12 \n\x18\x61ndroid_engine_init_flag\x18_ \x01(\r\x12\x0f\n\x07if_push\x18\x61 \x01(\x05\x12\x0e\n\x06is_vpn\x18\x62 \x01(\x05\x12\x1c\n\x14origin_platform_type\x18\x63 \x01(\t\x12\x1d\n\x15primary_platform_type\x18\x64 \x01(\t\"5\n\x0cGameSecurity\x12\x0f\n\x07version\x18\x06 \x01(\x05\x12\x14\n\x0chidden_value\x18\x08 \x01(\x04\x62\x06proto3'
)
_builder.BuildMessageAndEnumDescriptors(DESC_MAJOR_LOGIN_REQ, _globals)
_builder.BuildTopDescriptorsAndMessages(DESC_MAJOR_LOGIN_REQ, 'MajorLoginReq_pb2', _globals)

# 3. MajorLoginRes Proto
DESC_MAJOR_LOGIN_RES = _descriptor_pool.Default().AddSerializedFile(
    b'\n\x13MajorLoginRes.proto\"|\n\rMajorLoginRes\x12\x13\n\x0b\x61\x63\x63ount_uid\x18\x01 \x01(\x04\x12\x0e\n\x06region\x18\x02 \x01(\t\x12\r\n\x05token\x18\x08 \x01(\t\x12\x0b\n\x03url\x18\n \x01(\t\x12\x11\n\ttimestamp\x18\x15 \x01(\x03\x12\x0b\n\x03key\x18\x16 \x01(\x0c\x12\n\n\x02iv\x18\x17 \x01(\x0c\x62\x06proto3'
)
_builder.BuildMessageAndEnumDescriptors(DESC_MAJOR_LOGIN_RES, _globals)
_builder.BuildTopDescriptorsAndMessages(DESC_MAJOR_LOGIN_RES, 'MajorLoginRes_pb2', _globals)

# 4. Duo Checker Proto (Beta.proto)
DESC_DUO = _descriptor_pool.Default().AddSerializedFile(
    b'\n\nBeta.proto\"u\n\x0e\x44ynamicDuoData\x12\x13\n\x0bpartner_uid\x18\x01 \x01(\x03\x12\r\n\x05score\x18\x03 \x01(\x05\x12\x1a\n\x12\x63reation_timestamp\x18\x04 \x01(\x03\x12\x13\n\x0b\x64\x61ys_active\x18\x05 \x01(\x05\x12\x0e\n\x06status\x18\x06 \x01(\x05\":\n\x15SpecialFriendResponse\x12!\n\x08\x64uo_info\x18\x01 \x01(\x0b\x32\x0f.DynamicDuoDatab\x06proto3'
)
_builder.BuildMessageAndEnumDescriptors(DESC_DUO, _globals)
_builder.BuildTopDescriptorsAndMessages(DESC_DUO, 'Beta_pb2', _globals)


# Extract Protobuf Classes
Data = _globals['Data']
EmptyMessage = _globals['EmptyMessage']
MajorLogin = _globals['MajorLogin']
MajorLoginRes = _globals['MajorLoginRes']
SpecialFriendResponse = _globals['SpecialFriendResponse']

# Cryptographic Keys (Default Free Fire Keys)
KEY = bytes([89, 103, 38, 116, 99, 37, 68, 69, 117, 104, 54, 37, 90, 99, 94, 56])
IV = bytes([54, 111, 121, 90, 68, 114, 50, 50, 69, 51, 121, 99, 104, 106, 77, 37])

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

ssl_context = ssl.create_default_context(cafile=certifi.where())
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE

def YOuR_FaThER(uid):
    n = int(uid)
    res = bytearray()
    while n >= 0x80:
        res.append((n & 0x7f) | 0x80)
        n >>= 7
    res.append(n)
    
    payload_bytes = b"\x08" + bytes(res)
    cipher = AES.new(KEY, AES.MODE_CBC, IV)
    return cipher.encrypt(pad(payload_bytes, 16))

def UNknown(d):
    try:
        return unpad(AES.new(KEY, AES.MODE_CBC, IV).decrypt(d), 16)
    except:
        return d

class PacketBuilder:
    @staticmethod
    async def create_major_login_payload(open_id, access_token, dev):
        major_login = MajorLogin()
        
        # 🟢 CONSTANTS
        major_login.event_time = str(datetime.now())[:-7]
        major_login.game_name = "free fire"
        major_login.platform_id = 2
        major_login.client_version = "1.126.1"
        major_login.client_using_version = "7428b253defc164018c604a1ebbfebdf"
        major_login.client_version_code = "2019120775"
        major_login.release_channel = "android"
        
        # 🟢 DEVICE DETAILS
        major_login.system_software = dev["os"]
        major_login.system_hardware = dev["cpu_short"]
        major_login.telecom_operator = dev["operator"]
        
        selected_network = random.choice(["WIFI", "4G", "5G"])
        major_login.network_type = selected_network
        major_login.network_type_a = selected_network
        major_login.network_operator_a = dev["operator"]
        
        major_login.screen_width = dev["width"]
        major_login.screen_height = dev["height"]
        major_login.screen_dpi = dev["dpi"]
        major_login.processor_details = dev["cpu_long"]
        major_login.memory = dev["ram"]
        major_login.gpu_renderer = dev["gpu"]
        major_login.gpu_version = dev["opengl"]
        
        # 🟢 UNIQUE DEVICE ID & IP
        major_login.unique_device_id = f"Google|{uuid.uuid4()}"
        major_login.client_ip = f"{random.randint(1,254)}.{random.randint(1,254)}.{random.randint(1,254)}.{random.randint(1,254)}"
        
        # 🟢 AUTHENTICATION
        major_login.language = "en"
        major_login.open_id = open_id
        major_login.open_id_type = "4"
        major_login.login_open_id_type = 4
        major_login.device_type = "Handheld"
        major_login.access_token = access_token
        major_login.platform_sdk_id = 2
        
        # 🟢 RANDOMIZED STORAGE CALCULATIONS
        total_storage = random.randint(30000, 60000)
        avail_storage = random.randint(10000, 29000)
        total_internal = random.randint(2000, 4000)
        avail_internal = random.randint(500, 1500)
        avail_game_disk = random.randint(20000, 25000)
        total_game_disk = random.randint(25000, 28000)
        
        major_login.external_storage_total = total_storage
        major_login.external_storage_available = avail_storage
        major_login.internal_storage_total = total_internal
        major_login.internal_storage_available = avail_internal
        major_login.game_disk_storage_available = avail_game_disk
        major_login.game_disk_storage_total = total_game_disk
        major_login.external_sdcard_avail_storage = avail_storage
        major_login.external_sdcard_total_storage = total_storage
        
        # 🟢 PROTOCOL SETTINGS
        major_login.login_by = 3
        major_login.library_path = "/data/app/com.dts.freefireth-YPKM8jHEwAJlhpmhDhv5MQ==/lib/arm64"
        major_login.reg_avatar = 1
        major_login.library_token = "5b892aaabd688e571f688053118a162b|/data/app/com.dts.freefireth-YPKM8jHEwAJlhpmhDhv5MQ==/base.apk"
        major_login.channel_type = 3
        major_login.cpu_type = 2
        major_login.cpu_architecture = "64"
        major_login.graphics_api = "OpenGLES2"
        major_login.supported_astc_bitset = 16383
        major_login.analytics_detail = b"FwQVTgUPX1UaUllDDwcWCRBpWA0FUgsvA1snWlBaO1kFYg=="
        
        # 🟢 RANDOMIZED LOADING & HIDDEN VALUE
        major_login.loading_time = random.randint(8000, 18000)
        major_login.android_engine_init_flag = 110009
        major_login.if_push = 2
        major_login.is_vpn = 0
        major_login.origin_platform_type = "4"
        major_login.primary_platform_type = "4"
        major_login.memory_available.version = 55
        major_login.memory_available.hidden_value = random.randint(70, 99)
        
        return major_login

class AuthHandler:
    @staticmethod
    async def get_guest_token(bot_uid, bot_pass):
        url = "https://100067.connect.garena.com/oauth/guest/token/grant"
        headers = {
            "Host": "100067.connect.garena.com", 
            "Content-Type": "application/x-www-form-urlencoded", 
            "Accept-Encoding": "gzip", 
            "Connection": "keep-alive"
        }
        data = {
            "uid": bot_uid, "password": bot_pass, "response_type": "token",
            "client_type": "2", "client_id": "100067",
            "client_secret": "2ee44819e9b4598845141067b281621874d0d5d7af9d8f7e00c1e54715b7d1e3"
        }
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, data=data, ssl=ssl_context) as response:
                    if response.status != 200: return None, None
                    j = await response.json()
                    return j.get("open_id"), j.get("access_token")
        except Exception:
            return None, None

    @staticmethod
    async def major_login(payload):
        url = "https://loginbp.ggpolarbear.com/MajorLogin"
        headers = {
            'Connection': "Keep-Alive",
            'Accept-Encoding': "gzip",
            'Content-Type': "application/x-www-form-urlencoded",
            'X-Unity-Version': "2018.4.11f1",
            'X-GA': "v1 1",
            'ReleaseVersion': "OB54"
        }
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, data=payload, headers=headers, ssl=ssl_context) as response:
                    if response.status == 200:
                        data = await response.read()
                        proto = MajorLoginRes()
                        proto.ParseFromString(data)
                        return proto
                    return None
        except Exception:
            return None

class MultiToolApp:
    @staticmethod
    def create_long_bio_proto(bio_text):
        field_2 = b'\x10\x11'
        field_5 = b'\x2A\x00'
        field_6 = b'\x32\x00'
        
        bio_bytes = bio_text.encode('utf-8')
        bio_len = len(bio_bytes)
        
        def encode_varint(value):
            encoded = []
            while value > 127:
                encoded.append((value & 0x7F) | 0x80)
                value >>= 7
            encoded.append(value)
            return bytes(encoded)
        
        field_8 = b'\x42' + encode_varint(bio_len) + bio_bytes
        field_9 = b'\x48\x01'
        field_11 = b'\x5A\x00'
        field_12 = b'\x62\x00'
        
        return field_2 + field_5 + field_6 + field_8 + field_9 + field_11 + field_12

    @staticmethod
    async def update_bio(jwt_token, bio_text, regional_base_url):
        try:
            url = f"{regional_base_url}/UpdateSocialBasicInfo"
            proto_data = MultiToolApp.create_long_bio_proto(bio_text)
            
            cipher = AES.new(KEY, AES.MODE_CBC, IV)
            padded_data = pad(proto_data, 16)
            encrypted_data = cipher.encrypt(padded_data)
            
            headers = {
                "Expect": "100-continue",
                "Authorization": f"Bearer {jwt_token}",
                "X-Unity-Version": "2018.4.11f1",
                "X-GA": "v1 1",
                "ReleaseVersion": "OB54",
                "Content-Type": "application/x-www-form-urlencoded",
                "Connection": "Keep-Alive",
                "Accept-Encoding": "gzip"
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, data=encrypted_data, ssl=ssl_context) as response:
                    if response.status == 200: return True, "Signature updated successfully!"
                    else: return False, f"HTTP {response.status}"
        except Exception as e:
            return False, str(e)

    @staticmethod
    async def check_duo(jwt_token, target_uid, regional_base_url):
        try:
            url = f"{regional_base_url}/GetSpecialFriendList"
            headers = {
                "Authorization": f"Bearer {jwt_token}",
                "Content-Type": "application/x-www-form-urlencoded",
                "X-Unity-Version": "2018.4.11f1",
                "X-GA": "v1 1",
                "ReleaseVersion": "OB54",
                "Connection": "Keep-Alive"
            }
            payload = YOuR_FaThER(target_uid)
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, data=payload, ssl=ssl_context) as response:
                    if response.status == 200:
                        data = await response.read()
                        dec_data = UNknown(data)
                        
                        resp_proto = SpecialFriendResponse()
                        resp_proto.ParseFromString(dec_data)
                        
                        if not resp_proto.HasField("duo_info"):
                            return False, "No Dynamic Duo info found for this player."
                            
                        duo = resp_proto.duo_info
                        score = duo.score
                        if score < 101: lvl = 1
                        elif score < 301: lvl = 2
                        elif score < 501: lvl = 3
                        elif score < 801: lvl = 4
                        elif score < 1201: lvl = 5
                        else: lvl = 6
                        
                        status = "Active" if duo.status == 2 else "Inactive"
                        creation_time = time.strftime('%B %d, %Y', time.localtime(duo.creation_timestamp))
                        
                        info = {
                            "Partner UID": str(duo.partner_uid),
                            "Level": lvl,
                            "Score": score,
                            "Active Days": duo.days_active,
                            "Formed On": creation_time,
                            "Status": status
                        }
                        return True, info
                    elif response.status == 500:
                        return False, "Private Profile or Invalid UID."
                    else:
                        return False, f"HTTP Error {response.status}"
        except Exception as e:
            return False, str(e)

async def _login_and_get_session(bot_uid, bot_pass):
    device = random.choice(DEVICE_PROFILES)
    oid, acc_token = await AuthHandler.get_guest_token(bot_uid, bot_pass)
    if not oid or not acc_token: return None, "Failed Garena Authentication"
    
    major_login_inst = await PacketBuilder.create_major_login_payload(oid, acc_token, device)
    
    cipher = AES.new(KEY, AES.MODE_CBC, IV)
    encrypted_payload = cipher.encrypt(pad(major_login_inst.SerializeToString(), AES.block_size))
    
    auth_info = await AuthHandler.major_login(encrypted_payload)
    if not auth_info: return None, "Game Server Handshake Failed."
    
    return auth_info, "Success"

async def check_player_duo(bot_uid, bot_pass, target_uid):
    """API Gateway for Web Dynamic Duo Check"""
    auth_info, err = await _login_and_get_session(bot_uid, bot_pass)
    if not auth_info:
        return False, err
    success, data = await MultiToolApp.check_duo(auth_info.token, target_uid, auth_info.url)
    return success, data

async def change_bot_bio(bot_uid, bot_pass, bio_text):
    """API Gateway for Web Signature Update"""
    auth_info, err = await _login_and_get_session(bot_uid, bot_pass)
    if not auth_info:
        return False, err
    success, msg = await MultiToolApp.update_bio(auth_info.token, bio_text, auth_info.url)
    return success, msg

# END OF FILE bio_changer.py