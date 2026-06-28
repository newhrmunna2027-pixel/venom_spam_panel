# -*- coding: utf-8 -*-
# START OF FILE manager.py

import asyncio
import time
import httpx
import json
import threading
import base64
import os
import urllib.parse
from typing import Tuple, Dict, Any, List
from Crypto.Cipher import AES
from collections import defaultdict

# DB Coordinator import for dual system compatibility
import data_coordinator

# === Protobuf Imports & Setup ===
from google.protobuf import json_format, message
from google.protobuf.message import Message
from google.protobuf import descriptor as _descriptor
from google.protobuf import descriptor_pool as _descriptor_pool
from google.protobuf import symbol_database as _symbol_database
from google.protobuf.internal import builder as _builder

_sym_db = _symbol_database.Default()


DESCRIPTOR_1 = _descriptor_pool.Default().AddSerializedFile(b'\n\x19\x41\x63\x63ountPersonalShow.proto\x12\x08\x66reefire\"\xbc\x01\n\x0e\x41\x63\x63ountPrefers\x12\x15\n\rhide_my_lobby\x18\x01 \x01(\x08\x12\x1c\n\x14pregame_show_choices\x18\x02 \x03(\r\x12\x1f\n\x17\x62r_pregame_show_choices\x18\x03 \x03(\r\x12\x1a\n\x12hide_personal_info\x18\x04 \x01(\x08\x12\x1f\n\x17\x64isable_friend_spectate\x18\x05 \x01(\x08\x12\x17\n\x0fhide_occupation\x18\x06 \x01(\x08\"\x8a\x01\n\x10\x45xternalIconInfo\x12\x15\n\rexternal_icon\x18\x01 \x01(\t\x12,\n\x06status\x18\x02 \x01(\x0e\x32\x1c.freefire.ExternalIconStatus\x12\x31\n\tshow_type\x18\x03 \x01(\x0e\x32\x1e.freefire.ExternalIconShowType\"\\\n\x0fSocialHighLight\x12\'\n\nhigh_light\x18\x01 \x01(\x0e\x32\x13.freefire.HighLight\x12\x11\n\texpire_at\x18\x02 \x01(\x03\x12\r\n\x05value\x18\x03 \x01(\r\"\xfc\x01\n\x14WeaponPowerTitleInfo\x12\x0e\n\x06region\x18\x01 \x01(\t\x12\x14\n\x0ctitle_cfg_id\x18\x02 \x01(\r\x12\x16\n\x0eleaderboard_id\x18\x03 \x01(\x04\x12\x11\n\tweapon_id\x18\x04 \x01(\r\x12\x0c\n\x04rank\x18\x05 \x01(\r\x12\x13\n\x0b\x65xpire_time\x18\x06 \x01(\x03\x12\x13\n\x0breward_time\x18\x07 \x01(\x03\x12\x12\n\nRegionName\x18\x08 \x01(\t\x12\x39\n\nRegionType\x18\t \x01(\x0e\x32%.freefire.ELeaderBoardTitleRegionType\x12\x0c\n\x04IsBr\x18\n \x01(\x08\"\xad\x01\n\x11GuildWarTitleInfo\x12\x0e\n\x06region\x18\x01 \x01(\t\x12\x0f\n\x07\x63lan_id\x18\x02 \x01(\x04\x12\x14\n\x0ctitle_cfg_id\x18\x03 \x01(\r\x12\x16\n\x0eleaderboard_id\x18\x04 \x01(\x04\x12\x0c\n\x04rank\x18\x05 \x01(\r\x12\x13\n\x0b\x65xpire_time\x18\x06 \x01(\x03\x12\x13\n\x0breward_time\x18\x07 \x01(\x03\x12\x11\n\tclan_name\x18\x08 \x01(\t\"\x92\x01\n\x14LeaderboardTitleInfo\x12?\n\x17weapon_power_title_info\x18\x01 \x03(\x0b\x32\x1e.freefire.WeaponPowerTitleInfo\x12\x39\n\x14guild_war_title_info\x18\x02 \x03(\x0b\x32\x1b.freefire.GuildWarTitleInfo\"\xfb\x03\n\x0fSocialBasicInfo\x12\x12\n\naccount_id\x18\x01 \x01(\x04\x12 \n\x06gender\x18\x02 \x01(\x0e\x32\x10.freefire.Gender\x12$\n\x08language\x18\x03 \x01(\x0e\x32\x12.freefire.Language\x12)\n\x0btime_online\x18\x04 \x01(\x0e\x32\x14.freefire.TimeOnline\x12)\n\x0btime_active\x18\x05 \x01(\x0e\x32\x14.freefire.TimeActive\x12/\n\nbattle_tag\x18\x06 \x03(\x0e\x32\x1b.freefire.PlayerBattleTagID\x12\'\n\nsocial_tag\x18\x07 \x03(\x0e\x32\x13.freefire.SocialTag\x12)\n\x0bmode_prefer\x18\x08 \x01(\x0e\x32\x14.freefire.ModePrefer\x12\x11\n\tsignature\x18\t \x01(\t\x12%\n\trank_show\x18\n \x01(\x0e\x32\x12.freefire.RankShow\x12\x18\n\x10\x62\x61ttle_tag_count\x18\x0b \x03(\r\x12!\n\x19signature_ban_expire_time\x18\x0c \x01(\x03\x12:\n\x12leaderboard_titles\x18\r \x01(\x0b\x32\x1e.freefire.LeaderboardTitleInfo\"\x92\x01\n#SocialHighLightsWithSocialBasicInfo\x12\x35\n\x12social_high_lights\x18\x01 \x03(\x0b\x32\x19.freefire.SocialHighLight\x12\x34\n\x11social_basic_info\x18\x02 \x01(\x0b\x32\x19.freefire.SocialBasicInfo\"c\n\x0eOccupationInfo\x12\x15\n\roccupation_id\x18\x01 \x01(\r\x12\x0e\n\x06scores\x18\x02 \x01(\x04\x12\x13\n\x0bproficients\x18\x03 \x01(\x04\x12\x15\n\rproficient_lv\x18\x04 \x01(\r\"d\n\x14OccupationSeasonInfo\x12\x11\n\tseason_id\x18\x01 \x01(\r\x12\x11\n\tgame_mode\x18\x02 \x01(\r\x12&\n\x04info\x18\x03 \x01(\x0b\x32\x18.freefire.OccupationInfo\"\xcb\x0c\n\x10\x41\x63\x63ountInfoBasic\x12\x12\n\naccount_id\x18\x01 \x01(\x04\x12\x14\n\x0c\x61\x63\x63ount_type\x18\x02 \x01(\r\x12\x10\n\x08nickname\x18\x03 \x01(\t\x12\x13\n\x0b\x65xternal_id\x18\x04 \x01(\t\x12\x0e\n\x06region\x18\x05 \x01(\t\x12\r\n\x05level\x18\x06 \x01(\r\x12\x0b\n\x03\x65xp\x18\x07 \x01(\r\x12\x15\n\rexternal_type\x18\x08 \x01(\r\x12\x15\n\rexternal_name\x18\t \x01(\t\x12\x15\n\rexternal_icon\x18\n \x01(\t\x12\x11\n\tbanner_id\x18\x0b \x01(\r\x12\x10\n\x08head_pic\x18\x0c \x01(\r\x12\x11\n\tclan_name\x18\r \x01(\t\x12\x0c\n\x04rank\x18\x0e \x01(\r\x12\x16\n\x0eranking_points\x18\x0f \x01(\r\x12\x0c\n\x04role\x18\x10 \x01(\r\x12\x16\n\x0ehas_elite_pass\x18\x11 \x01(\x08\x12\x11\n\tbadge_cnt\x18\x12 \x01(\r\x12\x10\n\x08\x62\x61\x64ge_id\x18\x13 \x01(\r\x12\x11\n\tseason_id\x18\x14 \x01(\r\x12\r\n\x05liked\x18\x15 \x01(\r\x12\x12\n\nis_deleted\x18\x16 \x01(\x08\x12\x11\n\tshow_rank\x18\x17 \x01(\x08\x12\x15\n\rlast_login_at\x18\x18 \x01(\x03\x12\x14\n\x0c\x65xternal_uid\x18\x19 \x01(\x04\x12\x11\n\treturn_at\x18\x1a \x01(\x03\x12\x1e\n\x16\x63hampionship_team_name\x18\x1b \x01(\t\x12$\n\x1c\x63hampionship_team_member_num\x18\x1c \x01(\r\x12\x1c\n\x14\x63hampionship_team_id\x18\x1d \x01(\x04\x12\x0f\n\x07\x63s_rank\x18\x1e \x01(\r\x12\x19\n\x11\x63s_ranking_points\x18\x1f \x01(\r\x12\x19\n\x11weapon_skin_shows\x18  \x03(\r\x12\x0e\n\x06pin_id\x18! \x01(\r\x12\x19\n\x11is_cs_ranking_ban\x18\" \x01(\x08\x12\x10\n\x08max_rank\x18# \x01(\r\x12\x13\n\x0b\x63s_max_rank\x18$ \x01(\r\x12\x1a\n\x12max_ranking_points\x18% \x01(\r\x12\x15\n\rgame_bag_show\x18& \x01(\r\x12\x15\n\rpeak_rank_pos\x18\' \x01(\r\x12\x18\n\x10\x63s_peak_rank_pos\x18( \x01(\r\x12\x31\n\x0f\x61\x63\x63ount_prefers\x18) \x01(\x0b\x32\x18.freefire.AccountPrefers\x12\x1f\n\x17periodic_ranking_points\x18* \x01(\r\x12\x15\n\rperiodic_rank\x18+ \x01(\r\x12\x11\n\tcreate_at\x18, \x01(\x03\x12:\n\x16veteran_leave_days_tag\x18- \x01(\x0e\x32\x1a.freefire.VeteranLeaveDays\x12\x1b\n\x13selected_item_slots\x18. \x03(\r\x12\x38\n\x10pre_veteran_type\x18/ \x01(\x0e\x32\x1e.freefire.PreVeteranActionType\x12\r\n\x05title\x18\x30 \x01(\r\x12\x36\n\x12\x65xternal_icon_info\x18\x31 \x01(\x0b\x32\x1a.freefire.ExternalIconInfo\x12\x17\n\x0frelease_version\x18\x32 \x01(\t\x12\x1b\n\x13veteran_expire_time\x18\x33 \x01(\x04\x12\x14\n\x0cshow_br_rank\x18\x34 \x01(\x08\x12\x14\n\x0cshow_cs_rank\x18\x35 \x01(\x08\x12\x0f\n\x07\x63lan_id\x18\x36 \x01(\x04\x12\x15\n\rclan_badge_id\x18\x37 \x01(\r\x12\x19\n\x11\x63ustom_clan_badge\x18\x38 \x01(\t\x12\x1d\n\x15use_custom_clan_badge\x18\x39 \x01(\x08\x12\x15\n\rclan_frame_id\x18: \x01(\r\x12\x18\n\x10membership_state\x18; \x01(\x08\x12:\n\x12select_occupations\x18< \x03(\x0b\x32\x1e.freefire.OccupationSeasonInfo\x12Y\n\"social_high_lights_with_basic_info\x18= \x01(\x0b\x32-.freefire.SocialHighLightsWithSocialBasicInfo\"\x9a\x01\n\x0f\x41vatarSkillSlot\x12\x14\n\x07slot_id\x18\x01 \x01(\x04H\x00\x88\x01\x01\x12\x15\n\x08skill_id\x18\x02 \x01(\x04H\x01\x88\x01\x01\x12\x30\n\x0c\x65quip_source\x18\x03 \x01(\x0e\x32\x15.freefire.EquipSourceH\x02\x88\x01\x01\x42\n\n\x08_slot_idB\x0b\n\t_skill_idB\x0f\n\r_equip_source\"\xfe\x03\n\rAvatarProfile\x12\x16\n\tavatar_id\x18\x01 \x01(\rH\x00\x88\x01\x01\x12\x17\n\nskin_color\x18\x03 \x01(\rH\x01\x88\x01\x01\x12\x0f\n\x07\x63lothes\x18\x04 \x03(\r\x12\x16\n\x0e\x65quiped_skills\x18\x05 \x03(\r\x12\x18\n\x0bis_selected\x18\x06 \x01(\x08H\x02\x88\x01\x01\x12\x1f\n\x12pve_primary_weapon\x18\x07 \x01(\rH\x03\x88\x01\x01\x12\x1f\n\x12is_selected_awaken\x18\x08 \x01(\x08H\x04\x88\x01\x01\x12\x15\n\x08\x65nd_time\x18\t \x01(\rH\x05\x88\x01\x01\x12.\n\x0bunlock_type\x18\n \x01(\x0e\x32\x14.freefire.UnlockTypeH\x06\x88\x01\x01\x12\x18\n\x0bunlock_time\x18\x0b \x01(\rH\x07\x88\x01\x01\x12\x1b\n\x0eis_marked_star\x18\x0c \x01(\x08H\x08\x88\x01\x01\x12\x1e\n\x16\x63lothes_tailor_effects\x18\x0d \x03(\rB\x0c\n\n_avatar_idB\r\n\x0b_skin_colorB\x0e\n\x0c_is_selectedB\x15\n\x13_pve_primary_weaponB\x15\n\x13_is_selected_awakenB\x0b\n\t_end_timeB\x0e\n\x0c_unlock_typeB\x0e\n\x0c_unlock_timeB\x11\n\x0f_is_marked_star\"\xd8\x02\n\x12\x41\x63\x63ountNewsContent\x12\x10\n\x08item_ids\x18\x01 \x03(\r\x12\x11\n\x04rank\x18\x02 \x01(\rH\x00\x88\x01\x01\x12\x17\n\nmatch_mode\x18\x03 \x01(\rH\x01\x88\x01\x01\x12\x13\n\x06map_id\x18\x04 \x01(\rH\x02\x88\x01\x01\x12\x16\n\tgame_mode\x18\x05 \x01(\rH\x03\x88\x01\x01\x12\x17\n\ngroup_mode\x18\x06 \x01(\rH\x04\x88\x01\x01\x12\x1b\n\x0etreasurebox_id\x18\x07 \x01(\rH\x05\x88\x01\x01\x12\x19\n\x0c\x63ommodity_id\x18\x08 \x01(\rH\x06\x88\x01\x01\x12\x15\n\x08store_id\x18\t \x01(\rH\x07\x88\x01\x01\x42\x07\n\x05_rankB\r\n\x0b_match_modeB\t\n\x07_map_idB\x0c\n\n_game_modeB\r\n\x0b_group_modeB\x11\n\x0f_treasurebox_idB\x0f\n\r_commodity_idB\x0b\n\t_store_id\"\xa7\x01\n\x0b\x41\x63\x63ountNews\x12%\n\x04type\x18\x01 \x01(\x0e\x32\x12.freefire.NewsTypeH\x00\x88\x01\x01\x12\x32\n\x07\x63ontent\x18\x02 \x01(\x0b\x32\x1c.freefire.AccountNewsContentH\x01\x88\x01\x01\x12\x18\n\x0bupdate_time\x18\x03 \x01(\x03H\x02\x88\x01\x01\x42\x07\n\x05_typeB\n\n\x08_contentB\x0e\n\x0c_update_time\"\x99\x02\n\x0b\x42\x61sicEPInfo\x12\x18\n\x0b\x65p_event_id\x18\x01 \x01(\rH\x00\x88\x01\x01\x12\x17\n\nowned_pass\x18\x02 \x01(\x08H\x01\x88\x01\x01\x12\x15\n\x08\x65p_badge\x18\x03 \x01(\rH\x02\x88\x01\x01\x12\x16\n\tbadge_cnt\x18\x04 \x01(\rH\x03\x88\x01\x01\x12\x14\n\x07\x62p_icon\x18\x05 \x01(\tH\x04\x88\x01\x01\x12\x16\n\tmax_level\x18\x06 \x01(\rH\x05\x88\x01\x01\x12\x17\n\nevent_name\x18\x07 \x01(\tH\x06\x88\x01\x01\x42\x0e\n\x0c_ep_event_idB\r\n\x0b_owned_passB\x0b\n\t_ep_badgeB\x0c\n\n_badge_cntB\n\n\x08_bp_iconB\x0c\n\n_max_levelB\r\n\x0b_event_name\"\x9d\x02\n\rClanInfoBasic\x12\x14\n\x07\x63lan_id\x18\x01 \x01(\x04H\x00\x88\x01\x01\x12\x16\n\tclan_name\x18\x02 \x01(\tH\x01\x88\x01\x01\x12\x17\n\ncaptain_id\x18\x03 \x01(\x04H\x02\x88\x01\x01\x12\x17\n\nclan_level\x18\x04 \x01(\rH\x03\x88\x01\x01\x12\x15\n\x08\x63\x61pacity\x18\x05 \x01(\rH\x04\x88\x01\x01\x12\x17\n\nmember_num\x18\x06 \x01(\rH\x05\x88\x01\x01\x12\x18\n\x0bhonor_point\x18\x07 \x01(\rH\x06\x88\x01\x01\x42\n\n\x08_clan_idB\x0c\n\n_clan_nameB\r\n\x0b_captain_idB\r\n\x0b_clan_levelB\x0b\n\t_capacityB\r\n\x0b_member_numB\x0e\n\x0c_honor_point\"|\n\x0cPetSkillInfo\x12\x13\n\x06pet_id\x18\x01 \x01(\rH\x00\x88\x01\x01\x12\x15\n\x08skill_id\x18\x02 \x01(\rH\x01\x88\x01\x01\x12\x18\n\x0bskill_level\x18\x03 \x01(\rH\x02\x88\x01\x01\x42\t\n\x07_pet_idB\x0b\n\t_skill_idB\x0e\n\x0c_skill_level\"\x84\x03\n\x07PetInfo\x12\x0f\n\x02id\x18\x01 \x01(\rH\x00\x88\x01\x01\x12\x11\n\x04name\x18\x02 \x01(\tH\x01\x88\x01\x01\x12\x12\n\x05level\x18\x03 \x01(\rH\x02\x88\x01\x01\x12\x10\n\x03\x65xp\x18\x04 \x01(\rH\x03\x88\x01\x01\x12\x18\n\x0bis_selected\x18\x05 \x01(\x08H\x04\x88\x01\x01\x12\x14\n\x07skin_id\x18\x06 \x01(\rH\x05\x88\x01\x01\x12\x0f\n\x07\x61\x63tions\x18\x07 \x03(\r\x12&\n\x06skills\x18\x08 \x03(\x0b\x32\x16.freefire.PetSkillInfo\x12\x1e\n\x11selected_skill_id\x18\t \x01(\rH\x06\x88\x01\x01\x12\x1b\n\x0eis_marked_star\x18\n \x01(\x08H\x07\x88\x01\x01\x12\x15\n\x08\x65nd_time\x18\x0b \x01(\rH\x08\x88\x01\x01\x42\x05\n\x03_idB\x07\n\x05_nameB\x08\n\x06_levelB\x06\n\x04_expB\x0e\n\x0c_is_selectedB\n\n\x08_skin_idB\x14\n\x12_selected_skill_idB\x11\n\x0f_is_marked_starB\x0b\n\t_end_time\"<\n\x0e\x44iamondCostRes\x12\x19\n\x0c\x64iamond_cost\x18\x01 \x01(\rH\x00\x88\x01\x01\x42\x0f\n\r_diamond_cost\"\xfd\x03\n\x14\x43reditScoreInfoBasic\x12\x19\n\x0c\x63redit_score\x18\x01 \x01(\rH\x00\x88\x01\x01\x12\x14\n\x07is_init\x18\x02 \x01(\x08H\x01\x88\x01\x01\x12\x30\n\x0creward_state\x18\x03 \x01(\x0e\x32\x15.freefire.RewardStateH\x02\x88\x01\x01\x12&\n\x19periodic_summary_like_cnt\x18\x04 \x01(\rH\x03\x88\x01\x01\x12)\n\x1cperiodic_summary_illegal_cnt\x18\x05 \x01(\rH\x04\x88\x01\x01\x12\x1d\n\x10weekly_match_cnt\x18\x06 \x01(\rH\x05\x88\x01\x01\x12(\n\x1bperiodic_summary_start_time\x18\x07 \x01(\x03H\x06\x88\x01\x01\x12&\n\x19periodic_summary_end_time\x18\x08 \x01(\x03H\x07\x88\x01\x01\x42\x0f\n\r_credit_scoreB\n\n\x08_is_initB\x0f\n\r_reward_stateB\x1c\n\x1a_periodic_summary_like_cntB\x1f\n\x1d_periodic_summary_illegal_cntB\x13\n\x11_weekly_match_cntB\x1e\n\x1c_periodic_summary_start_timeB\x1c\n\x1a_periodic_summary_end_time\"-\n\x0c\x45quipAchInfo\x12\x0e\n\x06\x61\x63h_id\x18\x01 \x01(\r\x12\r\n\x05level\x18\x02 \x01(\r\"\xfa\x06\n\x17\x41\x63\x63ountPersonalShowInfo\x12\x33\n\nbasic_info\x18\x01 \x01(\x0b\x32\x1a.freefire.AccountInfoBasicH\x00\x88\x01\x01\x12\x32\n\x0cprofile_info\x18\x02 \x01(\x0b\x32\x17.freefire.AvatarProfileH\x01\x88\x01\x01\x12$\n\x17ranking_leaderboard_pos\x18\x03 \x01(\x05H\x02\x88\x01\x01\x12#\n\x04news\x18\x04 \x03(\x0b\x32\x15.freefire.AccountNews\x12.\n\x0fhistory_ep_info\x18\x05 \x03(\x0b\x32\x15.freefire.BasicEPInfo\x12\x35\n\x0f\x63lan_basic_info\x18\x06 \x01(\x0b\x32\x17.freefire.ClanInfoBasicH\x03\x88\x01\x01\x12;\n\x12\x63\x61ptain_basic_info\x18\x07 \x01(\x0b\x32\x1a.freefire.AccountInfoBasicH\x04\x88\x01\x01\x12(\n\x08pet_info\x18\x08 \x01(\x0b\x32\x11.freefire.PetInfoH\x05\x88\x01\x01\x12\x33\n\x0bsocial_info\x18\t \x01(\x0b\x32\x19.freefire.SocialBasicInfoH\x06\x88\x01\x01\x12\x37\n\x10\x64iamond_cost_res\x18\n \x01(\x0b\x32\x18.freefire.DiamondCostResH\x07\x88\x01\x01\x12>\n\x11\x63redit_score_info\x18\x0b \x01(\x0b\x32\x1e.freefire.CreditScoreInfoBasicH\x08\x88\x01\x01\x12=\n\x10pre_veteran_type\x18\x0c \x01(\x0e\x32\x1e.freefire.PreVeteranActionTypeH\t\x88\x01\x01\x12,\n\x0c\x65quipped_ach\x18\r \x03(\x0b\x32\x16.freefire.EquipAchInfoB\r\n\x0b_basic_infoB\x0f\n\r_profile_infoB\x1a\n\x18_ranking_leaderboard_posB\x12\n\x10_clan_basic_infoB\x15\n\x13_captain_basic_infoB\x0b\n\t_pet_infoB\x0e\n\x0c_social_infoB\x13\n\x11_diamond_cost_resB\x14\n\x12_credit_score_infoB\x13\n\x11_pre_veteran_type*\xa0\x01\n\x10VeteranLeaveDays\x12\x19\n\x15VeteranLeaveDays_NONE\x10\x00\x12\x1a\n\x16VeteranLeaveDays_SHORT\x10\x01\x12\x1b\n\x17VeteranLeaveDays_NORMAL\x10\x02\x12\x19\n\x15VeteranLeaveDays_LONG\x10\x03\x12\x1d\n\x19VeteranLeaveDays_VERYLONG\x10\x04*w\n\x14PreVeteranActionType\x12\x1d\n\x19PreVeteranActionType_NONE\x10\x00\x12!\n\x1dPreVeteranActionType_ACTIVITY\x10\x01\x12\x1d\n\x19PreVeteranActionType_BUFF\x10\x02*s\n\x12\x45xternalIconStatus\x12\x1b\n\x17\x45xternalIconStatus_NONE\x10\x00\x12!\n\x1d\x45xternalIconStatus_NOT_IN_USE\x10\x01\x12\x1d\n\x19\x45xternalIconStatus_IN_USE\x10\x02*t\n\x14\x45xternalIconShowType\x12\x1d\n\x19\x45xternalIconShowType_NONE\x10\x00\x12\x1f\n\x1b\x45xternalIconShowType_FRIEND\x10\x01\x12\x1c\n\x18\x45xternalIconShowType_ALL\x10\x02*\xf0\x02\n\tHighLight\x12\x12\n\x0eHighLight_NONE\x10\x00\x12\x14\n\x10HighLight_BR_WIN\x10\x01\x12\x14\n\x10HighLight_CS_MVP\x10\x02\x12\x1b\n\x17HighLight_BR_STREAK_WIN\x10\x03\x12\x1b\n\x17HighLight_CS_STREAK_WIN\x10\x04\x12#\n\x1fHighLight_CS_RANK_GROUP_UPGRADE\x10\x05\x12\x16\n\x12HighLight_TEAM_ACE\x10\x06\x12 \n\x1cHighLight_WEAPON_POWER_TITLE\x10\x07\x12#\n\x1fHighLight_BR_RANK_GROUP_UPGRADE\x10\t\x12&\n\"HighLight_BR_STREAK_WIN_EXECELLENT\x10\n\x12&\n\"HighLight_CS_STREAK_WIN_EXECELLENT\x10\x0b\x12\x15\n\x11HighLight_VETERAN\x10\x0c*T\n\x06Gender\x12\x0f\n\x0bGender_NONE\x10\x00\x12\x0f\n\x0bGender_MALE\x10\x01\x12\x11\n\rGender_FEMALE\x10\x02\x12\x15\n\x10Gender_UNLIMITED\x10\xe7\x07*\xf5\x03\n\x08Language\x12\x11\n\rLanguage_NONE\x10\x00\x12\x0f\n\x0bLanguage_EN\x10\x01\x12\x1a\n\x16Language_CN_SIMPLIFIED\x10\x02\x12\x1b\n\x17Language_CN_TRADITIONAL\x10\x03\x12\x11\n\rLanguage_Thai\x10\x04\x12\x17\n\x13Language_VIETNAMESE\x10\x05\x12\x17\n\x13Language_INDONESIAN\x10\x06\x12\x17\n\x13Language_PORTUGUESE\x10\x07\x12\x14\n\x10Language_SPANISH\x10\x08\x12\x14\n\x10Language_RUSSIAN\x10\t\x12\x13\n\x0fLanguage_KOREAN\x10\n\x12\x13\n\x0fLanguage_FRENCH\x10\x0b\x12\x13\n\x0fLanguage_GERMAN\x10\x0c\x12\x14\n\x10Language_TURKISH\x10\r\x12\x12\n\x0eLanguage_HINDI\x10\x0e\x12\x15\n\x11Language_JAPANESE\x10\x0f\x12\x15\n\x11Language_ROMANIAN\x10\x10\x12\x13\n\x0fLanguage_ARABIC\x10\x11\x12\x14\n\x10Language_BURMESE\x10\x12\x12\x11\n\rLanguage_URDU\x10\x13\x12\x14\n\x10Language_BENGALI\x10\x14\x12\x17\n\x12Language_UNLIMITED\x10\xe7\x07*l\n\nTimeOnline\x12\x13\n\x0fTimeOnline_NONE\x10\x00\x12\x16\n\x12TimeOnline_WORKDAY\x10\x01\x12\x16\n\x12TimeOnline_WEEKEND\x10\x02\x12\x19\n\x14TimeOnline_UNLIMITED\x10\xe7\x07*\x84\x01\n\nTimeActive\x12\x13\n\x0fTimeActive_NONE\x10\x00\x12\x16\n\x12TimeActive_MORNING\x10\x01\x12\x18\n\x14TimeActive_AFTERNOON\x10\x02\x12\x14\n\x10TimeActive_NIGHT\x10\x03\x12\x19\n\x14TimeActive_UNLIMITED\x10\xe7\x07*\xf6\x02\n\x11PlayerBattleTagID\x12\x1a\n\x16PlayerBattleTagID_NONE\x10\x00\x12!\n\x1cPlayerBattleTagID_DOMINATION\x10\xcd\x08\x12\x1e\n\x19PlayerBattleTagID_UNCROWN\x10\xce\x08\x12\"\n\x1dPlayerBattleTagID_BESTPARTNER\x10\xcf\x08\x12\x1d\n\x18PlayerBattleTagID_SNIPER\x10\xd0\x08\x12\x1c\n\x17PlayerBattleTagID_MELEE\x10\xd1\x08\x12!\n\x1cPlayerBattleTagID_PEACEMAKER\x10\xd2\x08\x12\x1d\n\x18PlayerBattleTagID_AMBUSH\x10\xd3\x08\x12 \n\x1bPlayerBattleTagID_SHORTSTOP\x10\xd4\x08\x12\x1e\n\x19PlayerBattleTagID_RAMPAGE\x10\xd5\x08\x12\x1d\n\x18PlayerBattleTagID_LEADER\x10\xd6\x08*\xe4\x01\n\tSocialTag\x12\x12\n\x0eSocialTag_NONE\x10\x00\x12\x16\n\x11SocialTag_FASHION\x10\xb5\x10\x12\x15\n\x10SocialTag_SOCIAL\x10\xb6\x10\x12\x16\n\x11SocialTag_VETERAN\x10\xb7\x10\x12\x15\n\x10SocialTag_NEWBIE\x10\xb8\x10\x12\x19\n\x14SocialTag_PLAYFORWIN\x10\xb9\x10\x12\x19\n\x14SocialTag_PLAYFORFUN\x10\xba\x10\x12\x16\n\x11SocialTag_VOICEON\x10\xbb\x10\x12\x17\n\x12SocialTag_VOICEOFF\x10\xbc\x10*\x80\x01\n\nModePrefer\x12\x13\n\x0fModePrefer_NONE\x10\x00\x12\x11\n\rModePrefer_BR\x10\x01\x12\x11\n\rModePrefer_CS\x10\x02\x12\x1c\n\x18ModePrefer_ENTERTAINMENT\x10\x03\x12\x19\n\x14ModePrefer_UNLIMITED\x10\xe7\x07*X\n\x08RankShow\x12\x11\n\rRankShow_NONE\x10\x00\x12\x0f\n\x0bRankShow_BR\x10\x01\x12\x0f\n\x0bRankShow_CS\x10\x02\x12\x17\n\x12RankShow_UNLIMITED\x10\xe7\x07*L\n\x1b\x45LeaderBoardTitleRegionType\x12\x08\n\x04None\x10\x00\x12\x0b\n\x07\x43ountry\x10\x01\x12\x0c\n\x08Province\x10\x02\x12\x08\n\x04\x43ity\x10\x03*6\n\nUnlockType\x12\x13\n\x0fUnlockType_NONE\x10\x00\x12\x13\n\x0fUnlockType_LINK\x10\x01*E\n\x0b\x45quipSource\x12\x14\n\x10\x45quipSource_SELF\x10\x00\x12 \n\x1c\x45quipSource_CONFIDANT_FRIEND\x10\x01*\xfa\x01\n\x08NewsType\x12\x11\n\rNewsType_NONE\x10\x00\x12\x11\n\rNewsType_RANK\x10\x01\x12\x14\n\x10NewsType_LOTTERY\x10\x02\x12\x15\n\x11NewsType_PURCHASE\x10\x03\x12\x18\n\x14NewsType_TREASUREBOX\x10\x04\x12\x16\n\x12NewsType_ELITEPASS\x10\x05\x12\x1a\n\x16NewsType_EXCHANGESTORE\x10\x06\x12\x13\n\x0fNewsType_BUNDLE\x10\x07\x12#\n\x1fNewsType_LOTTERYSPECIALEXCHANGE\x10\x08\x12\x13\n\x0fNewsType_OTHERS\x10\t*]\n\x0bRewardState\x12\x18\n\x14REWARD_STATE_INVALID\x10\x00\x12\x1a\n\x16REWARD_STATE_UNCLAIMED\x10\x01\x12\x18\n\x14REWARD_STATE_CLAIMED\x10\x02\x62\x06proto3')
_builder.BuildMessageAndEnumDescriptors(DESCRIPTOR_1, globals())
_builder.BuildTopDescriptorsAndMessages(DESCRIPTOR_1, 'AccountPersonalShow_pb2', globals())

