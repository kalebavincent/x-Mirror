# -*- coding: utf-8 -*-
"""Configuration file for the Telegram bot.
This file loads environment variables and sets up the bot's configuration.
It includes settings for Telegram API, database, upload paths, and more.
"""

import os
import json
from dotenv import load_dotenv

# Charger les variables d'environnement
load_dotenv()

# Fonctions utilitaires
def get_bool(value: str) -> bool:
    return value.lower() in ("true", "1", "yes") if value else False

def get_list(value: str) -> list:
    if not value:
        return []
    try:
        return json.loads(value.replace("'", '"'))
    except:
        return [x.strip() for x in value.split(",")]

def get_dict(value: str) -> dict:
    return json.loads(value) if value else {}

# REQUIRED CONFIG
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
OWNER_ID = int(os.getenv("OWNER_ID", "0"))
TELEGRAM_API = int(os.getenv("TELEGRAM_API", "0"))
TELEGRAM_HASH = os.getenv("TELEGRAM_HASH", "")

# OPTIONAL CONFIG
TG_PROXY = get_dict(os.getenv("TG_PROXY", "{}"))
USER_SESSION_STRING = os.getenv("USER_SESSION_STRING", "")
CMD_SUFFIX = os.getenv("CMD_SUFFIX", "")
AUTHORIZED_CHATS = get_list(os.getenv("AUTHORIZED_CHATS", ""))
SUDO_USERS = get_list(os.getenv("SUDO_USERS", ""))
DATABASE_URL = os.getenv("DATABASE_URL", "")
DATABASE_ENCRYPTION_KEY = os.getenv("DATABASE_ENCRYPTION_KEY", "")
STATUS_LIMIT = int(os.getenv("STATUS_LIMIT", "4"))
DEFAULT_UPLOAD = os.getenv("DEFAULT_UPLOAD", "rc")
STATUS_UPDATE_INTERVAL = int(os.getenv("STATUS_UPDATE_INTERVAL", "15"))
FILELION_API = os.getenv("FILELION_API", "")
STREAMWISH_API = os.getenv("STREAMWISH_API", "")
EXCLUDED_EXTENSIONS = os.getenv("EXCLUDED_EXTENSIONS", "")
INCOMPLETE_TASK_NOTIFIER = get_bool(os.getenv("INCOMPLETE_TASK_NOTIFIER", "False"))
YT_DLP_OPTIONS = os.getenv("YT_DLP_OPTIONS", "")
USE_SERVICE_ACCOUNTS = get_bool(os.getenv("USE_SERVICE_ACCOUNTS", "False"))
NAME_SUBSTITUTE = os.getenv("NAME_SUBSTITUTE", "")
FFMPEG_CMDS = get_dict(os.getenv("FFMPEG_CMDS", "{}"))
UPLOAD_PATHS = get_dict(os.getenv("UPLOAD_PATHS", "{}"))
RSS_CHAT = get_list(os.getenv("RSS_CHAT", "0"))

# GDrive Tools
GDRIVE_ID = os.getenv("GDRIVE_ID", "")
IS_TEAM_DRIVE = get_bool(os.getenv("IS_TEAM_DRIVE", "False"))
STOP_DUPLICATE = get_bool(os.getenv("STOP_DUPLICATE", "False"))
INDEX_URL = os.getenv("INDEX_URL", "")

# Rclone
RCLONE_PATH = os.getenv("RCLONE_PATH", "")
RCLONE_FLAGS = os.getenv("RCLONE_FLAGS", "")
RCLONE_SERVE_URL = os.getenv("RCLONE_SERVE_URL", "")
RCLONE_SERVE_PORT = int(os.getenv("RCLONE_SERVE_PORT", "0"))
RCLONE_SERVE_USER = os.getenv("RCLONE_SERVE_USER", "")
RCLONE_SERVE_PASS = os.getenv("RCLONE_SERVE_PASS", "")

# JDownloader
JD_EMAIL = os.getenv("JD_EMAIL", "")
JD_PASS = os.getenv("JD_PASS", "")

# Sabnzbd (reste inchangé car complexe)
USENET_SERVERS = [
    {
        "name": "main",
        "host": "",
        "port": 563,
        "timeout": 60,
        "username": "",
        "password": "",
        "connections": 8,
        "ssl": 1,
        "ssl_verify": 2,
        "ssl_ciphers": "",
        "enable": 1,
        "required": 0,
        "optional": 0,
        "retention": 0,
        "send_group": 0,
        "priority": 0,
    }
]

