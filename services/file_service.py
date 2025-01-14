import os
import yaml
import logging
import asyncio
from config.settings import FILE_IDS_FILE
from typing import Union

def load_file_ids() -> dict:
    """טעינת רשימת מזהי הקבצים מהקובץ"""
    if os.path.exists(FILE_IDS_FILE):
        with open(FILE_IDS_FILE, "r") as file:
            return yaml.safe_load(file) or {}
    return {}

def save_file_id(file_name: str, file_id: str) -> None:
    """שמירת מזהה הקובץ במאגר
    
    Args:
        file_name: שם הקובץ לשמירה
        file_id: מזהה הקובץ מטלגרם (מחרוזת)
    """
    file_ids = {}
    if os.path.exists(FILE_IDS_FILE):
        with open(FILE_IDS_FILE, 'r') as f:
            file_ids = yaml.safe_load(f) or {}
    
    file_ids[file_name] = file_id
    
    with open(FILE_IDS_FILE, 'w') as f:
        yaml.dump(file_ids, f)

def check_existing_file(file_name: str) -> Union[str, None]:
    """בדיקה אם הקובץ כבר קיים במאגר
    
    Args:
        file_name: שם הקובץ לחיפוש
        
    Returns:
        str או None: מחזיר את ה-file_id כמחרוזת אם קיים, אחרת None
    """
    if os.path.exists(FILE_IDS_FILE):
        with open(FILE_IDS_FILE, 'r') as f:
            file_ids = yaml.safe_load(f) or {}
            return file_ids.get(file_name)
    return None

async def convert_to_mp4(input_file: str, output_file: str) -> bool:
    """המרת קובץ וידאו לפורמט MP4"""
    try:
        process = await asyncio.create_subprocess_shell(
            f'ffmpeg -i "{input_file}" "{output_file}"',
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        await process.communicate()
        return process.returncode == 0
    except Exception as e:
        logging.error(f"שגיאה בהמרת הקובץ ל-MP4: {e}")
        return False

async def create_thumbnail(input_file: str, thumbnail_file: str) -> bool:
    """יצירת תמונה ממוזערת לוידאו"""
    try:
        process = await asyncio.create_subprocess_shell(
            f'ffmpeg -i "{input_file}" -ss 00:00:01.000 -vframes 1 "{thumbnail_file}"',
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        await process.communicate()
        return process.returncode == 0
    except Exception as e:
        logging.error(f"שגיאה ביצירת תמונה ממוזערת: {e}")
        return False