DESCRIPTOR_2 = _descriptor_pool.Default().AddSerializedFile(b'\n\x0e\x46reeFire.proto\"c\n\x08LoginReq\x12\x0f\n\x07open_id\x18\x16 \x01(\t\x12\x14\n\x0copen_id_type\x18\x17 \x01(\t\x12\x13\n\x0blogin_token\x18\x1d \x01(\t\x12\x1b\n\x13orign_platform_type\x18\x63 \x01(\t\"]\n\x10\x42lacklistInfoRes\x12\x1e\n\nban_reason\x18\x01 \x01(\x0e\x32\n.BanReason\x12\x17\n\x0f\x65xpire_duration\x18\x02 \x01(\r\x12\x10\n\x08\x62\x61n_time\x18\x03 \x01(\r\"f\n\x0eLoginQueueInfo\x12\r\n\x05\x61llow\x18\x01 \x01(\x08\x12\x16\n\x0equeue_position\x18\x02 \x01(\r\x12\x16\n\x0eneed_wait_secs\x18\x03 \x01(\r\x12\x15\n\rqueue_is_full\x18\x04 \x01(\x08\"\xa0\x03\n\x08LoginRes\x12\x12\n\naccount_id\x18\x01 \x01(\x04\x12\x13\n\x0block_region\x18\x02 \x01(\t\x12\x13\n\x0bnoti_region\x18\x03 \x01(\t\x12\x11\n\tip_region\x18\x04 \x01(\t\x12\x19\n\x11\x61gora_environment\x18\x05 \x01(\t\x12\x19\n\x11new_active_region\x18\x06 \x01(\t\x12\x19\n\x11recommend_regions\x18\x07 \x03(\t\x12\r\n\x05token\x18\x08 \x01(\t\x12\x0b\n\x03ttl\x18\t \x01(\r\x12\x12\n\nserver_url\x18\n \x01(\t\x12\x16\n\x0e\x65mulator_score\x18\x0b \x01(\r\x12$\n\tblacklist\x18\x0c \x01(\x0b\x32\x11.BlacklistInfoRes\x12#\n\nqueue_info\x18\r \x01(\x0b\x32\x0f.LoginQueueInfo\x12\x0e\n\x06tp_url\x18\x0e \x01(\t\x12\x15\n\rapp_server_id\x18\x0f \x01(\r\x12\x0f\n\x07\x61no_url\x18\x10 \x01(\t\x12\x0f\n\x07ip_city\x18\x11 \x01(\t\x12\x16\n\x0eip_subdivision\x18\x12 \x01(\t*\xa8\x01\n\tBanReason\x12\x16\n\x12\x42\x41N_REASON_UNKNOWN\x10\x00\x12\x1b\n\x17\x42\x41N_REASON_IN_GAME_AUTO\x10\x01\x12\x15\n\x11\x42\x41N_REASON_REFUND\x10\x02\x12\x15\n\x11\x42\x41N_REASON_OTHERS\x10\x03\x12\x16\n\x12\x42\x41N_REASON_SKINMOD\x10\x04\x12 \n\x1b\x42\x41N_REASON_IN_GAME_AUTO_NEW\x10\xf6\x07\x62\x06proto3')
_builder.BuildMessageAndEnumDescriptors(DESCRIPTOR_2, globals())
_builder.BuildTopDescriptorsAndMessages(DESCRIPTOR_2, 'FreeFire_pb2', globals())