# Nzb search
HYDRA_IP = os.getenv("HYDRA_IP", "")
HYDRA_API_KEY = os.getenv("HYDRA_API_KEY", "")

# Update
UPSTREAM_REPO = os.getenv("UPSTREAM_REPO", "")
UPSTREAM_BRANCH = os.getenv("UPSTREAM_BRANCH", "master")

# Leech
LEECH_SPLIT_SIZE = int(os.getenv("LEECH_SPLIT_SIZE", "0"))
AS_DOCUMENT = get_bool(os.getenv("AS_DOCUMENT", "False"))
EQUAL_SPLITS = get_bool(os.getenv("EQUAL_SPLITS", "False"))
MEDIA_GROUP = get_bool(os.getenv("MEDIA_GROUP", "False"))
USER_TRANSMISSION = get_bool(os.getenv("USER_TRANSMISSION", "False"))
HYBRID_LEECH = get_bool(os.getenv("HYBRID_LEECH", "False"))
LEECH_FILENAME_PREFIX = os.getenv("LEECH_FILENAME_PREFIX", "")
LEECH_DUMP_CHAT = os.getenv("LEECH_DUMP_CHAT", "")
THUMBNAIL_LAYOUT = os.getenv("THUMBNAIL_LAYOUT", "")

# qBittorrent/Aria2c
TORRENT_TIMEOUT = int(os.getenv("TORRENT_TIMEOUT", "0"))
BASE_URL = os.getenv("BASE_URL", "")
BASE_URL_PORT = int(os.getenv("BASE_URL_PORT", "0"))
WEB_PINCODE = get_bool(os.getenv("WEB_PINCODE", "False"))

# Queueing system
QUEUE_ALL = int(os.getenv("QUEUE_ALL", "0"))
QUEUE_DOWNLOAD = int(os.getenv("QUEUE_DOWNLOAD", "0"))
QUEUE_UPLOAD = int(os.getenv("QUEUE_UPLOAD", "0"))

# RSS
RSS_DELAY = int(os.getenv("RSS_DELAY", "600"))
RSS_CHAT = os.getenv("RSS_CHAT", "")
RSS_SIZE_LIMIT = int(os.getenv("RSS_SIZE_LIMIT", "0"))

# Torrent Search
SEARCH_API_LINK = os.getenv("SEARCH_API_LINK", "")
SEARCH_LIMIT = int(os.getenv("SEARCH_LIMIT", "0"))
SEARCH_PLUGINS = get_list(os.getenv("SEARCH_PLUGINS", "")) or [
    "https://raw.githubusercontent.com/qbittorrent/search-plugins/master/nova3/engines/piratebay.py",
    "https://raw.githubusercontent.com/qbittorrent/search-plugins/master/nova3/engines/limetorrents.py",
    "https://raw.githubusercontent.com/qbittorrent/search-plugins/master/nova3/engines/torlock.py",
    "https://raw.githubusercontent.com/qbittorrent/search-plugins/master/nova3/engines/torrentscsv.py",
    "https://raw.githubusercontent.com/qbittorrent/search-plugins/master/nova3/engines/eztv.py",
    "https://raw.githubusercontent.com/qbittorrent/search-plugins/master/nova3/engines/torrentproject.py",
    "https://raw.githubusercontent.com/MaurizioRicci/qBittorrent_search_engines/master/kickass_torrent.py",
    "https://raw.githubusercontent.com/MaurizioRicci/qBittorrent_search_engines/master/yts_am.py",
    "https://raw.githubusercontent.com/MadeOfMagicAndWires/qBit-plugins/master/engines/linuxtracker.py",
    "https://raw.githubusercontent.com/MadeOfMagicAndWires/qBit-plugins/master/engines/nyaasi.py",
    "https://raw.githubusercontent.com/LightDestory/qBittorrent-Search-Plugins/master/src/engines/ettv.py",
    "https://raw.githubusercontent.com/LightDestory/qBittorrent-Search-Plugins/master/src/engines/glotorrents.py",
    "https://raw.githubusercontent.com/LightDestory/qBittorrent-Search-Plugins/master/src/engines/thepiratebay.py",
    "https://raw.githubusercontent.com/v1k45/1337x-qBittorrent-search-plugin/master/leetx.py",
    "https://raw.githubusercontent.com/nindogo/qbtSearchScripts/master/magnetdl.py",
    "https://raw.githubusercontent.com/msagca/qbittorrent_plugins/main/uniondht.py",
    "https://raw.githubusercontent.com/khensolomon/leyts/master/yts.py",
]