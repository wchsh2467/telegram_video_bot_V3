import os
from dotenv import load_dotenv

# טעינת משתני הסביבה
load_dotenv()

# הגדרות Telethon
API_ID = int(os.getenv("API_ID"))  # חייב להיות מספר עבור Telethon
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")

# הגדרות Session
SESSION_NAME = "bot_session"  # שם ה-session עבור Telethon

# הגדרות נתיבים
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOWNLOAD_PATH = os.getenv("DOWNLOAD_PATH", os.path.join(BASE_DIR, "downloads"))
TEMP_PATH = os.path.join(BASE_DIR, "temp")

# הגדרות קבוצה
TARGET_GROUP_ID = int(os.getenv("TARGET_GROUP_ID"))

# הגדרות קבצים
FILE_IDS_FILE = os.path.join(BASE_DIR, "data", "file_ids.yaml")
USERS_FILE = os.path.join(BASE_DIR, "data", "allowed_users.yaml")

# הגדרות קבצים
AUTH_CONFIG_FILE = os.path.join(BASE_DIR, 'config', 'authorized_users.yaml')

# הגדרות פורמטים
VIDEO_FORMATS = {
    'PIXEL': [
        '144p', '240p', '360p', '480p', '600p', '720p', '1080p', '2160p',
        '144P', '240P', '360P', '480P', '600P', '720P', '1080P', '2160P'
    ],
    'OTHER': [
        'CAM', 'Ts', 'DVDRip', 'TVRip', 'HDTV', 'IPTV', 'WEB-DL',
        'WEBRip', 'HDRip', 'BDRip', 'BRRip', 'BluRay'
    ]
}

# מזהה מנהל הבוט
ADMIN_USER_ID = 1681880347  # המרה למספר שלם עבור Telethon

# יצירת תיקיות נדרשות
for path in [DOWNLOAD_PATH, TEMP_PATH, os.path.dirname(FILE_IDS_FILE), os.path.dirname(AUTH_CONFIG_FILE)]:
    if not os.path.exists(path):
        os.makedirs(path)