DESCRIPTOR_3 = _descriptor_pool.Default().AddSerializedFile(b'\n\x0csample.proto\"*\n\x12SearchWorkshopCode\x12\t\n\x01\x61\x18\x01 \x01(\t\x12\t\n\x01\x62\x18\x02 \x01(\x05\"-\n\x15GetPlayerPersonalShow\x12\t\n\x01\x61\x18\x01 \x01(\x03\x12\t\n\x01\x62\x18\x02 \x01(\x05\"\xf8\x08\n\x0cJwtGenerator\x12\x11\n\ttimestamp\x18\x03 \x01(\t\x12\x11\n\tgame_name\x18\x04 \x01(\t\x12\x14\n\x0cversion_code\x18\x05 \x01(\x05\x12\x13\n\x0b\x61pp_version\x18\x07 \x01(\t\x12\x17\n\x0f\x61ndroid_version\x18\x08 \x01(\t\x12\x13\n\x0b\x64\x65vice_type\x18\t \x01(\t\x12\x18\n\x10network_provider\x18\n \x01(\t\x12\x14\n\x0cnetwork_type\x18\x0b \x01(\t\x12\x14\n\x0cscreen_width\x18\x0c \x01(\x05\x12\x15\n\rscreen_height\x18\r \x01(\x05\x12\x0b\n\x03\x64pi\x18\x0e \x01(\t\x12\x10\n\x08\x63pu_info\x18\x0f \x01(\t\x12\x0b\n\x03\x66ps\x18\x10 \x01(\x05\x12\x11\n\tgpu_model\x18\x11 \x01(\t\x12\x16\n\x0eopengl_version\x18\x12 \x01(\t\x12\x11\n\tdevice_id\x18\x13 \x01(\t\x12\x12\n\nip_address\x18\x14 \x01(\t\x12\x10\n\x08language\x18\x15 \x01(\t\x12\x13\n\x0b\x64\x65vice_hash\x18\x16 \x01(\t\x12\x14\n\x0cos_api_level\x18\x17 \x01(\t\x12\x15\n\ros_build_type\x18\x18 \x01(\t\x12\x14\n\x0c\x64\x65vice_model\x18\x19 \x01(\t\x12\x19\n\x11package_signature\x18\x1d \x01(\t\x12\x12\n\nuser_level\x18\x1e \x01(\x05\x12\x14\n\x0c\x63\x61rrier_name\x18) \x01(\t\x12\x1a\n\x12network_generation\x18* \x01(\t\x12\x15\n\rapp_signature\x18\x39 \x01(\t\x12\x11\n\tplayer_id\x18< \x01(\x03\x12\x12\n\nsession_id\x18= \x01(\x03\x12\x10\n\x08match_id\x18> \x01(\x05\x12\r\n\x05score\x18@ \x01(\x03\x12\x13\n\x0btotal_score\x18\x41 \x01(\x03\x12\x12\n\nhigh_score\x18\x42 \x01(\x03\x12\x11\n\tmax_score\x18\x43 \x01(\x03\x12\x13\n\x0bplayer_rank\x18I \x01(\x05\x12\x17\n\x0fnative_lib_path\x18J \x01(\t\x12\x15\n\ris_debuggable\x18L \x01(\x05\x12\x12\n\napp_source\x18M \x01(\t\x12\x0f\n\x07is_beta\x18N \x01(\x05\x12\x11\n\tis_tester\x18O \x01(\x05\x12\x1b\n\x13target_architecture\x18Q \x01(\t\x12\x18\n\x10\x61pp_version_code\x18S \x01(\t\x12\x19\n\x11\x61pp_revision_code\x18U \x01(\x05\x12\x14\n\x0cgraphics_api\x18V \x01(\t\x12\x18\n\x10max_texture_size\x18W \x01(\x05\x12\x17\n\x0fprocessor_count\x18X \x01(\x05\x12\x16\n\x0e\x65ncryption_key\x18Y \x01(\t\x12\x19\n\x11\x66rame_buffer_size\x18\\ \x01(\x05\x12\x15\n\rplatform_type\x18] \x01(\t\x12\x16\n\x0esecurity_token\x18^ \x01(\t\x12\x18\n\x10\x64isplay_settings\x18` \x01(\t\x12\x14\n\x0cis_logged_in\x18\x61 \x01(\x05\x62\x06proto3')
_builder.BuildMessageAndEnumDescriptors(DESCRIPTOR_3, globals())
_builder.BuildTopDescriptorsAndMessages(DESCRIPTOR_3, 'main_pb2', globals())

