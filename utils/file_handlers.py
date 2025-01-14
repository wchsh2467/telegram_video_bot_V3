import os
import re
import asyncio
import logging
from typing import Optional
import yaml
from config.settings import FILE_IDS_FILE, VIDEO_FORMATS

logger = logging.getLogger(__name__)

def clean_filename(filename: str) -> str:
    """ניקוי שם הקובץ מתווים לא חוקיים"""
    # החלפת תווים לא חוקיים ברווח
    illegal_chars = r'[<>:"/\\|?*]'
    cleaned = re.sub(illegal_chars, ' ', filename)
    # הסרת רווחים מיותרים
    cleaned = ' '.join(cleaned.split())
    return cleaned

def get_video_quality(filename: str) -> tuple[Optional[str], Optional[str]]:
    """מציאת איכות הווידאו מתוך שם הקובץ"""
    pixel_format = None
    other_format = None
    
    # חיפוש פורמט פיקסלים
    for fmt in VIDEO_FORMATS['PIXEL']:
        if fmt.lower() in filename.lower():
            pixel_format = fmt
            break
            
    # חיפוש פורמט אחר
    for fmt in VIDEO_FORMATS['OTHER']:
        if fmt.lower() in filename.lower():
            other_format = fmt
            break
            
    return pixel_format, other_format

def load_file_ids() -> dict:
    """טעינת מזהי קבצים מהקובץ"""
    if os.path.exists(FILE_IDS_FILE):
        try:
            with open(FILE_IDS_FILE, 'r', encoding='utf-8') as file:
                return yaml.safe_load(file) or {}
        except Exception as e:
            logger.error(f"שגיאה בטעינת קובץ מזהים: {e}")
    return {}

def get_file_id(file_id_str: str) -> Optional[int]:
    """המרת מזהה קובץ ממחרוזת למספר עבור Telethon"""
    try:
        return int(file_id_str) if file_id_str else None
    except ValueError:
        logger.error(f"שגיאה בהמרת file_id: {file_id_str}")
        return None

def save_file_id(file_name: str, file_id: int):
    """שמירת מזהה קובץ"""
    file_ids = load_file_ids()
    # המרת מזהה הקובץ למחרוזת כי ב-Telethon הוא מגיע כמספר
    file_ids[file_name] = str(file_id)
    try:
        os.makedirs(os.path.dirname(FILE_IDS_FILE), exist_ok=True)
        with open(FILE_IDS_FILE, 'w', encoding='utf-8') as file:
            yaml.dump(file_ids, file, allow_unicode=True)
        logger.info(f"נשמר file_id עבור {file_name}")
    except Exception as e:
        logger.error(f"שגיאה בשמירת file_id: {e}")

async def wait_for_file_release(file_path: str):
    """המתנה לשחרור הקובץ"""
    max_attempts = 10
    attempt = 0
    while attempt < max_attempts:
        try:
            with open(file_path, 'a'):
                pass
            return True
        except IOError:
            attempt += 1
            await asyncio.sleep(1)
    return False

async def safe_delete_file(file_path: str):
    """מחיקה בטוחה של קובץ"""
    try:
        if os.path.exists(file_path):
            if await wait_for_file_release(file_path):
                os.remove(file_path)
                logger.info(f"הקובץ {file_path} נמחק בהצלחה")
            else:
                logger.warning(f"לא ניתן למחוק את הקובץ {file_path} - הקובץ נעול")
    except Exception as e:
        logger.error(f"שגיאה במחיקת הקובץ {file_path}: {e}")

def get_video_caption(file_path: str) -> str:
    """יצירת כיתוב לווידאו"""
    # הסרת הסיומת מהקובץ
    base_name = os.path.splitext(os.path.basename(file_path))[0]
    
    # קבלת פרטי איכות
    pixel_format, other_format = get_video_quality(base_name)
    
    # הסרת פרטי האיכות מהשם
    clean_name = base_name
    if pixel_format:
        clean_name = clean_name.replace(pixel_format, '').strip()
    if other_format:
        clean_name = clean_name.replace(other_format, '').strip()
    
    # בניית הכיתוב
    caption = f"**{clean_name}**\n\n"
    
    # הוספת פרטי איכות אם קיימים
    quality_info = []
    if pixel_format:
        quality_info.append(f"**🎯 רזולוציה:** {pixel_format}")
    if other_format:
        quality_info.append(f"**📼 איכות:** {other_format}")
        
    if quality_info:
        caption += '\n'.join(quality_info)
        
    return caption