# === Settings & Encryption Keys ===
MAIN_KEY = base64.b64decode('WWcmdGMlREV1aDYlWmNeOA==')
MAIN_IV = base64.b64decode('Nm95WkRyMjJFM3ljaGpNJQ==')
RELEASEVERSION = "OB54"

# === Dynamic Accounts State Management ===
API_ACCOUNTS_FILE = 'api.json'
file_lock = threading.Lock()

# 🚀 LOCAL GLOBAL IN-MEMORY CACHE (RAM) replacing Redis Server entirely
token_pool = {}
account_index = 0
account_lock = threading.Lock()

API_ACCOUNTS_CACHE = []
LAST_API_ACCS_LOAD_TIME = 0
LAST_API_ACCS_MTIME = 0

HTTP_CLIENT = httpx.AsyncClient(
    limits=httpx.Limits(max_keepalive_connections=50, max_connections=150),
    timeout=10.0
)

# 🚀 RESTORED DYNAMIC SYNC ENGINE (Bypasses physical files on SQLite Mode)
def load_dynamic_api_accounts() -> List[Any]:
    global API_ACCOUNTS_CACHE, LAST_API_ACCS_LOAD_TIME, LAST_API_ACCS_MTIME
    try:
        if os.environ.get("USE_DB") == "TRUE":
            now = time.time()
            if now - LAST_API_ACCS_LOAD_TIME > 5 or not API_ACCOUNTS_CACHE:
                API_ACCOUNTS_CACHE = data_coordinator.load_data(API_ACCOUNTS_FILE, [])
                LAST_API_ACCS_LOAD_TIME = now
        else:
            if os.path.exists(API_ACCOUNTS_FILE):
                curr_mtime = os.path.getmtime(API_ACCOUNTS_FILE)
                if curr_mtime != LAST_API_ACCS_MTIME or not API_ACCOUNTS_CACHE:
                    API_ACCOUNTS_CACHE = data_coordinator.load_data(API_ACCOUNTS_FILE, [])
                    LAST_API_ACCS_MTIME = curr_mtime
            else:
                API_ACCOUNTS_CACHE = []
    except Exception:
        pass
    return API_ACCOUNTS_CACHE

def get_next_account_index() -> int:
    global account_index
    current_accounts = load_dynamic_api_accounts()
    num_accounts = len(current_accounts)
    if num_accounts == 0:
        return -1
    with account_lock:
        account_index = account_index % num_accounts
        current_idx = account_index
        account_index = (current_idx + 1) % num_accounts
        return current_idx

# === Verified Device Profiles ===
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

# === Helper Functions ===
def pad(text: bytes) -> bytes:
    padding_length = AES.block_size - (len(text) % AES.block_size)
    return text + bytes([padding_length] * padding_length)

def normalize_key_iv(val) -> bytes:
    if isinstance(val, str):
        val = val.strip()
        if len(val) == 32:
            try: return bytes.fromhex(val)
            except ValueError: pass
        return val.encode('utf-8')[:16].ljust(16, b'\x00')
    elif isinstance(val, bytes):
        if len(val) == 32:
            try: return bytes.fromhex(val.decode('utf-8', errors='ignore'))
            except Exception: pass
        return val[:16].ljust(16, b'\x00')
    try: return bytes(val)[:16].ljust(16, b'\x00')
    except Exception: return b'\x00' * 16

def aes_cbc_encrypt(key: bytes, iv: bytes, plaintext: bytes) -> bytes:
    norm_key = normalize_key_iv(key)
    norm_iv = normalize_key_iv(iv)
    aes = AES.new(norm_key, AES.MODE_CBC, norm_iv)
    return aes.encrypt(pad(plaintext))

def decode_protobuf(encoded_data: bytes, message_type: message.Message) -> message.Message:
    instance = message_type()
    instance.ParseFromString(encoded_data)
    return instance

async def json_to_proto(json_data: str, proto_message: Message) -> bytes:
    json_format.ParseDict(json.loads(json_data), proto_message)
    return proto_message.SerializeToString()

# === Token Generation ===
async def get_access_token(account_data: Any):
    if isinstance(account_data, dict):
        # 🟢 CRITICAL FIX: Ensure 'account' is defined if 'uid' is passed,
        # as Garena ffmconnect API specifically requires the 'account' parameter.
        temp_dict = {}
        for k, v in account_data.items():
            if k == 'uid' or k == 'account':
                temp_dict['account'] = str(v).strip()
                temp_dict['uid'] = str(v).strip()
            else:
                temp_dict[k] = str(v).strip()
        account_str = "&".join(f"{k}={v}" for k, v in temp_dict.items())
    else:
        account_str = str(account_data).strip()
        # If passed as raw string like "uid=123&password=abc", ensure 'account' is appended
        if "uid=" in account_str and "account=" not in account_str:
            account_str = account_str.replace("uid=", "account=") + "&" + account_str
        elif "account=" in account_str and "uid=" not in account_str:
            account_str = account_str.replace("account=", "uid=") + "&" + account_str

    url = "https://ffmconnect.live.gop.garenanow.com/oauth/guest/token/grant"
    payload = account_str + "&response_type=token&client_type=2&client_secret=2ee44819e9b4598845141067b281621874d0d5d7af9d8f7e00c1e54715b7d1e3&client_id=100067"
    headers = {
        'Connection': "Keep-Alive",
        'Accept-Encoding': "gzip",
        'Content-Type': "application/x-www-form-urlencoded"
    }
    resp = await HTTP_CLIENT.post(url, data=payload, headers=headers)
    data = resp.json()
    return data.get("access_token", "0"), data.get("open_id", "0")

# 🚀 NATIVE LOCAL RAM CACHING (Bypasses Redis, keeps Garena handshake fast & active)
async def create_jwt_for_account(idx: int, account_data: Any):
    try:
        acc_uid = "0"
        if isinstance(account_data, dict):
            acc_uid = str(account_data.get("uid", "0")).strip()
        elif "uid=" in str(account_data):
            try: acc_uid = str(urllib.parse.parse_qs(account_data).get("uid", ["0"])[0]).strip()
            except: pass

        # Load session details directly from local python token pool dictionary
        if acc_uid != "0" and acc_uid in token_pool:
            info = token_pool[acc_uid]
            if time.time() < info['expires_at']:
                return info

        token_val, open_id = await get_access_token(account_data)
        body = json.dumps({
            "open_id": open_id,
            "open_id_type": "4",
            "login_token": token_val,
            "orign_platform_type": "4"
        })
        
        proto_bytes = await json_to_proto(body, globals()['LoginReq']())
        payload = aes_cbc_encrypt(MAIN_KEY, MAIN_IV, proto_bytes)
        url = "https://loginbp.ggblueshark.com/MajorLogin"
        headers = {
            'Connection': "Keep-Alive",
            'Accept-Encoding': "gzip",
            'Content-Type': "application/octet-stream",
            'Expect': "100-continue",
            'X-Unity-Version': "2018.4.11f1",
            'X-GA': "v1 1",
            'ReleaseVersion': RELEASEVERSION
        }
        
        resp = await HTTP_CLIENT.post(url, data=payload, headers=headers)
        if resp.status_code != 200 or not resp.content or resp.content.startswith(b'BR_GOP_TOKEN_AUTH_FAILED'):
            raise RuntimeError(f"Token request failed for account index {idx}")
        
        msg = json.loads(json_format.MessageToJson(decode_protobuf(resp.content, globals()['LoginRes'])))
        
        token_info = {
            'token': f"Bearer {msg.get('token','0')}",
            'region': msg.get('lockRegion','0'),
            'server_url': msg.get('serverUrl','0'),
            'expires_at': time.time() + 21600  # Valid for 6 hours
        }

        # Cache successfully logged-in session inside python memory
        if acc_uid != "0":
            token_pool[acc_uid] = token_info

        return token_info
    except Exception as e:
        print(f"Error generating token for Account [{idx}]: {e}")
        raise e

async def get_rotated_token_info() -> Tuple[int, str, str, str]:
    current_accounts = load_dynamic_api_accounts()
    if not current_accounts:
        raise RuntimeError("api.json accounts pool is empty!")
        
    idx = get_next_account_index()
    if idx == -1 or idx >= len(current_accounts):
        idx = 0
        if not current_accounts:
            raise RuntimeError("api.json accounts pool is empty!")
            
    account_data = current_accounts[idx]
    acc_uid = "0"
    if isinstance(account_data, dict):
        acc_uid = str(account_data.get("uid", "0")).strip()
    elif "uid=" in str(account_data):
        try: acc_uid = str(urllib.parse.parse_qs(account_data).get("uid", ["0"])[0]).strip()
        except: pass

    # Fetch token directly from local RAM dictionary cache
    if acc_uid != "0" and acc_uid in token_pool:
        info = token_pool[acc_uid]
        if time.time() < info['expires_at']:
            return idx, info['token'], info['region'], info['server_url']
            
    info = await create_jwt_for_account(idx, account_data)
    return idx, info['token'], info['region'], info['server_url']

# ========================================================
# 🚀 CORE GARENA API CLIENT IMPLEMENTATION
# ========================================================
async def GetAccountInformation(uid, unk="7", endpoint="/GetPlayerPersonalShow", max_retries=5):
    current_accounts = load_dynamic_api_accounts()
    if not current_accounts:
        raise RuntimeError("No active bot accounts available inside api.json database pool!")

    try: payload = await json_to_proto(json.dumps({'a': int(uid), 'b': int(unk)}), globals()['GetPlayerPersonalShow']())
    except ValueError: payload = await json_to_proto(json.dumps({'a': uid, 'b': unk}), globals()['GetPlayerPersonalShow']())
        
    data_enc = aes_cbc_encrypt(MAIN_KEY, MAIN_IV, payload)
    last_error = None
    
    for attempt in range(max_retries):
        acc_idx = "Unknown" 
        try:
            acc_idx, token, lock, server = await get_rotated_token_info()
            
            headers = {
                'Connection': "Keep-Alive",
                'Accept-Encoding': "gzip",
                'Content-Type': "application/octet-stream",
                'Expect': "100-continue",
                'Authorization': token,
                'X-Unity-Version': "2018.4.11f1",
                'X-GA': "v1 1",
                'ReleaseVersion': RELEASEVERSION
            }
            
            resp = await HTTP_CLIENT.post(server + endpoint, data=data_enc, headers=headers)
            
            if resp.status_code == 401:
                # Remove cached memory session instantly if Garena returns Unauthorized
                current_accounts = load_dynamic_api_accounts()
                if acc_idx < len(current_accounts):
                    acc = current_accounts[acc_idx]
                    acc_uid = "0"
                    if isinstance(acc, dict): acc_uid = str(acc.get("uid", "0")).strip()
                    elif "uid=" in str(acc): acc_uid = str(urllib.parse.parse_qs(acc).get("uid", ["0"])[0]).strip()
                    if acc_uid != "0" and acc_uid in token_pool:
                        del token_pool[acc_uid]
                continue 
            
            return json.loads(json_format.MessageToJson(
                decode_protobuf(resp.content, globals()['AccountPersonalShowInfo'])
            ))
            
        except Exception as e:
            last_error = e
            continue
            
    raise RuntimeError(f"Garena API connection failed after {max_retries} attempts. Original Error: {str(last_error)}")

# END OF FILE manager.py